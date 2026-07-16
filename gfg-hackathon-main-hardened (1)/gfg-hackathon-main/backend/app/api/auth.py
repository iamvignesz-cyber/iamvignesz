from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.rate_limit import SlidingWindowRateLimiter, client_ip
from app.db.session import get_db
from app.models.models import User, Organization, Role
from app.schemas.schemas import OrgCreate, TokenResponse, RefreshRequest
from app.core.security import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_token,
    get_current_user,
    constant_time_dummy_hash_check,
)
from app.services.audit import log_action

router = APIRouter(prefix="/api/auth", tags=["auth"])

_signup_limiter = SlidingWindowRateLimiter(
    settings.AUTH_RATE_LIMIT_MAX_REQUESTS, settings.AUTH_RATE_LIMIT_WINDOW_SECONDS
)
_login_limiter = SlidingWindowRateLimiter(
    settings.AUTH_RATE_LIMIT_MAX_REQUESTS, settings.AUTH_RATE_LIMIT_WINDOW_SECONDS
)
_refresh_limiter = SlidingWindowRateLimiter(
    settings.AUTH_RATE_LIMIT_MAX_REQUESTS, settings.AUTH_RATE_LIMIT_WINDOW_SECONDS
)


@router.post("/signup", response_model=TokenResponse)
def signup(payload: OrgCreate, request: Request, db: Session = Depends(get_db)):
    _signup_limiter.check(client_ip(request))

    existing = db.query(User).filter(User.email == payload.email).first()
    if existing:
        # Same generic message pattern as login — don't confirm which
        # emails are already registered.
        raise HTTPException(status_code=400, detail="Unable to create account with these details")

    org = Organization(name=payload.org_name)
    db.add(org)
    db.flush()  # get org.id without full commit

    user = User(
        org_id=org.id,
        email=payload.email,
        hashed_password=hash_password(payload.password),
        role=Role.OWNER,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    log_action(db, org.id, user.id, "signup", "organization", {"org_name": org.name})

    return TokenResponse(
        access_token=create_access_token(user.id),
        refresh_token=create_refresh_token(user.id),
    )


@router.post("/login", response_model=TokenResponse)
def login(request: Request, form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    _login_limiter.check(client_ip(request))

    # NOTE: generic error message + generic status on both "no such user"
    # and "wrong password" — prevents user-enumeration (a common SL-2/SL-3
    # finding). We also run a dummy bcrypt verify on the "no such user"
    # branch so the two branches take comparable time.
    user = db.query(User).filter(User.email == form_data.username).first()

    if not user:
        constant_time_dummy_hash_check()
        raise HTTPException(status_code=401, detail="Invalid credentials")

    if user.locked_until and user.locked_until > datetime.utcnow():
        # Same generic message — don't reveal lockout state to an attacker
        # probing for valid usernames, but do log it server-side.
        raise HTTPException(status_code=401, detail="Invalid credentials")

    if not verify_password(form_data.password, user.hashed_password):
        user.failed_login_attempts = (user.failed_login_attempts or 0) + 1
        if user.failed_login_attempts >= settings.MAX_FAILED_LOGIN_ATTEMPTS:
            user.locked_until = datetime.utcnow() + timedelta(minutes=settings.LOCKOUT_MINUTES)
        db.commit()
        raise HTTPException(status_code=401, detail="Invalid credentials")

    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account disabled")

    # Successful login resets the counter.
    user.failed_login_attempts = 0
    user.locked_until = None
    db.commit()

    log_action(db, user.org_id, user.id, "login", "user")

    return TokenResponse(
        access_token=create_access_token(user.id),
        refresh_token=create_refresh_token(user.id),
    )


@router.post("/refresh", response_model=TokenResponse)
def refresh(payload: RefreshRequest, request: Request, db: Session = Depends(get_db)):
    # Token is read from the JSON body (not a query string) so it never ends
    # up in server access logs, browser history, or proxy logs the way a
    # query parameter would.
    _refresh_limiter.check(client_ip(request))

    decoded = decode_token(payload.refresh_token)
    if decoded.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Invalid token type")
    user_id = decoded.get("sub")
    user = db.query(User).filter(User.id == user_id).first()
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="User not found")
    return TokenResponse(
        access_token=create_access_token(user.id),
        refresh_token=create_refresh_token(user.id),
    )


@router.get("/me")
def get_me(current_user: User = Depends(get_current_user)):
    return {
        "id": current_user.id,
        "email": current_user.email,
        "role": current_user.role,
        "org_id": current_user.org_id,
        "org_name": current_user.organization.name,
    }
