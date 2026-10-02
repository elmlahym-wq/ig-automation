# Instagram Comment-to-DM Automation

When someone comments a keyword on a tracked post, this app **replies publicly to the comment** and **sends the commenter a private DM**. Built on FastAPI + **Supabase Postgres** (SQLite for local dev) and the official Instagram Graph API only.

## Run locally

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env        # fill in values (see setup below)
uvicorn main:app --reload
```
Open http://localhost:8000/dashboard. Meta must reach your webhook over public HTTPS, so for local testing use a tunnel (`ngrok http 8000`) and use that URL below.

Docker: `docker build -t comment-dm . && docker run -p 8000:8000 --env-file .env comment-dm`

## Database (Supabase)

The app talks to any PostgreSQL database through `DATABASE_URL`. Recommended: **Supabase**.

1. Create a project at [supabase.com/dashboard](https://supabase.com/dashboard) → **New project**.
2. Copy the connection string: click **Connect → Session pooler** and copy it:
   ```
   postgresql://postgres.<PROJECT_REF>:<PASSWORD>@aws-<INDEX>-<REGION>.pooler.supabase.com:5432/postgres
   ```
   > Copy the host from the dialog — the `aws-<INDEX>` number is a cluster index that
   > **cannot be guessed from the region** (e.g. our project uses `aws-1-eu-central-1`, not `aws-0`).
3. Put it in `.env` (or in your host's `DATABASE_URL` env var).

Tables (`config`, `campaigns`, `processed_comments`) are created automatically on first startup. The token you paste in Dashboard → Settings is stored in the `config` row.

> Local dev works out of the box without Supabase: the default `DATABASE_URL=sqlite:///./app.db` is used.

## Deploy

- **Railway:** push to GitHub → New Project → Deploy from repo (`railway.toml` is picked up). Add the env vars: `DATABASE_URL` (Supabase), `FACEBOOK_APP_SECRET`, `WEBHOOK_VERIFY_TOKEN`, `DASHBOARD_PASSWORD`.
- **Render:** New → Blueprint → select the repo (`render.yaml` prompts for the same env vars). No disk needed — the database lives in Supabase.

Set `DASHBOARD_PASSWORD` in production, otherwise anyone with the URL can open your dashboard. When set, `/dashboard` and `/api` require HTTP Basic auth (user `DASHBOARD_USER`, default `admin`). `/webhook/instagram` is protected by Meta's request signature instead. `/health` is public.

---

## Instagram API setup guide

### 1. Convert Instagram to Business or Creator
Instagram app → Settings and privacy → Account type and tools → Switch to professional account → choose **Business** or **Creator**.

### 2. Connect it to a Facebook Page
Create (or pick) a Facebook Page, then link it: Instagram → Edit profile → Page (or Page settings → Linked accounts → Instagram). This guide uses the **Facebook Login** flavor of the API, which requires a linked Page.

