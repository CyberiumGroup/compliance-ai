"""Add LLM scoring tables

Revision ID: 023
Revises: 022
Create Date: 2026-02-26

Creates tables for LLM-assisted requirement scoring:
  - requirement_elements: cached per-requirement decomposed elements (Phase 1)
  - scoring_jobs: background job tracking per assessment
  - requirement_scores: per-requirement scores (0-100%) for all 3 dimensions
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

revision = '023'
down_revision = '022'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # requirement_elements — Phase 1 output, cached per requirement
    op.create_table(
        'requirement_elements',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('requirement_id', UUID(as_uuid=True), sa.ForeignKey('framework_requirements.id', ondelete='CASCADE'), nullable=False),
        sa.Column('element_id', sa.String(20), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.UniqueConstraint('requirement_id', 'element_id', name='uq_requirement_element'),
    )
    op.create_index('ix_requirement_elements_requirement_id', 'requirement_elements', ['requirement_id'])

    # scoring_jobs — background job per assessment
    op.create_table(
        'scoring_jobs',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('assessment_id', UUID(as_uuid=True), sa.ForeignKey('assessments.id', ondelete='CASCADE'), nullable=False),
        sa.Column('status', sa.String(20), nullable=False, server_default='pending'),
        sa.Column('total_requirements', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('completed_requirements', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('failed_requirements', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('started_at', sa.DateTime(), nullable=True),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
    )
    op.create_index('ix_scoring_jobs_assessment_id', 'scoring_jobs', ['assessment_id'])

    # requirement_scores — per-requirement LLM scoring results
    op.create_table(
        'requirement_scores',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('assessment_id', UUID(as_uuid=True), sa.ForeignKey('assessments.id', ondelete='CASCADE'), nullable=False),
        sa.Column('requirement_id', UUID(as_uuid=True), sa.ForeignKey('framework_requirements.id', ondelete='CASCADE'), nullable=False),
        sa.Column('scoring_job_id', UUID(as_uuid=True), sa.ForeignKey('scoring_jobs.id', ondelete='SET NULL'), nullable=True),
        # Three scores (0.0–100.0)
        sa.Column('score1', sa.Float(), nullable=True),
        sa.Column('score2', sa.Float(), nullable=True),
        sa.Column('score3', sa.Float(), nullable=True),
        # Full phase outputs (stored for transparency/debugging)
        sa.Column('phase1_output', JSONB(), nullable=True),
        sa.Column('phase2_output', JSONB(), nullable=True),
        sa.Column('phase4_output', JSONB(), nullable=True),
        sa.Column('phase5_output', JSONB(), nullable=True),
        # Explanations
        sa.Column('score1_explanation', JSONB(), nullable=True),
        sa.Column('score2_explanation', JSONB(), nullable=True),
        sa.Column('score3_explanation', JSONB(), nullable=True),
        # Metadata
        sa.Column('model_used', sa.String(100), nullable=True),
        sa.Column('llm_calls_used', sa.Integer(), nullable=True),
        sa.Column('scored_at', sa.DateTime(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('status', sa.String(20), nullable=False, server_default='pending'),
        sa.Column('skip_reason', sa.String(50), nullable=True),
        sa.UniqueConstraint('assessment_id', 'requirement_id', name='uq_assessment_requirement_score'),
    )
    op.create_index('ix_requirement_scores_assessment_id', 'requirement_scores', ['assessment_id'])
    op.create_index('ix_requirement_scores_requirement_id', 'requirement_scores', ['requirement_id'])
    op.create_index('ix_requirement_scores_scoring_job_id', 'requirement_scores', ['scoring_job_id'])


def downgrade() -> None:
    op.drop_index('ix_requirement_scores_scoring_job_id', table_name='requirement_scores')
    op.drop_index('ix_requirement_scores_requirement_id', table_name='requirement_scores')
    op.drop_index('ix_requirement_scores_assessment_id', table_name='requirement_scores')
    op.drop_table('requirement_scores')

    op.drop_index('ix_scoring_jobs_assessment_id', table_name='scoring_jobs')
    op.drop_table('scoring_jobs')

    op.drop_index('ix_requirement_elements_requirement_id', table_name='requirement_elements')
    op.drop_table('requirement_elements')
