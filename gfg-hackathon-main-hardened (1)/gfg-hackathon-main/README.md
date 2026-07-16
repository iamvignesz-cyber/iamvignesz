# Web Sentinel — Website Defacement & Vulnerability Assessment Platform

Built for System Siege (PS-005, Cyber Security & Web Mining domain).

## What it does
Monitors registered websites, detects content/defacement changes between scans,
runs a deterministic HTTP/TLS security check (headers, CORS, cookies, SSL expiry),
computes a transparent 0–100 security score, and (optionally) asks an LLM to turn
that real scan data into a plain-language executive/technical summary.

## AI disclosure (BYOK)
- **Provider:** Google Gemini
- **Model:** `gemini-2.0-flash` (configurable via `AI_MODEL` env var)
- **What it's used for:** ONLY summarizing/prioritizing findings already produced
  by the deterministic scanner (`backend/app/services/scanner.py`). It never
  invents vulnerabilities and never executes code.
- Set your own key in `backend/.env` as `AI_API_KEY`. Without a key set, the
  summary endpoint returns a clear "not configured" message rather than faking output.

## Stack
- Frontend: Next.js (JavaScript)
- Backend: FastAPI (Python)
- DB: PostgreSQL
- Auth: JWT (access + refresh), bcrypt password hashing, RBAC (Owner/Admin/Analyst/Viewer)

## Roles
| Role | Can view | Can add/scan sites | Can delete sites | Can view audit log |
|---|---|---|---|---|
| Viewer | ✅ | ❌ | ❌ | ❌ |
| Analyst | ✅ | ✅ | ❌ | ❌ |
| Admin | ✅ | ✅ | ✅ | ✅ |
| Owner | ✅ | ✅ | ✅ | ✅ |

RBAC is enforced **server-side on every route** (`require_role` dependency in
`app/core/security.py`), not just hidden in the UI — a Viewer's JWT cannot reach
Admin-only endpoints by calling the API directly. Cross-tenant access is blocked
via explicit `require_same_org` checks on every resource fetch by ID.

## Local setup
```bash
cp backend/.env.example backend/.env
# edit backend/.env and set AI_API_KEY, JWT_SECRET

docker compose up --build
```
- Backend: http://localhost:8000/docs (Swagger UI)
- Frontend: http://localhost:3000

## Known limitations (honest, not hidden)
- Screenshot/visual diffing (Playwright-based pixel comparison) is not yet wired
  in — current defacement detection is HTML-hash-based only. This is the first
  thing to add with remaining build time.
- No email verification / password reset flow yet.
- Migrations use `Base.metadata.create_all` for speed; swap to Alembic for
  real schema evolution. Because of this, the account-lockout columns added
  to `users` won't appear on an *existing* database automatically — see
  `backend/app/db/manual_migration_lockout_fields.sql`.
- No automated test suite included yet.
- Rate limiting (`backend/app/core/rate_limit.py`) is in-process/in-memory.
  Correct for the single-container deployment this repo ships, but if you
  scale to multiple backend workers/containers without a shared store, each
  process enforces its own limit independently — swap in a Redis-backed
  counter before doing that.
- No JWT revocation/deny-list — a logged-out access token remains valid
  until it expires (30 min by default). Acceptable for the short token TTL
  here; add a revocation store if you need immediate logout.
- Frontend `next` version (14.2.15, see `frontend/package-lock.json`) has a
  known upstream advisory — worth bumping, out of scope for this pass since
  it's a frontend dependency, not backend logic.

## Security notes for the attack/defend phase
Things we already checked ourselves (self-attack before submission):
- Viewer JWT cannot call POST /api/sites or DELETE /api/sites/{id} (403)
- Site/alert fetch-by-ID checks org ownership, not just existence (404 on cross-org access)
- CORS is restricted to `ALLOWED_ORIGINS`, never `*`
- Login returns identical error + comparable response time for "no such user"
  and "wrong password" (no user enumeration via message or timing)
- No secrets committed — `.env` is gitignored, `.env.example` has placeholders only
- **SSRF**: the scanner fetches an attacker-influenceable URL (any registered
  site). `backend/app/core/net_security.py` + the SSRF-aware fetch in
  `backend/app/services/scanner.py` block private/loopback/link-local/cloud-
  metadata addresses, re-validate DNS at fetch time (not just at site-creation
  time), pin the actual HTTP connection to the pre-validated IP to close the
  DNS-rebinding TOCTOU window, and re-validate every redirect hop.
- **Brute force**: failed logins are rate-limited per-IP and the account
  locks for `LOCKOUT_MINUTES` after `MAX_FAILED_LOGIN_ATTEMPTS` (both
  configurable). Signup/refresh/scan-trigger are also rate-limited.
- **Token hygiene**: `/api/auth/refresh` takes the refresh token in the
  request body (previously a query parameter, which risked it landing in
  server/proxy access logs and browser history).
- **Fail-fast secrets**: startup refuses to boot with `ENVIRONMENT=production`
  and a missing/placeholder/short `JWT_SECRET`, instead of quietly running
  with a guessable one.
- **Error handling**: a catch-all exception handler returns a generic 500
  instead of leaking stack traces/internal error text; the AI-summary call
  degrades gracefully (never turns a successful scan into a failed request).
- **Input validation**: site URLs must be `http(s)://`, cannot embed
  credentials, and reject obvious private/loopback IP literals at
  submission time (defense-in-depth on top of the scan-time SSRF check);
  name/email/password fields are length-capped.
