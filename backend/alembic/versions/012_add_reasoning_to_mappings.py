"""Add reasoning and source_excerpt to mapping tables

Revision ID: 012
Revises: 011
Create Date: 2026-02-12

Stores the AI's reasoning for each mapping suggestion and, for policy
mappings, a short excerpt from the source document that supports the mapping.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision: str = "012"
down_revision: Union[str, None] = "011"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("control_mappings", sa.Column("reasoning", sa.Text(), nullable=True))
    op.add_column("policy_mappings", sa.Column("reasoning", sa.Text(), nullable=True))
    op.add_column("policy_mappings", sa.Column("source_excerpt", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("policy_mappings", "source_excerpt")
    op.drop_column("policy_mappings", "reasoning")
    op.drop_column("control_mappings", "reasoning")
