"""Add per-requirement threshold table

Revision ID: 022
Revises: 021
Create Date: 2026-02-26

Stores per-requirement relevance thresholds per assessment, allowing fine-grained
control over which policy mappings qualify as control documentation for scoring.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = '022'
down_revision = '021'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'assessment_requirement_thresholds',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('assessment_id', UUID(as_uuid=True), sa.ForeignKey('assessments.id', ondelete='CASCADE'), nullable=False),
        sa.Column('requirement_id', UUID(as_uuid=True), sa.ForeignKey('framework_requirements.id', ondelete='CASCADE'), nullable=False),
        sa.Column('threshold', sa.Float(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.CheckConstraint('threshold >= 0 AND threshold <= 100', name='threshold_range_check'),
        sa.UniqueConstraint('assessment_id', 'requirement_id', name='uq_assessment_requirement_threshold'),
    )
    op.create_index('ix_assessment_req_thresholds_assessment_id', 'assessment_requirement_thresholds', ['assessment_id'])


def downgrade() -> None:
    op.drop_index('ix_assessment_req_thresholds_assessment_id', table_name='assessment_requirement_thresholds')
    op.drop_table('assessment_requirement_thresholds')
