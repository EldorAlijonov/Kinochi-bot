"""add movie code counter

Revision ID: 20260421_0008
Revises: 20260421_0007
Create Date: 2026-04-21 22:45:00
"""

from alembic import op
import sqlalchemy as sa


revision = "20260421_0008"
down_revision = "20260421_0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "movie_code_counters",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("last_value", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    bind = op.get_bind()
    dialect = bind.dialect.name
    if dialect == "postgresql":
        bind.execute(
            sa.text(
                """
                INSERT INTO movie_code_counters (id, last_value)
                SELECT 1, COALESCE(MAX(code::integer), 0)
                FROM movies
                WHERE code ~ '^\\d{4}$'
                """
            )
        )
    else:
        rows = bind.execute(sa.text("SELECT code FROM movies")).fetchall()
        max_code = max(
            (int(row[0]) for row in rows if row[0] and str(row[0]).isdigit()),
            default=0,
        )
        bind.execute(
            sa.text(
                "INSERT INTO movie_code_counters (id, last_value) "
                "VALUES (1, :last_value)"
            ),
            {"last_value": max_code},
        )


def downgrade() -> None:
    op.drop_table("movie_code_counters")
