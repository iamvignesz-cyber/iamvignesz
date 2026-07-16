from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.models import Alert, Site, User, Role, AuditLog
from app.schemas.schemas import AlertOut
from app.core.security import get_current_user, require_role, require_same_org
from app.services.audit import log_action

router = APIRouter(prefix="/api", tags=["alerts"])


@router.get("/sites/{site_id}/alerts", response_model=list[AlertOut])
def list_alerts(site_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    site = db.query(Site).filter(Site.id == site_id).first()
    if not site:
        raise HTTPException(status_code=404, detail="Site not found")
    require_same_org(site.org_id, current_user)
    return db.query(Alert).filter(Alert.site_id == site_id).order_by(Alert.created_at.desc()).all()


@router.post("/alerts/{alert_id}/resolve")
def resolve_alert(
    alert_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(Role.ANALYST)),
):
    alert = db.query(Alert).filter(Alert.id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    site = db.query(Site).filter(Site.id == alert.site_id).first()
    require_same_org(site.org_id, current_user)
    alert.resolved = True
    db.commit()
    log_action(db, current_user.org_id, current_user.id, "resolve_alert", "alert", {"alert_id": alert_id})
    return {"status": "resolved"}


@router.get("/audit-logs")
def get_audit_logs(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(Role.ADMIN)),  # only Admin/Owner sees audit trail
):
    logs = (
        db.query(AuditLog)
        .filter(AuditLog.org_id == current_user.org_id)
        .order_by(AuditLog.created_at.desc())
        .limit(200)
        .all()
    )
    return [
        {
            "id": l.id, "action": l.action, "resource": l.resource,
            "details": l.details, "user_id": l.user_id, "created_at": l.created_at,
        }
        for l in logs
    ]
