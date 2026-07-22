"""Immutable journaling helpers."""

from __future__ import annotations

import json
from typing import Any

from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from alphaquant_db.models import AuditEvent, SignalRecord
from alphaquant_shared.types import TradeIdea


def persist_signal(session: Session, idea: TradeIdea) -> SignalRecord:
    record = SignalRecord(
        symbol=idea.symbol,
        action=idea.action.value,
        trading_mode=idea.trading_mode.value,
        confidence=idea.confidence,
        entry=idea.entry,
        stop_loss=idea.risk.stop_loss if idea.risk else None,
        take_profit_1=idea.risk.take_profit_1 if idea.risk else None,
        risk_reward=idea.risk.risk_reward if idea.risk else None,
        position_size=idea.risk.position_size if idea.risk else None,
        reasons_json=json.dumps(idea.reasons),
        conflicts_json=json.dumps(idea.conflicts),
        no_trade_reason=idea.no_trade_reason,
        raw_json=idea.model_dump_json(),
    )
    session.add(record)
    session.add(
        AuditEvent(
            event_type="signal_generated",
            trading_mode=idea.trading_mode.value,
            payload_json=idea.model_dump_json(),
        )
    )
    session.flush()
    return record


def list_recent_signals(
    session: Session,
    *,
    limit: int = 40,
    symbol: str | None = None,
) -> list[dict[str, Any]]:
    """Return newest journal rows for the desk UI."""
    limit = max(1, min(limit, 200))
    stmt = select(SignalRecord)
    if symbol:
        stmt = stmt.where(SignalRecord.symbol == symbol.upper())
    stmt = stmt.order_by(desc(SignalRecord.created_at)).limit(limit)
    rows = session.scalars(stmt).all()
    out: list[dict[str, Any]] = []
    for row in rows:
        try:
            reasons = json.loads(row.reasons_json or "[]")
        except json.JSONDecodeError:
            reasons = []
        try:
            conflicts = json.loads(row.conflicts_json or "[]")
        except json.JSONDecodeError:
            conflicts = []
        out.append(
            {
                "id": row.id,
                "created_at": row.created_at.isoformat() if row.created_at else None,
                "symbol": row.symbol,
                "action": row.action,
                "trading_mode": row.trading_mode,
                "confidence": row.confidence,
                "entry": row.entry,
                "stop_loss": row.stop_loss,
                "take_profit_1": row.take_profit_1,
                "risk_reward": row.risk_reward,
                "reasons": reasons,
                "conflicts": conflicts,
                "no_trade_reason": row.no_trade_reason,
            }
        )
    return out
