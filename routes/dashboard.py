from pathlib import Path
from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from routes.auth import require_auth

BASE_DIR = Path(__file__).resolve().parent.parent
router = APIRouter(dependencies=[Depends(require_auth)])
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))
