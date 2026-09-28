from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from routes.auth import require_auth

router = APIRouter(dependencies=[Depends(require_auth)])
templates = Jinja2Templates(directory="templates")


@router.get("/")
@router.get("/dashboard")
def index():
    return RedirectResponse("/dashboard/campaigns")


@router.get("/dashboard/settings")
def settings(request: Request):
    return templates.TemplateResponse(request, "settings.html", {"page": "settings"})


@router.get("/dashboard/campaigns")
def campaigns(request: Request):
    return templates.TemplateResponse(request, "campaigns.html", {"page": "campaigns"})
