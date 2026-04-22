"""add pending movie requests

Revision ID: 20260421_0006
Revises: 20260421_0005
Create Date: 2026-04-21 21:00:00
"""

from alembic import op
import sqlalchemy as sa


revision = "20260421_0006"
down_revision = "20260421_0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "pending_movie_requests",
        sa.Column("user_telegram_id", sa.BigInteger(), nullable=False),
        sa.Column("movie_code", sa.String(length=4), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.PrimaryKeyConstraint("user_telegram_id"),
    )
    op.create_index(
        "ix_pending_movie_requests_expires_at",
        "pending_movie_requests",
        ["expires_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_pending_movie_requests_expires_at",
        table_name="pending_movie_requests",
    )
    op.drop_table("pending_movie_requests")
