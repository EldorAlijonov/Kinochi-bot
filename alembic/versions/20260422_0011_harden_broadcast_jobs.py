"""harden broadcast jobs

Revision ID: 20260422_0011
Revises: 20260422_0010
Create Date: 2026-04-22 00:30:00
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "20260422_0011"
down_revision = "20260422_0010"
branch_labels = None
depends_on = None


def _has_column(table_name: str, column_name: str) -> bool:
    bind = op.get_bind()
    columns = {column["name"] for column in inspect(bind).get_columns(table_name)}
    return column_name in columns


def upgrade() -> None:
    if not _has_column("broadcast_campaigns", "file_id"):
        op.add_column(
            "broadcast_campaigns",
            sa.Column("file_id", sa.String(length=512), nullable=True),
        )

    if not _has_column("broadcast_jobs", "retry_count"):
        op.add_column(
            "broadcast_jobs",
            sa.Column("retry_count", sa.Integer(), server_default="0", nullable=False),
        )
        op.alter_column("broadcast_jobs", "retry_count", server_default=None)

    op.execute(
        "UPDATE broadcast_campaigns SET status = 'queued' "
        "WHERE status = 'sending' AND id IN ("
        "SELECT campaign_id FROM broadcast_jobs WHERE status = 'queued'"
        ")"
    )


def downgrade() -> None:
    if _has_column("broadcast_jobs", "retry_count"):
        op.drop_column("broadcast_jobs", "retry_count")

    if _has_column("broadcast_campaigns", "file_id"):
        op.drop_column("broadcast_campaigns", "file_id")
