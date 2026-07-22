# AlphaQuant AI — Architecture

Institutional-style crypto futures trading assistant. Proposes trade ideas with
confidence scores and explicit uncertainty. Does **not** auto-execute in v1.
**NO TRADE** is a first-class, frequent outcome.

## Principles

| Rule | Implication |
|------|-------------|
| No guaranteed profits | All copy, logs, UI use probability language |
| Human-in-the-loop | AI proposes; human confirms (live later, gated) |
| Risk before prediction | Risk Engine ships and is tested first |
| Explainability | Every signal lists fired confluences + conflicts |
| Phased build | Follow `docs/ROADMAP.md` — no live trading until paper gate |

## High-Level Diagram

```
┌─────────────┐   WS/REST   ┌──────────────┐
│  Exchanges  │────────────▶│  data-layer  │──▶ Redis cache / PostgreSQL
│ Binance…    │             │  adapters    │
└─────────────┘             └──────┬───────┘
                                   │ OHLCV / funding / OI
                                   ▼
┌──────────────┐            ┌──────────────┐            ┌──────────────┐
│  indicators  │◀───────────│   services   │───────────▶│ news/sent.   │
│ structure/SMC│            │  orchestration│            └──────────────┘
└──────┬───────┘            └──────┬───────┘
       │ features                  │
       ▼                           ▼
┌──────────────┐            ┌──────────────┐            ┌──────────────┐
│  strategies  │───────────▶│ risk-engine  │───────────▶│ Trade Idea   │
│  confluence  │            │ size/SL/TP   │            │ or NO TRADE  │
└──────┬───────┘            └──────────────┘            └──────┬───────┘
       │ (later)                                                │
       ▼                                                        ▼
┌──────────────┐            ┌──────────────┐            ┌──────────────┐
│  ai-models   │            │ backtesting  │            │ FastAPI + WS │
│  P(direction)│            │ paper gate   │            │ Next.js UI   │
└──────────────┘            └──────────────┘            └──────────────┘
```

## Package Layout

| Path | Responsibility |
|------|----------------|
| `shared/` | Types, enums, config, logging, errors |
| `data-layer/` | `ExchangeAdapter` + Binance/Bybit/… adapters, ingestion, cache |
| `indicators/` | TA, structure, SMC, candlestick patterns, volume |
| `strategies/` | Confluence rules, strategy selector, trade-idea formatter |
| `risk-engine/` | Position sizing, SL/TP, liquidation, daily loss gates |
| `ai-models/` | Feature pipelines, training, inference, model registry (Phase 6) |
| `services/` | News filter, sentiment, journaling, notifications |
| `database/` | SQLAlchemy models, Alembic migrations |
| `api/` | FastAPI routes, WebSocket push |
| `backtesting/` | Historical runner + metrics |
| `frontend/` | Next.js 15 dashboard (Phase 7) |
| `tests/` | Unit + integration per module |

## Exchange Abstraction

All venue access goes through `ExchangeAdapter`:

- `get_klines`, `get_ticker`, `get_funding_rate`, `get_open_interest`
- `subscribe_klines` (async websocket with reconnect + backoff)
- Rate-limit budget tracking per venue

Strategy / indicator code must never import a concrete exchange client.

## Decision Pipeline (rule-based v1)

1. Ingest multi-TF OHLCV for symbol
2. Detect structure + SMC + indicators + volume + patterns
3. Score timeframe alignment (≥3 TF required)
4. Apply news blackout filter
5. Compute confidence from confluence weights − conflict penalties
6. Hard gates: confidence ≥ 85%, RR ≥ 2.0, no news blackout, TF alignment
7. Risk Engine sizes position / SL / TP / leverage / liquidation
8. Emit `TradeIdea` or `NO_TRADE` with reasons

ML (later) only supplies `P(direction | horizon)`. It never bypasses Risk Engine or hard gates.

## Modes

| Mode | Status in build |
|------|-----------------|
| Analysis / signal generation | Phase 4+ |
| Backtest | Phase 5 |
| Paper trading | Phase 8 |
| Live (human confirm) | Phase 9 — only after paper gate |
| Autopilot | Explicit opt-in after Phase 9 |

UI must always show **PAPER TRADING** vs **LIVE** prominently.

## Security

- API keys via env / secrets manager only
- Exchange keys: trade-only, no withdraw; IP whitelist where available
- Immutable audit log for every signal and position event
- Rate-limit + graceful degradation on venue outages
