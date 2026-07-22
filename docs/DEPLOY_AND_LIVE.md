# Deploy + Paper → Live Checklist

Yeh agent **laptop pe soye hue** 24/7 nahi chal sakta. Agar internet off / PC sleep ho,
bot bhi ruk jata hai. Always-on ke liye **cloud/VPS** chahiye.

## 1) Always-on (soye / internet off pe bhi)

| Cheez | Kyun |
|-------|------|
| VPS / cloud VM (Hetzner, DigitalOcean, AWS Lightsail, Railway, Render, Fly.io) | Apna internet band ho to bhi server online |
| Docker Compose (API + Postgres + Redis + Frontend) | Stable restart |
| Process manager / health checks | Crash pe auto-restart |
| MEXC API keys on server secrets | Kabhi frontend mein mat daalo |
| Domain + HTTPS | Mobile se safe access |
| Telegram/Discord alerts | Phone pe signal / errors |

**Minimum architecture (deploy):**

```
Internet users → Frontend (Next.js)
                      ↓
                 FastAPI (paper/live engine)
                      ↓
              Postgres + Redis + MEXC API
```

Laptop = sirf development. Production = cloud.

## 2) Paper → Real (live) jaane se pehle (mandatory)

Live module abhi **band** hai by design. Enable karne se pehle:

1. **Paper trading gate**
   - ~60–90 days **ya** 100+ paper trades
   - Positive expectancy after fees/slippage
   - Paper results ≈ backtest (badi mismatch = rukao)

2. **Risk locked**
   - ≤ 0.5% wallet risk
   - 200x isolated margin
   - Stop before liquidation
   - Daily loss halt

3. **Exchange safety**
   - MEXC API: **trade only**, withdrawals OFF
   - IP whitelist on VPS IP
   - Keys only in server env / secrets manager

4. **Human confirm first**
   - Pehli live version: signal aaye → aap confirm → order
   - Autopilot baad mein, alag opt-in (default OFF)

5. **Audit / journal**
   - Har signal + fill immutable log
   - Notifications on open/close

6. **Kill switch**
   - UI + API flag: halt all new entries instantly
   - Daily loss auto-halt already in risk engine

## 3) Abhi kya ready hai vs kya baqi

| Ready | Not yet (needed for real) |
|-------|---------------------------|
| MEXC market data + gold fix (`XAUUSDT`) | Live order placement on MEXC |
| Risk 200x / 0.5% | Signed trade endpoints + confirm flow |
| Paper evaluate + journal (session) | Persistent paper ledger + 24/7 worker |
| Frontend desk controls | Cloud deploy scripts / CI |
| Scanner symbols (BTC, DOGE, …) | Autopilot (opt-in later) |

## 4) Honest note on “profit wale coins”

Koi list **guaranteed profit** nahi deti. DOGE/SUI/WIF etc. liquidity ke liye add kiye gaye hain —
har setup pe **NO TRADE** zyada hona healthy hai, hamesha signal nahi.
