# AlphaQuant AI

Institutional-style **crypto futures trading assistant**. Generates explainable
trade ideas with confidence scores and uncertainty — never guaranteed outcomes.
**Human-in-the-loop by default.** Auto-execution is not part of v1.

> Most scans should return **NO TRADE**. That is correct behavior.

## Stack

| Layer | Tech |
|-------|------|
| Frontend | Next.js 15, React 19, Tailwind, Shadcn, Lightweight Charts (Phase 7) |
| Backend | FastAPI, Python 3.11+, Celery, WebSockets |
| Data | PostgreSQL, Redis |
| ML | scikit-learn, XGBoost, LightGBM, CatBoost, PyTorch (Phase 6) |
| Ops | Docker Compose |

## Quick Start (Phase 1 + Dashboard)

```bash
# From repo root
cp config/.env.example .env
python -m venv .venv
# Windows:
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"

# Terminal 1 — API
.\.venv\Scripts\python.exe -m uvicorn alphaquant_api.main:app --app-dir api --reload --port 8000

# Terminal 2 — Frontend (http://localhost:3000)
cd frontend
npm install
npm run dev
```

Open **http://localhost:3000** — you should see the PAPER TRADING desk.

## Documentation

- [Architecture](docs/ARCHITECTURE.md)
- [Roadmap / Build Order](docs/ROADMAP.md)
- [Risk Defaults](docs/RISK_POLICY.md)
- [Deploy + Paper→Live](docs/DEPLOY_AND_LIVE.md)
- [Always-on + Neon](docs/ALWAYS_ON_NEON.md)
- [Railway API + Scanner](docs/RAILWAY_SETUP.md)
- [Real Trading (human confirm)](docs/REAL_TRADING.md)

## Status

Building in phased order (Section 16). Current focus: **Foundation → Risk Engine → Indicators → Confluence**.

Live trading modules are intentionally **not** scaffolded until the paper-trading gate passes.
