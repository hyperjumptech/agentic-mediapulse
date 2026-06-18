"""initial schema: newsletters, subject_memory, agent_activity

Revision ID: 0001_initial
Revises:
Create Date: 2026-06-18

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0001_initial"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "newsletters",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("subject", sa.String(), nullable=False),
        sa.Column("content", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("metadata", postgresql.JSONB(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_newsletters_subject", "newsletters", ["subject"])
    op.create_index("ix_newsletters_status", "newsletters", ["status"])

    op.create_table(
        "subject_memory",
        sa.Column("subject", sa.String(), primary_key=True),
        sa.Column("brief", sa.String(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        "agent_activity",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("newsletter_id", sa.Integer(), nullable=False),
        sa.Column("kind", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("model", sa.String(), nullable=True),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("input_tokens", sa.Integer(), nullable=True),
        sa.Column("output_tokens", sa.Integer(), nullable=True),
        sa.Column("total_tokens", sa.Integer(), nullable=True),
        sa.Column("error", sa.String(), nullable=True),
        sa.Column("metadata", postgresql.JSONB(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_agent_activity_newsletter_id", "agent_activity", ["newsletter_id"])
    op.create_index("ix_agent_activity_name", "agent_activity", ["name"])
    op.create_index("ix_agent_activity_model", "agent_activity", ["model"])


def downgrade() -> None:
    op.drop_index("ix_agent_activity_model", table_name="agent_activity")
    op.drop_index("ix_agent_activity_name", table_name="agent_activity")
    op.drop_index("ix_agent_activity_newsletter_id", table_name="agent_activity")
    op.drop_table("agent_activity")

    op.drop_table("subject_memory")

    op.drop_index("ix_newsletters_status", table_name="newsletters")
    op.drop_index("ix_newsletters_subject", table_name="newsletters")
    op.drop_table("newsletters")
