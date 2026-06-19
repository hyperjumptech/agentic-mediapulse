"""newsletter_translations: stored localized variants

Revision ID: 0002_newsletter_translations
Revises: 0001_initial
Create Date: 2026-06-19

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0002_newsletter_translations"
down_revision: str | None = "0001_initial"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "newsletter_translations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("newsletter_id", sa.Integer(), nullable=False),
        sa.Column("subject", sa.String(), nullable=False),
        sa.Column("language", sa.String(), nullable=False),
        sa.Column("content", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("metadata", postgresql.JSONB(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("newsletter_id", "language", name="uq_newsletter_translations_nl_lang"),
    )
    op.create_index("ix_newsletter_translations_newsletter_id", "newsletter_translations", ["newsletter_id"])
    op.create_index("ix_newsletter_translations_subject", "newsletter_translations", ["subject"])
    op.create_index("ix_newsletter_translations_language", "newsletter_translations", ["language"])
    op.create_index("ix_newsletter_translations_status", "newsletter_translations", ["status"])


def downgrade() -> None:
    op.drop_index("ix_newsletter_translations_status", table_name="newsletter_translations")
    op.drop_index("ix_newsletter_translations_language", table_name="newsletter_translations")
    op.drop_index("ix_newsletter_translations_subject", table_name="newsletter_translations")
    op.drop_index("ix_newsletter_translations_newsletter_id", table_name="newsletter_translations")
    op.drop_table("newsletter_translations")
