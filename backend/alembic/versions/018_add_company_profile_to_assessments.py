"""Add company profile fields to assessments

Revision ID: 018
Revises: 017
Create Date: 2026-02-26

Adds structured company profile fields used to give the AI richer context
during interviews and report generation.
"""

from alembic import op
import sqlalchemy as sa

revision = '018'
down_revision = '017'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("assessments", sa.Column("company_name", sa.String(255), nullable=True))
    op.add_column("assessments", sa.Column("industry", sa.String(255), nullable=True))
    op.add_column("assessments", sa.Column("business_description", sa.Text(), nullable=True))
    op.add_column("assessments", sa.Column("product_service_description", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("assessments", "product_service_description")
    op.drop_column("assessments", "business_description")
    op.drop_column("assessments", "industry")
    op.drop_column("assessments", "company_name")
