"""Add summary column to policies table

Revision ID: 015
Revises: 014
Create Date: 2026-02-25

Stores an AI-generated high-level description of each policy document,
produced at upload time using the OpenAI chat completions API.
"""

from alembic import op
import sqlalchemy as sa

revision = '015'
down_revision = '014'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "policies",
        sa.Column("summary", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("policies", "summary")
