"""Add operating_effectiveness depth level

Revision ID: 021
Revises: 020
Create Date: 2026-02-26

The depth_level column is VARCHAR(50), so no schema change is needed.
This migration is a no-op placeholder to keep migration sequence consistent.
"""

from alembic import op
import sqlalchemy as sa

revision = '021'
down_revision = '020'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # No schema change needed — column is VARCHAR(50) and accepts any string value.
    pass


def downgrade() -> None:
    pass
