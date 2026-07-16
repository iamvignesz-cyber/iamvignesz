from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.rate_limit import SlidingWindowRateLimiter
from app.db.session import get_db
from app.models.models import Site, Snapshot, Alert, User, Role
from app.schemas.schemas import ScanResult
from app.core.security import get_current_user, require_role, require_same_org
from app.services.scanner import run_full_scan, score_from_scan
from app.services.ai import generate_summary
from app.services.audit import log_action

router = APIRouter(prefix="/api/scan", tags=["scan"])

# Scanning makes outbound network requests on the user's behalf and is the
# most abuse-prone endpoint (could otherwise be used to hammer a third-party
# site, or to brute-force-probe internal network responses/timing). Rate
# limit per-user in addition to the SSRF host validation in the scanner.
_scan_limiter = SlidingWindowRateLimiter(
    settings.SCAN_RATE_LIMIT_MAX_REQUESTS, settings.SCAN_RATE_LIMIT_WINDOW_SECONDS
)


@router.post("/{site_id}", response_model=ScanResult)
async def scan_site(
    site_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(Role.ANALYST)),  # Viewer cannot trigger scans
):
    # Keyed by user id (not just IP) so one org's heavy usage behind a shared
    # NAT/proxy doesn't throttle another org, and so the limit can't be
    # bypassed by rotating source IPs while reusing a token.
    _scan_limiter.check(f"user:{current_user.id}")

    site = db.query(Site).filter(Site.id == site_id).first()
    if not site:
        raise HTTPException(status_code=404, detail="Site not found")
    require_same_org(site.org_id, current_user)

    scan = await run_full_scan(site.url)
    score = score_from_scan(scan)

    prev = (
        db.query(Snapshot)
        .filter(Snapshot.site_id == site.id)
        .order_by(Snapshot.created_at.desc())
        .first()
    )
    defacement_suspected = bool(prev and prev.html_hash != scan.get("html_hash"))

    snapshot = Snapshot(
        site_id=site.id,
        html_hash=scan.get("html_hash", ""),
        headers=scan.get("headers"),
        scan_result=scan,
        security_score=str(score),
    )
    db.add(snapshot)

    if defacement_suspected:
        db.add(Alert(
            site_id=site.id,
            severity="SL-1",
            title="Content change detected (possible defacement)",
            description="HTML hash differs from previous snapshot.",
        ))

    if score < 60:
        db.add(Alert(
            site_id=site.id,
            severity="SL-2",
            title=f"Low security score: {score}/100",
            description="Multiple missing security headers or SSL issues detected.",
        ))

    db.commit()
    log_action(db, current_user.org_id, current_user.id, "scan_site", "site", {"site_id": site_id, "score": score})

    try:
        ai_summary = await generate_summary(scan, score)
    except Exception:
        # Scan data is already committed above; never let an AI-provider
        # hiccup turn a successful scan into a 500 for the caller.
        ai_summary = {
            "executive_summary": "AI summary unavailable due to an unexpected error.",
            "technical_summary": None,
            "remediation": None,
        }
    return ScanResult(scan=scan, score=score, ai_summary=ai_summary)
