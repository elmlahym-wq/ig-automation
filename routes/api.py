from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

import instagram
from database import get_db
from models import Campaign, Config, get_credentials
from routes.auth import require_auth

router = APIRouter(prefix="/api", dependencies=[Depends(require_auth)])


class ConfigIn(BaseModel):
    access_token: str = ""  # blank = keep existing
    page_id: str = ""
    ig_account_id: str = ""


class CampaignIn(BaseModel):
    name: str = ""
    post_id: str = Field(min_length=1)
    keywords: str = Field(min_length=1)
    comment_reply: str = Field(min_length=1)
    dm_message: str = Field(min_length=1)
    active: bool = True


def campaign_out(c: Campaign):
    return {"id": c.id, "name": c.name, "post_id": c.post_id, "keywords": c.keywords,
            "comment_reply": c.comment_reply, "dm_message": c.dm_message, "active": c.active}


@router.get("/config")
def get_config(db: Session = Depends(get_db)):
    cr = get_credentials(db)  # the token itself is never returned
    t = cr["access_token"]
    return {"page_id": cr["page_id"], "ig_account_id": cr["ig_account_id"],
            "token_set": bool(t), "token_hint": ("…" + t[-4:]) if t else ""}


@router.put("/config")
def save_config(body: ConfigIn, db: Session = Depends(get_db)):
    c = db.query(Config).first() or Config()
    if body.access_token.strip():
        c.access_token = body.access_token.strip()
    c.page_id, c.ig_account_id = body.page_id.strip(), body.ig_account_id.strip()
    db.add(c)
    db.commit()
    return {"ok": True}


@router.get("/post/{post_id}")
def post_preview(post_id: str, db: Session = Depends(get_db)):
    token = get_credentials(db)["access_token"]
    if not token:
        raise HTTPException(400, "Save your access token in Settings first")
    try:
        return instagram.get_post_details(post_id, token)
    except instagram.InstagramError as e:
        raise HTTPException(400, str(e))


@router.get("/campaigns")
def list_campaigns(db: Session = Depends(get_db)):
    return [campaign_out(c) for c in db.query(Campaign).order_by(Campaign.id.desc())]


@router.post("/campaigns", status_code=201)
def create_campaign(body: CampaignIn, db: Session = Depends(get_db)):
    c = Campaign(**body.model_dump())
    db.add(c)
    db.commit()
    return campaign_out(c)


def _get(db, cid):
    c = db.get(Campaign, cid)
    if not c:
        raise HTTPException(404, "Campaign not found")
    return c


@router.put("/campaigns/{cid}")
def update_campaign(cid: int, body: CampaignIn, db: Session = Depends(get_db)):
    c = _get(db, cid)
    for k, v in body.model_dump().items():
        setattr(c, k, v)
    db.commit()
    return campaign_out(c)


@router.post("/campaigns/{cid}/toggle")
def toggle_campaign(cid: int, db: Session = Depends(get_db)):
    c = _get(db, cid)
    c.active = not c.active
    db.commit()
    return campaign_out(c)


@router.delete("/campaigns/{cid}", status_code=204)
def delete_campaign(cid: int, db: Session = Depends(get_db)):
    db.delete(_get(db, cid))
    db.commit()
