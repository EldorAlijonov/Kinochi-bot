"""ensure movie code uniqueness

Revision ID: 20260422_0010
Revises: 20260421_0009
Create Date: 2026-04-22 00:00:00
"""

from alembic import op
from sqlalchemy import inspect


revision = "20260422_0010"
down_revision = "20260421_0009"
branch_labels = None
depends_on = None


def _has_unique_code(bind) -> bool:
    inspector = inspect(bind)
    for constraint in inspector.get_unique_constraints("movies"):
        if constraint.get("column_names") == ["code"]:
            return True

    for index in inspector.get_indexes("movies"):
        if index.get("unique") and index.get("column_names") == ["code"]:
            return True

    return False


def upgrade() -> None:
    bind = op.get_bind()
    if _has_unique_code(bind):
        return

    op.create_unique_constraint("uq_movies_code", "movies", ["code"])


def downgrade() -> None:
    bind = op.get_bind()
    constraints = inspect(bind).get_unique_constraints("movies")
    if any(constraint.get("name") == "uq_movies_code" for constraint in constraints):
        op.drop_constraint("uq_movies_code", "movies", type_="unique")
