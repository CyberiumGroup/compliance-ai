"""Add information_types to assessments

Revision ID: 020
Revises: 019
Create Date: 2026-02-26

Stores the selected NIST SP 800-60 information type IDs as a JSON string,
used for risk profiling and AI context in compliance assessments.
"""

from alembic import op
import sqlalchemy as sa

revision = '020'
down_revision = '019'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("assessments", sa.Column("information_types", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("assessments", "information_types")
