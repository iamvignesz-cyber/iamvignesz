from sqlalchemy.orm import Session
from app.models.models import AuditLog


def log_action(db: Session, org_id: str, user_id: str, action: str, resource: str = None, details: dict = None):
    entry = AuditLog(org_id=org_id, user_id=user_id, action=action, resource=resource, details=details or {})
    db.add(entry)
    db.commit()
    return entry
