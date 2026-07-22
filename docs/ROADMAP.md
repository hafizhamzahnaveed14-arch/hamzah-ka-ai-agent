# AlphaQuant AI — Implementation Roadmap

Follow this sequence. Do not scaffold live execution until Phase 8 gate passes.

## Phase 1 — Foundation ✅

- [x] Monorepo skeleton matching Section 18
- [x] Shared types, logging, errors, settings
- [x] PostgreSQL schema (SQLAlchemy) + Alembic bootstrap
- [x] `ExchangeAdapter` interface
- [x] Binance Futures adapter (REST + WS reconnect)
- [x] Redis caching helpers (in-memory; Redis URL configured)
- [x] Docker Compose (Postgres, Redis, API)
- [x] Unit tests for foundation modules

## Phase 2 — Indicators & Structure/SMC ✅ (core)

- [x] TA: EMA, SMA, VWAP, RSI, MACD, ATR, Bollinger, StochRSI, ADX
- [x] Structure: swings, HH/HL/LH/LL, BOS, CHoCH, bias
- [x] SMC: order blocks, FVG, liquidity pools, EQH/EQL, premium/discount
- [x] Candlestick patterns + volume spikes / approx delta
- [ ] Manual chart validation checklist for ETH/SOL (operator task)

## Phase 3 — Risk Engine ✅

- [x] Position sizing, SL/TP1–3, RR, conservative leverage, liquidation
- [x] Concurrent risk + daily loss halt + hard caps
- [x] Independent unit tests (must pass before money paths)

## Phase 4 — Confluence / Decision Logic ✅

- [x] Multi-TF alignment (≥3), confidence scoring, conflict penalties
- [x] News blackout hook + Section 13 formatter
- [x] Hard gates: RR < 2, conf < 85%, news, TF conflict → NO TRADE
- [x] FastAPI `/api/v1/signals/evaluate`

## Phase 5 — Backtesting (next up)

- [x] Metrics helpers scaffold
- [ ] Historical replay with fees/slippage
- [ ] Reports by symbol and regime (trend vs range)

## Phase 6 — ML Layer

- Walk-forward + OOS; probability-of-direction only; uplift vs rules

## Phase 7 — Dashboard UI

- Next.js 15 dark dashboard, charts, scanner, journal, PAPER vs LIVE banner

## Phase 8 — Paper Trading Gate

- Min period / 100+ trades, positive expectancy, paper ≈ backtest

## Phase 9 — Live Execution (only after gate)

- Human-confirm first; autopilot opt-in later

---

## Phase-1 Symbols

`ETHUSDT`, `ADAUSDT`, `SOLUSDT`, `AAVEUSDT`, `PEPEUSDT`, `RUNEUSDT`, `XAUUSD`

## Hard Decision Gates (always)

```
if RR < 2.0 or confidence < 0.85 or news_blackout or tf_conflict:
    return NO_TRADE
```
