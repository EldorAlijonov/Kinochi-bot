"""shrink movie code to four digits

Revision ID: 20260421_0003
Revises: 20260420_0002
Create Date: 2026-04-21 10:00:00
"""

from alembic import op
import sqlalchemy as sa


revision = "20260421_0003"
down_revision = "20260420_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column(
        "movies",
        "code",
        existing_type=sa.String(length=32),
        type_=sa.String(length=4),
        existing_nullable=False,
    )


def downgrade() -> None:
    op.alter_column(
        "movies",
        "code",
        existing_type=sa.String(length=4),
        type_=sa.String(length=32),
        existing_nullable=False,
    )
