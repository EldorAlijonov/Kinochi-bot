"""add movie title

Revision ID: 20260421_0004
Revises: 20260421_0003
Create Date: 2026-04-21 11:00:00
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "20260421_0004"
down_revision = "20260421_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    columns = {column["name"] for column in inspect(bind).get_columns("movies")}
    if "title" in columns:
        _fill_missing_titles()
        op.alter_column(
            "movies",
            "title",
            existing_type=sa.String(length=255),
            nullable=False,
            server_default=None,
        )
        return

    op.add_column(
        "movies",
        sa.Column(
            "title",
            sa.String(length=255),
            nullable=True,
        ),
    )
    _fill_missing_titles()
    op.alter_column("movies", "title", nullable=False)


def downgrade() -> None:
    bind = op.get_bind()
    columns = {column["name"] for column in inspect(bind).get_columns("movies")}
    if "title" not in columns:
        return

    op.drop_column("movies", "title")


def _fill_missing_titles() -> None:
    op.execute(
        sa.text(
            """
            UPDATE movies
            SET title = LEFT(
                COALESCE(
                    NULLIF(BTRIM(BTRIM(BTRIM(split_part(COALESCE(caption, ''), E'\\n', 1)), '/')), ''),
                    'Nomsiz kino'
                ),
                255
            )
            WHERE title IS NULL
            """
        )
    )
