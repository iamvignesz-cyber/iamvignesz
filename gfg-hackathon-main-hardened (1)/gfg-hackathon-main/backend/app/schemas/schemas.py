from datetime import datetime
from typing import Optional, Any
from pydantic import BaseModel, EmailStr, field_validator, Field

from app.core.net_security import UnsafeURLError, validate_public_url


class OrgCreate(BaseModel):
    org_name: str = Field(..., min_length=1, max_length=200)
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)

    @field_validator("password")
    @classmethod
    def password_strength(cls, v):
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        return v

    @field_validator("org_name")
    @classmethod
    def strip_org_name(cls, v):
        v = v.strip()
        if not v:
            raise ValueError("Organization name cannot be blank")
        return v


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., max_length=128)


class RefreshRequest(BaseModel):
    refresh_token: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class UserOut(BaseModel):
    id: str
    email: str
    role: str
    org_id: str

    class Config:
        from_attributes = True


class SiteCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    url: str = Field(..., min_length=1, max_length=2048)

    @field_validator("name")
    @classmethod
    def strip_name(cls, v):
        v = v.strip()
        if not v:
            raise ValueError("Site name cannot be blank")
        return v

    @field_validator("url")
    @classmethod
    def url_must_be_safe_format(cls, v):
        # Format-only check here (scheme, no credentials, not an obvious
        # private/loopback literal). DNS is re-resolved and re-checked at
        # scan time in app/services/scanner.py, since a hostname that was
        # public when the site was registered could later be repointed at
        # an internal address (DNS rebinding) — this check alone is not
        # sufficient on its own, only the first line of defense.
        try:
            validate_public_url(v)
        except UnsafeURLError as e:
            raise ValueError(str(e))
        return v


class SiteOut(BaseModel):
    id: str
    name: str
    url: str
    created_at: datetime

    class Config:
        from_attributes = True


class AlertOut(BaseModel):
    id: str
    site_id: str
    severity: str
    title: str
    description: Optional[str]
    resolved: bool
    created_at: datetime

    class Config:
        from_attributes = True


class ScanResult(BaseModel):
    scan: dict[str, Any]
    score: int
    ai_summary: Optional[dict[str, Any]] = None
