"""Add section and file_format columns to policies table.

Revision ID: 029
Revises: 028
Create Date: 2026-03-19
"""

from alembic import op
import sqlalchemy as sa

revision = "029"
down_revision = "028"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("policies", sa.Column("section", sa.String(20), nullable=True))
    op.add_column("policies", sa.Column("file_format", sa.String(20), nullable=True))


def downgrade() -> None:
    op.drop_column("policies", "file_format")
    op.drop_column("policies", "section")
