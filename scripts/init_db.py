"""Initialize DB tables (works with Neon DATABASE_URL)."""

from __future__ import annotations

from alphaquant_db.session import init_db
from alphaquant_shared.config import get_settings
from alphaquant_shared.logging import configure_logging, get_logger


def main() -> None:
    settings = get_settings()
    configure_logging(settings.log_level)
    log = get_logger(__name__)
    url = settings.database_url
    # Redact password in logs
    safe = url.split("@")[-1] if "@" in url else url
    log.info("init_db_begin", host=safe)
    init_db()
    log.info("init_db_done")


if __name__ == "__main__":
    main()
