import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    Column, String, DateTime, ForeignKey, Text, Enum, Boolean, JSON, Integer
)
try:
    from sqlalchemy.dialects.postgresql import UUID
except ImportError:
    class UUID(String):
        def __init__(self, *args, **kwargs):
            kwargs.pop("as_uuid", None)
            super().__init__(*args, **kwargs)

from sqlalchemy.orm import relationship

from app.db.session import Base


def gen_uuid():
    return str(uuid.uuid4())


class Role(str, enum.Enum):
    OWNER = "owner"
    ADMIN = "admin"
    ANALYST = "analyst"
    VIEWER = "viewer"


class Organization(Base):
    __tablename__ = "organizations"
    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    name = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    users = relationship("User", back_populates="organization")
    sites = relationship("Site", back_populates="organization")


class User(Base):
    __tablename__ = "users"
    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    org_id = Column(UUID(as_uuid=False), ForeignKey("organizations.id"), nullable=False)
    email = Column(String, unique=True, nullable=False, index=True)
    hashed_password = Column(String, nullable=False)
    role = Column(Enum(Role), default=Role.VIEWER, nullable=False)
    is_active = Column(Boolean, default=True)
    failed_login_attempts = Column(Integer, default=0, nullable=False)
    locked_until = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    organization = relationship("Organization", back_populates="users")


class Site(Base):
    __tablename__ = "sites"
    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    org_id = Column(UUID(as_uuid=False), ForeignKey("organizations.id"), nullable=False)
    url = Column(String, nullable=False)
    name = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    organization = relationship("Organization", back_populates="sites")
    snapshots = relationship("Snapshot", back_populates="site")


class Snapshot(Base):
    __tablename__ = "snapshots"
    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    site_id = Column(UUID(as_uuid=False), ForeignKey("sites.id"), nullable=False)
    html_hash = Column(String, nullable=False)
    dom_text = Column(Text, nullable=True)
    headers = Column(JSON, nullable=True)
    scan_result = Column(JSON, nullable=True)
    security_score = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    site = relationship("Site", back_populates="snapshots")


class Alert(Base):
    __tablename__ = "alerts"
    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    site_id = Column(UUID(as_uuid=False), ForeignKey("sites.id"), nullable=False)
    severity = Column(String, nullable=False)  # SL-1, SL-2, SL-3 style or info/warn/critical
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    ai_summary = Column(Text, nullable=True)
    resolved = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class AuditLog(Base):
    __tablename__ = "audit_logs"
    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    org_id = Column(UUID(as_uuid=False), ForeignKey("organizations.id"), nullable=False)
    user_id = Column(UUID(as_uuid=False), ForeignKey("users.id"), nullable=True)
    action = Column(String, nullable=False)
    resource = Column(String, nullable=True)
    details = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
