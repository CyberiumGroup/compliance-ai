"""Make subcategory_id nullable on mapping tables

Revision ID: 011
Revises: 010
Create Date: 2026-02-12

The subcategory_id column is a legacy FK to csf_subcategories.
Unified framework mappings use requirement_id instead, so
subcategory_id must be nullable to support both paths.
"""

from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "011"
down_revision: Union[str, None] = "010"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column("control_mappings", "subcategory_id", nullable=True)
    op.alter_column("policy_mappings", "subcategory_id", nullable=True)


def downgrade() -> None:
    op.alter_column("control_mappings", "subcategory_id", nullable=False)
    op.alter_column("policy_mappings", "subcategory_id", nullable=False)
