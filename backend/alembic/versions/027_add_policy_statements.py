"""Add policy_statements table

Revision ID: 027
Revises: 026
Create Date: 2026-03-09

Creates the policy_statements table used by the Policy Extraction stage.
Each row is one LLM-extracted policy statement from a mapped policy document,
linked to a specific requirement in a specific assessment.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = '027'
down_revision = '026'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'policy_statements',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('assessment_id', UUID(as_uuid=True),
                  sa.ForeignKey('assessments.id', ondelete='CASCADE'),
                  nullable=False, index=True),
        sa.Column('requirement_id', UUID(as_uuid=True),
                  sa.ForeignKey('framework_requirements.id', ondelete='CASCADE'),
                  nullable=False, index=True),
        sa.Column('statement', sa.Text, nullable=False),
        sa.Column('document_title', sa.String(500), nullable=False),
        sa.Column('document_section', sa.Text, nullable=True),
        sa.Column('is_relevant', sa.Boolean, nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime, nullable=False,
                  server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table('policy_statements')
