import os
from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime
from database import Base


class Config(Base):
    __tablename__ = "config"
    id = Column(Integer, primary_key=True)
    access_token = Column(Text, default="")
    page_id = Column(String(64), default="")
    ig_account_id = Column(String(64), default="")
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Campaign(Base):
    __tablename__ = "campaigns"
    id = Column(Integer, primary_key=True)
    name = Column(String(120), default="")
    post_id = Column(String(64), index=True, nullable=False)
    keywords = Column(Text, nullable=False)  # comma-separated
    comment_reply = Column(Text, nullable=False)
    dm_message = Column(Text, nullable=False)
    active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    @property
    def keyword_list(self):
        return [k.strip().lower() for k in (self.keywords or "").split(",") if k.strip()]


class ProcessedComment(Base):
    __tablename__ = "processed_comments"
    id = Column(Integer, primary_key=True)
    comment_id = Column(String(64), unique=True, index=True, nullable=False)
    campaign_id = Column(Integer, nullable=True)
    status = Column(String(255), default="")
    processed_at = Column(DateTime, default=datetime.utcnow)


def get_credentials(db):
    """DB values (set via dashboard) take priority; .env values are the fallback."""
    c = db.query(Config).first()
    return {
        "access_token": (c.access_token if c and c.access_token else os.getenv("INSTAGRAM_ACCESS_TOKEN", "")),
        "page_id": (c.page_id if c else "") or "",
        "ig_account_id": (c.ig_account_id if c and c.ig_account_id else os.getenv("INSTAGRAM_BUSINESS_ACCOUNT_ID", "")),
    }
