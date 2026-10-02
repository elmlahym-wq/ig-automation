import logging
import os
import secrets
import time

from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPBasic, HTTPBasicCredentials

log = logging.getLogger("auth")
_basic = HTTPBasic(auto_error=False)

# --- Brute-force protection (VULN-003): per-IP failure window ---
_WINDOW = 900          # 15 minutes
_MAX_FAILS = 10        # lock the IP after 10 failures within the window
_fails: dict[str, list[float]] = {}


def _is_production() -> bool:
    return os.getenv("ENV", "").lower() in ("production", "prod") or bool(os.getenv("RENDER"))


def _prune(now: float) -> None:
    if len(_fails) <= 5000:
        return
    for ip in list(_fails):
        if not [t for t in _fails[ip] if now - t < _WINDOW]:
            del _fails[ip]


def _rate_check(ip: str) -> None:
    now = time.monotonic()
    hits = [t for t in _fails.get(ip, ()) if now - t < _WINDOW]
    if len(hits) >= _MAX_FAILS:
        raise HTTPException(429, "Too many failed attempts, try again later")
    _fails[ip] = hits
    _prune(now)


def _deny(ip: str) -> None:
    _fails.setdefault(ip, []).append(time.monotonic())
    raise HTTPException(401, "Unauthorized", headers={"WWW-Authenticate": "Basic"})


def _eq(a: str, b: str) -> bool:
    # Compare as bytes: secrets.compare_digest(str, str) raises TypeError
    # (-> 500) when the attacker sends a non-ASCII header (VULN-006).
    return secrets.compare_digest(a.encode("utf-8"), b.encode("utf-8"))


def require_auth(request: Request, creds: HTTPBasicCredentials | None = Depends(_basic)):
    """Fail-closed in production; open only for local development (VULN-001)."""
    password = os.getenv("DASHBOARD_PASSWORD")
    if not password:
        if _is_production():
            log.error("DASHBOARD_PASSWORD not set — denying dashboard access (fail-closed)")
            raise HTTPException(503, "Dashboard password is not configured")
        log.warning("DASHBOARD_PASSWORD not set — dashboard is OPEN (development only)")
        return
    ip = request.client.host if request.client else "?"
    _rate_check(ip)
    user = os.getenv("DASHBOARD_USER", "admin")
    if not (creds and _eq(creds.username, user) and _eq(creds.password, password)):
        _deny(ip)
    _fails.pop(ip, None)  # successful login resets the counter
