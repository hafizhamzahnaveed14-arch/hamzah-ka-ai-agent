"""Immutable journaling helpers."""

from __future__ import annotations

import json

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
