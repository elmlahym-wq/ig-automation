from pathlib import Path
from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from routes.auth import require_auth

BASE_DIR = Path(__file__).resolve().parent.parent
router = APIRouter(dependencies=[Depends(require_auth)])
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

SETTINGS_HTML = """{% extends "base.html" %}
{% block title %}Settings{% endblock %}
{% block content %}
<h1>Instagram connection</h1>
<p class="muted">Credentials are stored on the server and never sent back to your browser.</p>
<form id="settings-form" class="panel">
  <label>Access token
    <input type="password" name="access_token" autocomplete="off" placeholder="Paste a long-lived token">
    <small id="token-hint" class="muted"></small>
  </label>
  <label>Facebook Page ID <input name="page_id" autocomplete="off"></label>
  <label>Instagram business account ID <input name="ig_account_id" autocomplete="off"></label>
  <button class="btn primary">Save settings</button>
</form>
{% endblock %}
"""


@router.get("/")
@router.get("/dashboard")
def index():
    return RedirectResponse("/dashboard/campaigns")


@router.get("/dashboard/settings")
def settings(request: Request):
    tpl = templates.env.from_string(SETTINGS_HTML)
    return HTMLResponse(tpl.render(request=request, page="settings"))


@router.get("/dashboard/campaigns")
def campaigns(request: Request):
    return templates.TemplateResponse(request, "campaigns.html", {"page": "campaigns"})
