# Real (Live) Trading — Human Confirm

Autopilot **OFF**. Har real order pe tumhe **YES** type karna hoga.

## Enable (deliberate)

`.env` / Railway variables:

```
TRADING_MODE=live
LIVE_TRADING_ENABLED=true
MEXC_API_KEY=...
MEXC_API_SECRET=...
MARGIN_MODE=cross
TARGET_LEVERAGE=200
RISK_PER_TRADE_PCT=0.005
DATABASE_URL=...neon...
```

Phir API restart.

## Flow

1. Frontend pe Evaluate (paper-style idea + risk)  
2. **Preview live order** → confirm token  
3. Type **YES** → **Confirm REAL order** → MEXC market order + SL/TP1  

API:
- `GET /api/v1/live/status`
- `POST /api/v1/live/preview`
- `POST /api/v1/live/confirm` `{ "confirm_token": "...", "typed_yes": "YES" }`

## Safety still on

- Risk ≤ 0.5% init/stop budget  
- Stop before liquidation (200x)  
- Confidence / RR / TF gates → NO TRADE = no order  
- Scanner **never** auto-places live orders  

## Risks (honest)

CROSS + 200x pe liquidation **0.5% se zyada** wallet kha sakti hai.  
Koi profit guarantee nahi. Pehle chhoti equity se test karo.

## MEXC checklist

- [ ] KYC done (futures trading permission)  
- [ ] API: **Order placing** ON, **Withdraw** OFF  
- [ ] IP whitelist = Railway/VPS IP  
- [ ] Secret sirf server env mein  

## Disable instantly

```
LIVE_TRADING_ENABLED=false
```
or `TRADING_MODE=paper` → redeploy.
