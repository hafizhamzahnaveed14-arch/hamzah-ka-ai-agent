# Railway — API + Paper Scanner (click-by-click)

**Netlify** = frontend (Next.js) ke liye theek.  
**API + always-on scanner** = **Railway** (ya Render/Fly). Netlify long-running Python worker ke liye designed nahi.

```
Netlify / Vercel  →  Frontend (UI)
Railway           →  API + Scanner (24/7)
Neon              →  Postgres
```

---

## 0) Pehle ready rakho

1. GitHub pe yeh repo push (`.env` commit **mat** karo)
2. Neon `DATABASE_URL` copy (sslmode=require)
3. MEXC keys (optional for market data public endpoints; trading keys baad mein)
4. Telegram token + chat id (optional but useful)

Local pe ek baar:
```bash
# .env mein DATABASE_URL=...
python scripts/init_db.py
```

---

## 1) Railway account

1. [https://railway.app](https://railway.app) → Login with GitHub  
2. **New Project** → **Deploy from GitHub repo** → apna `Trading Agent` repo select  
3. Agar monorepo root detect ho jaye — theek hai

---

## 2) Service A — API

1. Project mein **+ New** → **GitHub Repo** (same repo) ya pehli service ko rename: `alphaquant-api`
2. Settings → **Root Directory**: `/` (repo root)
3. Settings → **Build**:
   - Builder: **Dockerfile**
   - Dockerfile path: `docker/Dockerfile.api`
4. Settings → **Deploy** → **Custom Start Command**:
   ```bash
   uvicorn alphaquant_api.main:app --host 0.0.0.0 --port $PORT --app-dir api
   ```
   Railway `$PORT` deta hai — `8000` hardcode mat karo.
5. **Networking** → **Generate Domain** → public URL milegi, jaise:
   `https://alphaquant-api-production.up.railway.app`
6. Browser test:
   `https://YOUR-API.up.railway.app/health`  
   → `{"status":"ok",...}`

### Env vars (API service → Variables)

| Name | Value |
|------|--------|
| `DATABASE_URL` | Neon connection string |
| `TRADING_MODE` | `paper` |
| `APP_ENV` | `production` |
| `PRIMARY_EXCHANGE` | `mexc` |
| `MARGIN_MODE` | `cross` |
| `TARGET_LEVERAGE` | `200` |
| `RISK_PER_TRADE_PCT` | `0.005` |
| `MEXC_API_KEY` | (optional now) |
| `MEXC_API_SECRET` | (optional now) |
| `TELEGRAM_BOT_TOKEN` | (recommended) |
| `TELEGRAM_CHAT_ID` | (recommended) |
| `LOG_LEVEL` | `INFO` |

**Redeploy** after adding vars.

---

## 3) Service B — Scanner (always-on)

1. Same Railway project → **+ New** → **GitHub Repo** (same repo again)
2. Name: `alphaquant-scanner`
3. Dockerfile: `docker/Dockerfile.api` (same image)
4. **Start Command**:
   ```bash
   python scripts/paper_scanner.py
   ```
5. **Same env vars** copy from API (Variables → Shared variable / duplicate):
   - especially `DATABASE_URL`, Telegram, risk settings
6. Scanner ko **public domain ki zaroorat nahi** (sirf background worker)
7. Logs mein dikhna chahiye: `scanner_starting`, `scan_cycle_begin`, `scan_result`

Interval default **300s (5 min)** — change:
```
SCANNER_INTERVAL_SECONDS=300
SCANNER_ACCOUNT_EQUITY=10000
```

---

## 4) Neon tables (ek baar)

Option A — local se Neon pe:
```bash
DATABASE_URL="postgresql://...neon.../neondb?sslmode=require" python scripts/init_db.py
```

Option B — Railway API service pe one-off:
- Service → **Settings** → temporary start command:
  ```bash
  python scripts/init_db.py
  ```
- Deploy once → phir start command wapas uvicorn pe lao

---

## 5) Frontend (Netlify OK)

Netlify pe **sirf** `frontend/`:

1. Netlify → Add site → Import from Git  
2. Base directory: `frontend`  
3. Build: `npm run build`  
4. Publish: `.next` **nahi** — Next.js ke liye Netlify Next runtime use karo, ya asaan path: **Vercel** (Next ke liye behtar)

Env on Netlify/Vercel:
```
NEXT_PUBLIC_API_URL=https://YOUR-API.up.railway.app
```

CORS already allow karta hai `localhost:3000`; production frontend domain add karna hoga API mein.

### CORS fix (production domain)

`api/alphaquant_api/main.py` mein apna Netlify/Vercel URL add karo, e.g.:
`https://your-site.netlify.app`

---

## 6) Netlify vs Railway — short

| Kaam | Netlify | Railway |
|------|---------|---------|
| Next.js UI | ✅ theek | ✅ bhi chal jata |
| FastAPI | ❌ unsuitable | ✅ |
| 24/7 scanner loop | ❌ | ✅ |
| Neon connect | UI via API | ✅ API/scanner |

**Conclusion:** UI = Netlify/Vercel · Brain = Railway · DB = Neon.

---

## 7) Verify checklist

- [ ] `GET /health` → ok  
- [ ] `GET /api/v1/symbols` → list  
- [ ] Scanner logs → cycles every 5 min  
- [ ] Neon → table `signal_records` rows badh rahe  
- [ ] Telegram pe LONG/SHORT (jab aaye)  
- [ ] Frontend `NEXT_PUBLIC_API_URL` Railway API pe point  

---

## 8) Common errors

| Error | Fix |
|-------|-----|
| App crash on boot | `DATABASE_URL` missing / wrong SSL |
| Port bind error | Start command mein `$PORT` use karo |
| Scanner exits | Logs dekho; MEXC network / Neon SSL |
| Frontend CORS | API allow_origins mein Netlify domain |
| Build fails | Dockerfile path `docker/Dockerfile.api` |

---

## 9) Cost note

Railway hobby/trial limits check karo. 2 services (API + scanner) + Neon free tier se start ho jata hai; sleep policies dekh lena — scanner ko **sleep** na hone dena (paid/always-on plan).
