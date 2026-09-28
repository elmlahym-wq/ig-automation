import os
import secrets
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBasic, HTTPBasicCredentials

_basic = HTTPBasic(auto_error=False)


def require_auth(creds: HTTPBasicCredentials | None = Depends(_basic)):
    """No-op unless DASHBOARD_PASSWORD is set."""
    password = os.getenv("DASHBOARD_PASSWORD")
    if not password:
        return
    user = os.getenv("DASHBOARD_USER", "admin")
    ok = creds and secrets.compare_digest(creds.username, user) and secrets.compare_digest(creds.password, password)
    if not ok:
        raise HTTPException(401, "Unauthorized", headers={"WWW-Authenticate": "Basic"})
