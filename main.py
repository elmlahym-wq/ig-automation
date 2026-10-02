import logging
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from database import Base, engine
import models  # noqa: F401  (registers tables)
from routes import api, dashboard, webhook

BASE_DIR = Path(__file__).resolve().parent

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Comment-to-DM Automation")
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")
app.include_router(webhook.router)
app.include_router(api.router)
app.include_router(dashboard.router)


@app.get("/health")
def health():
    return {"status": "ok"}
