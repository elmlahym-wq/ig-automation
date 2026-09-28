import os
from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from database import get_db
import models

router = APIRouter()
templates = Jinja2Templates(directory="templates")

@router.get("", response_class=HTMLResponse)
@router.get("/", response_class=HTMLResponse)
@router.get("/campaigns", response_class=HTMLResponse)
async def dashboard_campaigns(request: Request, db: Session = Depends(get_db)):
    try:
        campaigns = db.query(models.Campaign).all()
    except Exception:
        campaigns = []
    return templates.TemplateResponse(
        "campaigns.html",
        {"request": request, "campaigns": campaigns, "page": "campaigns"}
    )

@router.get("/settings", response_class=HTMLResponse)
async def settings(request: Request, db: Session = Depends(get_db)):
    try:
        settings_data = db.query(models.Settings).first()
    except Exception:
        settings_data = None

    return templates.TemplateResponse(
        "settings.html",
        {"request": request, "settings": settings_data, "page": "settings"}
    )
