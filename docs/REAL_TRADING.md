# Real (Live) Trading — Human Confirm Only

Autopilot **OFF**. Scanner **never** places live orders.  
Desk only: **Preview → type YES → Confirm**.

Cross + 200x can liquidate **more than** the 0.5% init/stop budget. No profit guarantee.  
Use **real wallet equity** in Desk Controls (e.g. ~10 USDT if that is your MEXC balance) — not 10000.

### Already have open MEXC trades?

Manual positions on **CROSS** share the same wallet as any new desk order.  
If you already hold several 200x longs on a ~$10 account, **do not add another** until you reduce risk / free margin.  
After keys are on Railway: `GET /api/v1/live/account` lists open positions read-only.

---

## 1) MEXC API keys + IP whitelist

1. MEXC → API Management → Create key  
2. Permissions: **Futures / Order placing ON**, **Withdraw OFF**  
3. Whitelist the Railway API egress IP on the MEXC key:
   - Current production egress (from `/api/v1/live/egress`): **`50.18.122.164`**
   - Re-check anytime: `GET https://hamzah-ka-ai-agent-production.up.railway.app/api/v1/live/egress`
   - If Railway changes region/IP, update the whitelist.
4. Paste **Key + Secret only into Railway Variables** (never GitHub / Netlify / chat)

Checklist:

- [ ] KYC / futures enabled  
- [ ] Trade ON, Withdraw OFF  
- [ ] Railway egress IP whitelisted  
- [ ] Secrets only on API service  

---

## 2) Railway API variables

Service: **API** (`hamzah-ka-ai-agent` with public URL) — not the scanner.

| Variable | Value |
|----------|--------|
| `TRADING_MODE` | `live` |
| `LIVE_TRADING_ENABLED` | `true` |
| `MEXC_API_KEY` | your key |
| `MEXC_API_SECRET` | your secret |
| `MARGIN_MODE` | `cross` |
| `TARGET_LEVERAGE` | `200` |
| `RISK_PER_TRADE_PCT` | `0.005` |
| `DATABASE_URL` | Neon URL (existing) |
| `CORS_ORIGINS` | `https://tradingagen.netlify.app` |

Then **Deploy Latest Commit** / restart API so settings reload.

Scanner: keep `TRADING_MODE=paper` (or leave as-is). Do **not** put MEXC secrets on Netlify.

---

## 3) Verify armed (no order yet)

```bash
curl https://hamzah-ka-ai-agent-production.up.railway.app/api/v1/live/status
```

Expect:

```json
"armed": true,
"autopilot": false,
"mexc_keys_configured": true
```

Desk Live panel should show **ARMED**.

Local check script (after API is public):

```bash
python scripts/check_live_ready.py
```

---

## 4) First real order (manual)

1. Desk → liquid symbol (BTC/ETH) → set **small** Wallet equity  
2. Evaluate setup  
3. **1. Preview live order** → read size / stop / liq warning  
4. Type **YES** → **2. Confirm REAL order**  
5. Verify position + SL/TP on MEXC; check Neon `signal_records` / audit  

API:

- `GET /api/v1/live/status`  
- `GET /api/v1/live/egress`  
- `POST /api/v1/live/preview`  
- `POST /api/v1/live/confirm` `{ "confirm_token": "...", "typed_yes": "YES" }`  

---

## 5) Kill switch (instant)

Railway API variables:

```
LIVE_TRADING_ENABLED=false
```

or `TRADING_MODE=paper` → redeploy / restart.

Orders stay blocked until both live switches are on again + human YES.

---

## Safety still on

- Risk ≤ 0.5% init/stop budget  
- Stop before liquidation (200x)  
- Confidence / RR / TF gates → NO TRADE = no order  
- Autopilot OFF forever in this design  
