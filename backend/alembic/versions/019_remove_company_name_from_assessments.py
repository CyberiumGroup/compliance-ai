"""Remove company_name from assessments (duplicate of organization_name)

Revision ID: 019
Revises: 018
Create Date: 2026-02-26
"""

from alembic import op
import sqlalchemy as sa

revision = '019'
down_revision = '018'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_column("assessments", "company_name")


def downgrade() -> None:
    op.add_column("assessments", sa.Column("company_name", sa.String(255), nullable=True))
