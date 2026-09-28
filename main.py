import os
from fastapi import FastAPI
from database import engine, Base
import models
from routes import webhook, dashboard

# إنشاء جميع الجداول تلقائياً في قاعدة البيانات
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Instagram Comment-to-DM")

# ربط الـ Routers
app.include_router(webhook.router)
app.include_router(dashboard.router, prefix="/dashboard")
