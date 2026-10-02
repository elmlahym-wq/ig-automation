"""Instagram Graph API client (official API only). Retries with backoff on rate limits / 5xx."""
import logging
import os
import time
import httpx

log = logging.getLogger("instagram")
GRAPH = f"https://graph.facebook.com/{os.getenv('GRAPH_API_VERSION', 'v21.0')}"
RATE_LIMIT_CODES = {4, 17, 32, 613, 80002, 80006}
MAX_RETRIES = 4


class InstagramError(Exception):
    pass


def _request(method: str, path: str, token: str, params=None, json=None):
    params = dict(params or {})
    params["access_token"] = token
    for attempt in range(MAX_RETRIES + 1):
        try:
            r = _send(method, path, dict(params), json)
        except httpx.HTTPError as e:
            log.warning("Network error on %s %s: %s", method, path, e)
            r = None
        if r is not None:
            try:
                body = r.json() if r.content else {}
            except ValueError:
                body = {"error": {"message": f"Non-JSON response (HTTP {r.status_code})"}}
            log.info("%s %s -> %s %s", method, path, r.status_code, str(body)[:300])
            if r.status_code < 400:
                return body
            code = (body.get("error") or {}).get("code")
            retryable = r.status_code in (429, 500, 502, 503, 504) or code in RATE_LIMIT_CODES
            if not retryable or attempt == MAX_RETRIES:
                raise InstagramError((body.get("error") or {}).get("message", f"HTTP {r.status_code}"))
        elif attempt == MAX_RETRIES:
            raise InstagramError("Network error contacting Instagram")
        delay = 2 ** attempt * 2
        log.warning("Retrying in %ss (attempt %s)", delay, attempt + 1)
        time.sleep(delay)


def _send(method, path, params, json):
    if method == "GET":
        return httpx.get(f"{GRAPH}/{path}", params=params, timeout=20)
    if json is not None:  # access_token goes in query string, body is JSON
        token = params.pop("access_token")
        return httpx.post(f"{GRAPH}/{path}", params={"access_token": token}, json=json, timeout=20)
    return httpx.post(f"{GRAPH}/{path}", data=params, timeout=20)


def reply_to_comment(comment_id: str, message: str, token: str) -> dict:
    """Post a public reply under a comment."""
    return _request("POST", f"{comment_id}/replies", token, params={"message": message})


def send_dm(ig_account_id: str, message: str, token: str,
            instagram_user_id: str | None = None, comment_id: str | None = None) -> dict:
    """Send a DM. If comment_id is given, sends a *private reply* to that comment (the only way to
    message someone who hasn't messaged you first; allowed once per comment within 7 days).
    Otherwise sends to instagram_user_id (requires an open 24h messaging window)."""
    if comment_id:
        recipient = {"comment_id": comment_id}
    elif instagram_user_id:
        recipient = {"id": instagram_user_id}
    else:
        raise InstagramError("send_dm needs comment_id or instagram_user_id")
    return _request("POST", f"{ig_account_id}/messages", token,
                    json={"recipient": recipient, "message": {"text": message}})


def get_post_details(post_id: str, token: str) -> dict:
    """Fetch thumbnail + caption for display in the dashboard."""
    d = _request("GET", post_id, token,
                 params={"fields": "id,caption,media_type,media_url,thumbnail_url,permalink"})
    return {
        "id": d.get("id"),
        "caption": d.get("caption", ""),
        "thumbnail_url": d.get("thumbnail_url") or d.get("media_url"),
        "permalink": d.get("permalink"),
        "media_type": d.get("media_type"),
    }
