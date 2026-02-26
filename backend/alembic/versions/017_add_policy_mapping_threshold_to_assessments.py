"""Add policy_mapping_threshold column to assessments

Revision ID: 017
Revises: 016
Create Date: 2026-02-25

Stores the per-assessment default threshold (0.0–100.0) for the policy
mapping relevance slider so users don't have to reset it each session.
"""

from alembic import op
import sqlalchemy as sa

revision = '017'
down_revision = '016'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "assessments",
        sa.Column("policy_mapping_threshold", sa.Float(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("assessments", "policy_mapping_threshold")
