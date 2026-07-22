# Always-on + Neon — kya chahiye / kaise chalaye

Laptop band / internet off → bot ruk jata hai. **Cloud pe 24/7** chalana zaroori hai.

## Short answer (checklist)

| Cheez | Service (example) | Status |
|-------|-------------------|--------|
| Database | **Neon** Postgres | Tum choose kar rahe ho ✅ |
| Redis | **Upstash** Redis (free tier OK) | Recommended |
| API + Scanner (hamesha chalta) | **Railway / Render / Fly.io / VPS** | Required |
| Frontend | **Vercel** (Next.js) | Recommended |
| Secrets | Host env vars (`.env` commit mat karo) | Required |
| Alerts | **Telegram bot** | Strongly recommended |
| Exchange | MEXC API trade-only + VPS IP whitelist | Required later for live |

```
You (sleeping)
    ↑ Telegram alert
Scanner worker (cloud) ──→ Neon DB
        ↓
   MEXC market data
Frontend (Vercel) ──→ API (Railway) ──→ Neon
```

**Abhi auto = paper scan + journal + notify.** Live orders abhi OFF.

---

## 1) Neon setup (5 min)

1. [neon.tech](https://neon.tech) → New project
2. Dashboard → **Connection string** (URI)
3. Example shape:
   ```
   postgresql://USER:PASSWORD@ep-xxxx.region.aws.neon.tech/neondb?sslmode=require
   ```
4. Apne server `.env` mein:
   ```
   DATABASE_URL=postgresql://USER:PASSWORD@ep-xxxx.../neondb?sslmode=require
   TRADING_MODE=paper
   ```
5. Tables banao (ek baar):
   ```bash
   python scripts/init_db.py
   ```

Neon **serverless Postgres** hai — perfect. Connection pooling (Neon pooler) production mein better.

---

## 2) Baqi cheezein

### A) Host for API + scanner (must)
Ek jagah jahan process **restart=always** ho:

- **Railway** / **Render** / **Fly.io**: easy
- ya **cheap VPS** (Hetzner/DigitalOcean) + Docker

Do processes:
1. `uvicorn` → API (`:8000`)
2. `python scripts/paper_scanner.py` → har N minutes symbols scan, Neon pe save

### B) Redis (Upstash)
Celery / cache / rate-limit ke liye. Abhi scanner ke liye optional, baad mein zaroori.

```
REDIS_URL=rediss://default:PASSWORD@....upstash.io:6379
```

### C) Frontend (Vercel)
```
NEXT_PUBLIC_API_URL=https://YOUR-API-HOST
```
Deploy `frontend/` folder.

### D) Telegram (soye hue alerts)
1. @BotFather → token
2. Apni chat id
3. `.env`:
   ```
   TELEGRAM_BOT_TOKEN=...
   TELEGRAM_CHAT_ID=...
   ```
LONG/SHORT idea aaye to phone pe message (NO TRADE spam nahi).

### E) MEXC keys
- Trade only, withdraw OFF
- Linked IP = **cloud server ka public IP** (laptop IP nahi, warna ghar pe band)

---

## 3) Local test (pehle yeh)

```bash
# .env mein Neon DATABASE_URL daalo
python scripts/init_db.py
python scripts/paper_scanner.py
```

Ctrl+C se rukega. Cloud pe isi command ko service banao.

Docker (API + scanner, DB=Neon):

```bash
# root .env must contain DATABASE_URL=...neon...
docker compose -f docker/docker-compose.cloud.yml up -d --build
```

---

## 4) “Automatically” ka matlab abhi

| Hota hai | Nahi hota (abhi) |
|----------|------------------|
| Har ~5 min scan | Live MEXC order |
| Neon pe signal log | Autopilot money |
| Telegram pe actionable idea | Laptop-only 24/7 |
| Paper mode journal | Guaranteed profit |

Live auto-trade = alag phase (paper gate ke baad).

---

## 5) Approximate monthly cost (ballpark)

| Item | Free / low |
|------|------------|
| Neon | Free tier often enough start |
| Upstash Redis | Free tier |
| Railway/Render | Free/hobby or ~$5 |
| Vercel | Free hobby |
| VPS alternative | ~$4–6 |

---

## 6) Next step order

1. Neon project + `DATABASE_URL`  
2. `python scripts/init_db.py`  
3. Telegram bot  
4. Railway/Render pe API + `paper_scanner`  
5. Vercel pe frontend  
6. 1–2 hafta paper logs dekho — phir live sochna  

Agar chaho to agla message mein **Railway pe exact click-by-click** ya **VPS Docker** steps likh dunga.
