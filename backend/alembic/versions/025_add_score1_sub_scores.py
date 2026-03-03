"""Add Score 1 sub-score columns to requirement_scores

Revision ID: 025
Revises: 024
Create Date: 2026-03-02

Adds five new columns to requirement_scores to support the split Score 1
(Design + Implementation) approach:

  score1_design                  — Phase 2a result (0–100%), from policy docs
  score1_implementation          — Phase 2b result (0–100%); NULL if depth=design;
                                   0.0 if depth=implementation but no evidence docs
  phase2b_output                 — raw Phase 2b LLM output (JSONB)
  score1_design_explanation      — explanation from Phase 2a (JSONB)
  score1_implementation_explanation — explanation from Phase 2b (JSONB)

The existing score1 column is kept as the composite average for backward compat.
The existing phase2_output column becomes Phase 2a output (no rename needed).
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = '025'
down_revision = '024'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('requirement_scores', sa.Column('score1_design', sa.Float(), nullable=True))
    op.add_column('requirement_scores', sa.Column('score1_implementation', sa.Float(), nullable=True))
    op.add_column('requirement_scores', sa.Column('phase2b_output', JSONB(), nullable=True))
    op.add_column('requirement_scores', sa.Column('score1_design_explanation', JSONB(), nullable=True))
    op.add_column('requirement_scores', sa.Column('score1_implementation_explanation', JSONB(), nullable=True))


def downgrade() -> None:
    op.drop_column('requirement_scores', 'score1_implementation_explanation')
    op.drop_column('requirement_scores', 'score1_design_explanation')
    op.drop_column('requirement_scores', 'phase2b_output')
    op.drop_column('requirement_scores', 'score1_implementation')
    op.drop_column('requirement_scores', 'score1_design')
