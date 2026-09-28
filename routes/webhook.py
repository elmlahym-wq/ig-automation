import hashlib
import hmac
import logging
import os
from fastapi import APIRouter, BackgroundTasks, HTTPException, Query, Request
from fastapi.responses import PlainTextResponse
from sqlalchemy.exc import IntegrityError

import instagram
from database import SessionLocal
from models import Campaign, ProcessedComment, get_credentials

log = logging.getLogger("webhook")
router = APIRouter()


@router.get("/webhook/instagram")
def verify(mode: str = Query(None, alias="hub.mode"), token: str = Query(None, alias="hub.verify_token"),
           challenge: str = Query(None, alias="hub.challenge")):
    expected = os.getenv("WEBHOOK_VERIFY_TOKEN")
    if mode == "subscribe" and expected and hmac.compare_digest(token or "", expected):
        return PlainTextResponse(challenge)
    raise HTTPException(403, "Verification failed")


def _valid_signature(body: bytes, header: str | None) -> bool:
    secret = os.getenv("FACEBOOK_APP_SECRET", "")
    if not secret or not header or not header.startswith("sha256="):
        return False
    digest = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(digest, header.split("=", 1)[1])


@router.post("/webhook/instagram")
async def receive(request: Request, background: BackgroundTasks):
    body = await request.body()
    if not _valid_signature(body, request.headers.get("X-Hub-Signature-256")):
        raise HTTPException(403, "Invalid signature")
    payload = await request.json()
    for entry in payload.get("entry", []):
        for change in entry.get("changes", []):
            if change.get("field") == "comments":
                background.add_task(handle_comment, change.get("value", {}))
    return {"status": "received"}  # respond fast; work happens in background


def handle_comment(v: dict):
    comment_id, text = v.get("id"), (v.get("text") or "")
    author = v.get("from") or {}
    post_id = (v.get("media") or {}).get("id")
    if not (comment_id and post_id):
        return
    db = SessionLocal()
    try:
        creds = get_credentials(db)
        if author.get("id") and author.get("id") == creds["ig_account_id"]:
            return  # ignore our own replies (prevents loops)
        text_l = text.lower()
        campaign = next((c for c in db.query(Campaign).filter_by(post_id=str(post_id), active=True).all()
                         if any(k in text_l for k in c.keyword_list)), None)
        if not campaign:
            return
        # Deduplication: unique constraint makes this atomic
        record = ProcessedComment(comment_id=comment_id, campaign_id=campaign.id, status="processing")
        db.add(record)
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            log.info("Comment %s already processed", comment_id)
            return
        if not creds["access_token"] or not creds["ig_account_id"]:
            record.status = "error: credentials not configured"
            db.commit()
            return
        username = author.get("username", "")
        fmt = lambda s: s.replace("{username}", username)
        results = []
        for label, fn in (
            ("reply", lambda: instagram.reply_to_comment(comment_id, fmt(campaign.comment_reply), creds["access_token"])),
            ("dm", lambda: instagram.send_dm(creds["ig_account_id"], fmt(campaign.dm_message),
                                             creds["access_token"], comment_id=comment_id)),
        ):
            try:
                fn()
                results.append(f"{label}:ok")
            except Exception as e:  # one failure shouldn't block the other action
                log.error("%s failed for comment %s: %s", label, comment_id, e)
                results.append(f"{label}:error({str(e)[:80]})")
        record.status = " ".join(results)
        db.commit()
    finally:
        db.close()
