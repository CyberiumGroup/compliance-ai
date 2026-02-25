"""Add is_rejected and rejected_at columns to policy_mappings

Revision ID: 016
Revises: 015
Create Date: 2026-02-25

Mappings are no longer hard-deleted on rejection. Instead they are soft-rejected
so that the scoring engine can skip already-seen pairs on subsequent runs.
States: Pending (is_rejected=False) → Rejected (is_rejected=True) → Pending (unreject)
"""

from alembic import op
import sqlalchemy as sa

revision = '016'
down_revision = '015'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "policy_mappings",
        sa.Column("is_rejected", sa.Boolean(), nullable=False, server_default="false"),
    )
    op.add_column(
        "policy_mappings",
        sa.Column("rejected_at", sa.DateTime(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("policy_mappings", "rejected_at")
    op.drop_column("policy_mappings", "is_rejected")
