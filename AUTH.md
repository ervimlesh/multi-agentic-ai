# Authentication — Passwordless Email OTP

Claude-style passwordless auth: enter email → receive a 6-digit code → enter it → signed in. No passwords anywhere.

## Flow

```
Register:  POST /api/v1/auth/register  { email, full_name }  ─┐
Login:     POST /api/v1/auth/login     { email }             ─┤→ emails a 6-digit code
                                                              │
Verify:    POST /api/v1/auth/verify    { email, code }  ──────┘→ { user, tokens }
Resend:    POST /api/v1/auth/resend    { email }
Refresh:   POST /api/v1/auth/refresh   { refresh_token }  → rotates tokens
Logout:    POST /api/v1/auth/logout    { refresh_token }  → revokes token
Me:        GET  /api/v1/auth/me        Authorization: Bearer <access_token>
```

- Access token: JWT, 30 min. Refresh token: 7 days, stored hashed, **rotated** on refresh and revoked on logout.
- OTP: 6 digits, 10 min expiry, max 5 attempts, 60s resend cooldown. Stored as a keyed SHA-256 hash — never in plaintext.

## Run the API (Python 3.10+)

```bash
cd apps/api
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
cp .env.example .env          # set SMTP_* to actually deliver codes
.venv/bin/python -m pytest    # 15 integration tests
.venv/bin/uvicorn app.server:app --reload   # http://localhost:8000/docs
```

Without SMTP configured, the OTP is written to the server log instead of emailed (handy for local dev).

## Run the web app (requires Node 18+)

> ⚠️ This machine currently has Node 12, which Vite does not support. Upgrade to Node 18+ (e.g. via `nvm install 20`) before running the steps below.

```bash
cd apps/web
npm install
npm run dev        # http://localhost:5173  (proxies /api to localhost:8000)
```

`npm run typecheck` / `npm run build` validate and bundle the app.

## Postman

Import from `apps/api/postman/`:
- `multi-agentic-ai-auth.postman_collection.json`
- `multi-agentic-ai.postman_environment.json`

Run **Register** (or **Login**), copy the code from your email into the `otp_code` variable, then run **Verify** — tokens are captured automatically for the protected requests.
