"""Application settings loaded from environment variables."""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration. Secrets must never be hardcoded."""

    model_config = SettingsConfigDict(
        env_file=(".env", "config/.env.example"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_env: Literal["development", "staging", "production"] = "development"
    app_name: str = "AlphaQuant AI"
    log_level: str = "INFO"
    trading_mode: Literal["paper", "live"] = "paper"
    # Second switch — even if TRADING_MODE=live, orders stay blocked until true
    live_trading_enabled: bool = False
    # Production frontends (Netlify/Vercel), comma-separated
    cors_origins: str = ""

    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_user: str = "alphaquant"
    postgres_password: str = "alphaquant_dev_only"
    postgres_db: str = "alphaquant"
    # Neon / managed Postgres: set this and it overrides host/user/password pieces
    database_url_override: str = Field(default="", validation_alias="DATABASE_URL")

    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0
    redis_url_override: str = Field(default="", validation_alias="REDIS_URL")

    # Always-on paper scanner
    scanner_enabled: bool = True
    scanner_interval_seconds: int = Field(default=300, ge=60)  # 5 min
    scanner_account_equity: float = Field(default=10_000, gt=0)
    paper_wallet_equity: float = Field(default=10_000, gt=0)

    risk_per_trade_pct: float = Field(default=0.005, gt=0)
    risk_per_trade_hard_cap_pct: float = Field(default=0.005, gt=0)
    max_concurrent_risk_pct: float = Field(default=0.015, gt=0)
    daily_loss_limit_pct: float = Field(default=0.015, gt=0)
    min_risk_reward: float = Field(default=2.0, ge=2.0)
    min_confidence: float = Field(default=0.85, ge=0.0, le=1.0)
    news_buffer_minutes: int = Field(default=30, ge=0)
    margin_mode: Literal["cross", "isolated"] = "cross"
    max_leverage: float = Field(default=200.0, ge=1.0)
    target_leverage: float = Field(default=200.0, ge=1.0)
    use_fixed_leverage: bool = True
    leverage_safety_buffer: float = Field(default=3.0, ge=1.0)
    stop_liq_buffer_fraction: float = Field(default=0.6, gt=0, le=1.0)
    maintenance_margin_rate: float = Field(default=0.004, ge=0)

    primary_exchange: str = "mexc"

    binance_api_key: str = ""
    binance_api_secret: str = ""
    binance_testnet: bool = True
    binance_futures_rest: str = "https://fapi.binance.com"
    binance_futures_ws: str = "wss://fstream.binance.com"

    mexc_api_key: str = ""
    mexc_api_secret: str = ""
    mexc_futures_rest: str = "https://api.mexc.com"
    mexc_futures_ws: str = "wss://contract.mexc.com/edge"

    telegram_bot_token: str = ""
    telegram_chat_id: str = ""
    discord_webhook_url: str = ""

    @field_validator("trading_mode")
    @classmethod
    def _paper_default_safety(cls, value: str) -> str:
        # Live mode is not enabled until paper gate; keep default paper.
        return value

    @property
    def database_url(self) -> str:
        if self.database_url_override.strip():
            url = self.database_url_override.strip()
            # SQLAlchemy sync driver
            if url.startswith("postgres://"):
                url = url.replace("postgres://", "postgresql+psycopg2://", 1)
            elif url.startswith("postgresql://") and "+psycopg2" not in url and "+asyncpg" not in url:
                url = url.replace("postgresql://", "postgresql+psycopg2://", 1)
            return url
        return (
            f"postgresql+psycopg2://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def async_database_url(self) -> str:
        if self.database_url_override.strip():
            url = self.database_url_override.strip()
            if url.startswith("postgres://"):
                url = url.replace("postgres://", "postgresql+asyncpg://", 1)
            elif url.startswith("postgresql+psycopg2://"):
                url = url.replace("postgresql+psycopg2://", "postgresql+asyncpg://", 1)
            elif url.startswith("postgresql://") and "+asyncpg" not in url:
                url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
            return url
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def redis_url(self) -> str:
        if self.redis_url_override.strip():
            return self.redis_url_override.strip()
        return f"redis://{self.redis_host}:{self.redis_port}/{self.redis_db}"

    def effective_risk_per_trade_pct(self, requested: float | None = None) -> float:
        """Clamp requested risk to the hard cap."""
        base = self.risk_per_trade_pct if requested is None else requested
        if base <= 0:
            raise ValueError("risk_per_trade_pct must be positive")
        return min(base, self.risk_per_trade_hard_cap_pct)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
