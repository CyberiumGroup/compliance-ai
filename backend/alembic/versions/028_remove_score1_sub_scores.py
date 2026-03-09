"""Remove score1_design and score1_implementation sub-score columns

Revision ID: 028
Revises: 027
Create Date: 2026-03-09

The documentation score (score1) is now a single Covered/Partial/Gap label
mapped to 100/50/0. The design and implementation sub-scores no longer exist.
"""

from alembic import op
import sqlalchemy as sa

revision = '028'
down_revision = '027'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_column('requirement_scores', 'score1_design')
    op.drop_column('requirement_scores', 'score1_implementation')


def downgrade() -> None:
    op.add_column('requirement_scores', sa.Column('score1_design', sa.Float, nullable=True))
    op.add_column('requirement_scores', sa.Column('score1_implementation', sa.Float, nullable=True))
