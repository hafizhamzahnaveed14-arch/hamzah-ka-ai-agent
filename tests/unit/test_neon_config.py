"""DATABASE_URL / Neon URL parsing."""

from alphaquant_shared.config import Settings, get_settings


def test_neon_database_url_override():
    s = Settings(
        DATABASE_URL="postgresql://u:p@ep-x.neon.tech/neondb?sslmode=require",
    )
    assert "postgresql+psycopg2://" in s.database_url
    assert "neon.tech" in s.database_url
    assert "sslmode=require" in s.database_url


def test_async_url_from_neon():
    s = Settings(
        DATABASE_URL="postgresql://u:p@ep-x.neon.tech/neondb?sslmode=require",
    )
    assert s.async_database_url.startswith("postgresql+asyncpg://")


def test_redis_url_override():
    s = Settings(REDIS_URL="rediss://default:x@upstash.io:6379")
    assert s.redis_url.startswith("rediss://")


def test_get_settings_cache_clearable():
    get_settings.cache_clear()
    s = get_settings()
    assert s.app_name