### 3. Create a Facebook Developer App
1. Go to [developers.facebook.com](https://developers.facebook.com) → **My Apps → Create App**.
2. Choose a use case that includes Instagram messaging / "Manage messaging & content on Instagram", app type **Business**.
3. Note the **App ID** and **App Secret** (App settings → Basic). Put the secret in `.env` as `FACEBOOK_APP_SECRET`.

### 4. Add the Instagram Graph API product and permissions
Add the **Instagram** product (and **Webhooks**) to the app. Request these permissions:

| Permission | Why |
|---|---|
| `instagram_manage_comments` | Reply to comments |
| `instagram_manage_messages` | Send DMs |
| `instagram_basic` | Read post details |
| `pages_show_list`, `pages_read_engagement`, `pages_manage_metadata` | Find your Page / IG account and subscribe to webhooks |

> Meta has been renaming permissions for the newer "Instagram API with Instagram Login" (`instagram_business_manage_comments`, `instagram_business_manage_messages`). If your app dashboard shows those names instead, use them and the tokens/host from that flow; the endpoints in `instagram.py` are the same shape but the host is `graph.instagram.com`. Check the current docs, since this changes.

### 5. Generate a long-lived User Access Token
1. Open [Graph API Explorer](https://developers.facebook.com/tools/explorer), select your app, choose **User Token**, add the permissions above, and click **Generate Access Token**. This is a short-lived (~1 hour) token.
2. Exchange it for a long-lived (~60 day) token:
   ```
   GET https://graph.facebook.com/v21.0/oauth/access_token
       ?grant_type=fb_exchange_token
       &client_id={app-id}
       &client_secret={app-secret}
       &fb_exchange_token={short-lived-token}
   ```
3. Find your IDs: `GET /me/accounts` returns your **Page ID** (and a Page token). Then `GET /{page-id}?fields=instagram_business_account` returns your **Instagram Business Account ID**.
4. Paste the token, Page ID and IG account ID into **Dashboard → Settings**.

**Refreshing (60-day expiry):** long-lived tokens expire. Before expiry, re-run the exchange in step 2 using the current long-lived token as `fb_exchange_token` to get a fresh 60-day one, then paste it into Settings. Put a calendar reminder at ~50 days. Alternatively, calling `/me/accounts` with a long-lived user token returns **Page access tokens that don't expire**; these work for the Instagram account linked to the Page and are the lower-maintenance option.

### 6. Configure the webhook
1. Set `WEBHOOK_VERIFY_TOKEN` in `.env` to any random string and deploy the app.
2. App dashboard → **Webhooks** → choose the **Instagram** object → **Subscribe to this object**.
   - Callback URL: `https://YOUR-DOMAIN/webhook/instagram`
   - Verify token: the value from `.env`
3. Subscribe to the **`comments`** field.
4. Subscribe your Instagram account to the app:
   ```
   POST https://graph.facebook.com/v21.0/{ig-account-id}/subscribed_apps?subscribed_fields=comments&access_token={token}
   ```
   The app verifies `X-Hub-Signature-256` on every POST using `FACEBOOK_APP_SECRET`.

### 7. Get a Post ID for a specific video/post
In Graph API Explorer:
```
GET /{ig-account-id}/media?fields=id,caption,permalink,media_type,timestamp
```
Find the entry whose `permalink` matches your Reel/post URL and copy its `id`. Paste it into the campaign form; the preview (thumbnail + caption) loads on blur so you can confirm it's right. Add `&limit=50` or page through `paging.next` for older posts.

---

## Important limitations

- **DM rules:** you can't cold-DM arbitrary users. This app uses Instagram's **Private Replies** feature: it sends the DM using the *comment ID* as the recipient, which is the sanctioned way to open a conversation from a comment. Limits: **one private reply per comment, within 7 days** of the comment. Sending to a user ID (`send_dm(..., instagram_user_id=...)`) only works inside a 24-hour window after that user messaged you.
- **App Review:** in **Development mode** everything works, but only for people with a role on the app (admins, developers, testers) and their comments. For the public, switch the app to **Live** and get **Advanced Access** for `instagram_manage_comments` and `instagram_manage_messages` via **App Review → Permissions and Features → Request**. You'll need: Business Verification, a privacy policy URL, and a screen recording showing the comment → reply → DM flow. Describe the use case plainly (e.g., "Users comment a keyword on our post and receive the requested resource by DM").
- Instagram rate-limits messaging/comment calls; `instagram.py` retries with exponential backoff on rate-limit and 5xx errors.
- Don't send spam or promotional DMs to people who didn't ask; that risks the account and the app.

## How it works

1. Meta POSTs a `comments` event → signature checked → `200` returned immediately.
2. A background task finds an active campaign for that post whose keyword appears in the comment (case-insensitive, partial).
3. The comment ID is inserted into `processed_comments` (unique) *before* acting, so retries/duplicates from Meta never double-fire.
4. Public reply + private DM are sent independently; the outcome is stored on the row. Comments from your own account are ignored to avoid loops.

Message templates support `{username}`.

## Layout

```
main.py  instagram.py  models.py  database.py
routes/{webhook,api,dashboard,auth}.py
templates/  static/  Dockerfile  railway.toml  render.yaml  .env.example
```
