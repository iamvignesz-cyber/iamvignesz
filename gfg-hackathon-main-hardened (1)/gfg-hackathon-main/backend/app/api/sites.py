from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.models import Site, User, Role
from app.schemas.schemas import SiteCreate, SiteOut
from app.core.security import get_current_user, require_role, require_same_org
from app.services.audit import log_action

router = APIRouter(prefix="/api/sites", tags=["sites"])


@router.get("", response_model=list[SiteOut])
def list_sites(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    # Scoped strictly to the caller's org — prevents cross-tenant IDOR (e.g. incrementing IDs).
    return db.query(Site).filter(Site.org_id == current_user.org_id).all()


@router.post("", response_model=SiteOut)
def create_site(
    payload: SiteCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(Role.ANALYST)),  # Viewer cannot create
):
    site = Site(org_id=current_user.org_id, name=payload.name, url=payload.url)
    db.add(site)
    db.commit()
    db.refresh(site)
    log_action(db, current_user.org_id, current_user.id, "create_site", "site", {"url": payload.url})
    return site


@router.get("/{site_id}", response_model=SiteOut)
def get_site(site_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    site = db.query(Site).filter(Site.id == site_id).first()
    if not site:
        raise HTTPException(status_code=404, detail="Site not found")
    require_same_org(site.org_id, current_user)  # explicit tenant-isolation check
    return site


@router.delete("/{site_id}")
def delete_site(
    site_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(Role.ADMIN)),  # only Admin/Owner can delete
):
    site = db.query(Site).filter(Site.id == site_id).first()
    if not site:
        raise HTTPException(status_code=404, detail="Site not found")
    require_same_org(site.org_id, current_user)
    db.delete(site)
    db.commit()
    log_action(db, current_user.org_id, current_user.id, "delete_site", "site", {"site_id": site_id})
    return {"status": "deleted"}
