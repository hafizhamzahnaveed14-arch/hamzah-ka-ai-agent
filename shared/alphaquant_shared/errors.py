"""Domain and infrastructure exceptions."""

from __future__ import annotations


class AlphaQuantError(Exception):
    """Base error for AlphaQuant."""


class ConfigurationError(AlphaQuantError):
    pass


class ExchangeError(AlphaQuantError):
    """Exchange API or websocket failure."""


class RateLimitError(ExchangeError):
    """Venue rate limit exceeded; caller should back off."""


class ExchangeUnavailableError(ExchangeError):
    """Venue down or unreachable — degrade gracefully."""


class DataValidationError(AlphaQuantError):
    pass


class RiskViolationError(AlphaQuantError):
    """Hard risk rule would be violated."""


class NoTradeError(AlphaQuantError):
    """Raised optionally when callers want exception-style NO TRADE handling."""

    def __init__(self, reason: str) -> None:
        self.reason = reason
        super().__init__(reason)
