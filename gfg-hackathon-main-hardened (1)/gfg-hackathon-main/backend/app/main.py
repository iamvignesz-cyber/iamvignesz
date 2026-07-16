import logging
import os

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import settings, assert_production_secrets_are_safe
from app.db.session import Base, engine
from app.api import auth, sites, scan, alerts

logger = logging.getLogger("web_sentinel")

app = FastAPI(title="Website Defacement & Vulnerability Assessment Platform")

# Strict CORS — only allow the configured frontend origin(s), never "*".
# Blank entries (e.g. a stray trailing comma) are filtered out so they can't
# accidentally slip through as an empty-string origin.
ALLOWED_ORIGINS = [o.strip() for o in os.getenv("ALLOWED_ORIGINS", "http://localhost:3000").split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)


@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Content-Security-Policy"] = "default-src 'self'"
    response.headers["Permissions-Policy"] = "geolocation=(), camera=(), microphone=()"
    # HSTS only makes sense once served over HTTPS (harmless but pointless
    # to advertise over plain HTTP) — gate it on ENVIRONMENT=production,
    # where the deployment is expected to sit behind TLS termination.
    if settings.ENVIRONMENT.lower() == "production":
        response.headers["Strict-Transport-Security"] = "max-age=63072000; includeSubDomains"
    return response


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    # Never leak stack traces / internal error strings to the client — log
    # them server-side (with request path for correlation) and return a
    # generic 500 instead. FastAPI's own HTTPException handling is
    # untouched by this (it only catches what would otherwise be an
    # unhandled 500).
    logger.exception("Unhandled exception on %s %s", request.method, request.url.path)
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})


@app.on_event("startup")
def on_startup():
    # Fail fast rather than silently running production with a guessable
    # JWT secret (see app/core/config.py for what counts as "weak").
    assert_production_secrets_are_safe()
    # For hackathon speed we create tables directly; use Alembic migrations for real prod use.
    Base.metadata.create_all(bind=engine)


@app.get("/api/health")
def health():
    return {"status": "ok"}


app.include_router(auth.router)
app.include_router(sites.router)
app.include_router(scan.router)
app.include_router(alerts.router)
