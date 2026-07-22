"""Initial schema placeholder — use `alembic revision --autogenerate` against a live DB.

For local/dev, `alphaquant_db.session.init_db()` creates tables directly.
"""

from alembic import op
import sqlalchemy as sa

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Tables are managed via SQLAlchemy metadata in early phases.
    # Autogenerate against Postgres once Docker DB is up.
    pass


def downgrade() -> None:
    pass
