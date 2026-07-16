import os
import secrets
from pydantic_settings import BaseSettings

# Values that must never be used as the real JWT signing secret.
_INSECURE_JWT_SECRETS = {
    "",
    "change-me-in-prod",
    "replace-with-a-long-random-value",
    "secret",
    "changeme",
}


class Settings(BaseSettings):
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")  # "development" | "production"

    DATABASE_URL: str = os.getenv(
        "DATABASE_URL", "postgresql://postgres:postgres@db:5432/sysiege"
    )

    JWT_SECRET: str = os.getenv("JWT_SECRET", "change-me-in-prod")
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    AI_PROVIDER: str = os.getenv("AI_PROVIDER", "gemini")  # disclosed in README
    AI_MODEL: str = os.getenv("AI_MODEL", "gemini-2.0-flash")
    AI_API_KEY: str = os.getenv("AI_API_KEY", "")

    # --- Brute-force / account lockout ---
    MAX_FAILED_LOGIN_ATTEMPTS: int = int(os.getenv("MAX_FAILED_LOGIN_ATTEMPTS", "5"))
    LOCKOUT_MINUTES: int = int(os.getenv("LOCKOUT_MINUTES", "15"))

    # --- Rate limiting (in-process sliding window; see app/core/rate_limit.py) ---
    AUTH_RATE_LIMIT_MAX_REQUESTS: int = int(os.getenv("AUTH_RATE_LIMIT_MAX_REQUESTS", "10"))
    AUTH_RATE_LIMIT_WINDOW_SECONDS: int = int(os.getenv("AUTH_RATE_LIMIT_WINDOW_SECONDS", "60"))
    SCAN_RATE_LIMIT_MAX_REQUESTS: int = int(os.getenv("SCAN_RATE_LIMIT_MAX_REQUESTS", "10"))
    SCAN_RATE_LIMIT_WINDOW_SECONDS: int = int(os.getenv("SCAN_RATE_LIMIT_WINDOW_SECONDS", "60"))

    # --- SSRF-safe scanner limits ---
    SCAN_CONNECT_TIMEOUT_SECONDS: float = float(os.getenv("SCAN_CONNECT_TIMEOUT_SECONDS", "5"))
    SCAN_TOTAL_TIMEOUT_SECONDS: float = float(os.getenv("SCAN_TOTAL_TIMEOUT_SECONDS", "10"))
    SCAN_MAX_RESPONSE_BYTES: int = int(os.getenv("SCAN_MAX_RESPONSE_BYTES", str(5 * 1024 * 1024)))  # 5 MB
    SCAN_MAX_REDIRECTS: int = int(os.getenv("SCAN_MAX_REDIRECTS", "5"))

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()


def assert_production_secrets_are_safe() -> None:
    """Fail fast at startup instead of silently running with a guessable JWT
    secret. Called once from the FastAPI startup event in main.py."""
    if settings.JWT_SECRET in _INSECURE_JWT_SECRETS or len(settings.JWT_SECRET) < 32:
        if settings.ENVIRONMENT.lower() == "production":
            raise RuntimeError(
                "Refusing to start: JWT_SECRET is missing, a known placeholder, or too short "
                "(<32 chars) while ENVIRONMENT=production. Set a long random JWT_SECRET, e.g. "
                "one generated with: python -c \"import secrets; print(secrets.token_urlsafe(64))\" "
                f"-> example (do NOT reuse this one): {secrets.token_urlsafe(32)}"
            )
