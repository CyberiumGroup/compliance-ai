"""Add document_type to policies table

Revision ID: 024
Revises: 023
Create Date: 2026-03-02

Adds document_type column to the policies table to distinguish between:
  - 'policy'   — design-level policy documentation (existing behaviour, default)
  - 'evidence' — implementation evidence / audit artefacts (new)

All existing rows default to 'policy', so no backfill is needed.
"""

from alembic import op
import sqlalchemy as sa

revision = '024'
down_revision = '023'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        'policies',
        sa.Column(
            'document_type',
            sa.String(20),
            nullable=False,
            server_default='policy',
        ),
    )


def downgrade() -> None:
    op.drop_column('policies', 'document_type')
