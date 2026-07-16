from datetime import datetime, timedelta
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import get_db
from app.models.models import User, Role

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def create_token(subject: str, expires_delta: timedelta, token_type: str = "access") -> str:
    expire = datetime.utcnow() + expires_delta
    payload = {"sub": subject, "exp": expire, "type": token_type}
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def create_access_token(user_id: str) -> str:
    return create_token(user_id, timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES), "access")


def create_refresh_token(user_id: str) -> str:
    return create_token(user_id, timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS), "refresh")


def decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    payload = decode_token(token)
    if payload.get("type") != "access":
        raise HTTPException(status_code=401, detail="Invalid token type")
    user_id = payload.get("sub")
    user = db.query(User).filter(User.id == user_id).first()
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="User not found or inactive")
    return user


# ROLE HIERARCHY: enforced server-side on every route that needs it — never trust the frontend.
ROLE_RANK = {Role.VIEWER: 0, Role.ANALYST: 1, Role.ADMIN: 2, Role.OWNER: 3}


def require_role(minimum_role: Role):
    """Dependency factory: raises 403 unless current_user's role >= minimum_role.
    This is enforced at the API layer, independent of any UI hiding, to prevent
    privilege-escalation (a Viewer JWT cannot reach Admin routes by calling the API directly)."""

    def dependency(current_user: User = Depends(get_current_user)) -> User:
        if ROLE_RANK[current_user.role] < ROLE_RANK[minimum_role]:
            raise HTTPException(status_code=403, detail="Insufficient role for this action")
        return current_user

    return dependency


def require_same_org(resource_org_id: str, current_user: User):
    """Cross-tenant isolation check — prevents IDOR across organizations.
    Call this explicitly whenever fetching a resource by ID."""
    if str(current_user.org_id) != str(resource_org_id):
        raise HTTPException(status_code=404, detail="Resource not found")


# Generated once at import time (not a real credential) purely so the
# "user not found" login path can run a real bcrypt verify against it —
# see constant_time_dummy_hash_check() below.
_DUMMY_HASH = pwd_context.hash("dummy-password-for-timing-parity")


def constant_time_dummy_hash_check() -> None:
    """Run a bcrypt verify against a fixed dummy hash. Call this on the
    "user not found" path in login so that the response-time difference
    between "no such user" and "wrong password" doesn't leak which case
    occurred (timing side-channel on top of the already-identical error
    message and status code)."""
    pwd_context.verify("dummy-password-for-timing-parity", _DUMMY_HASH)
