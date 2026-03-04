"""Add chunk_strategy to policies table

Revision ID: 026
Revises: 025
Create Date: 2026-03-03

Adds chunk_strategy column to the policies table to record which chunking
strategy was used when the document was embedded:
  - 'semantic' — hybrid heading-aware chunking
  - 'fixed'    — fixed-size paragraph accumulation (original behaviour)
  - NULL       — document was chunked before this feature was introduced

Existing rows default to NULL (unknown); new documents are labelled at
chunk time by SemanticScoringService.chunk_policy().
"""

from alembic import op
import sqlalchemy as sa

revision = '026'
down_revision = '025'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        'policies',
        sa.Column('chunk_strategy', sa.String(20), nullable=True),
    )


def downgrade() -> None:
    op.drop_column('policies', 'chunk_strategy')
