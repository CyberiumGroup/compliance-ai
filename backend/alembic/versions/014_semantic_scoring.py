"""Add policy_chunks table and relevance_percentage to policy_mappings

Revision ID: 014
Revises: 013
Create Date: 2026-02-25

Implements the semantic relevance scoring engine per docs/semantic-relevance-scoring.md.
Policy documents are chunked and embedded; relevance_percentage stores the normalized
cosine similarity score (0-100) for each policy-requirement mapping.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '014'
down_revision = '013'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'policy_chunks',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('policy_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('chunk_index', sa.Integer(), nullable=False),
        sa.Column('chunk_text', sa.Text(), nullable=False),
        sa.Column('token_count', sa.Integer(), nullable=False),
        sa.Column('embedding_vector', sa.JSON(), nullable=True),
        sa.Column('embedding_model_version', sa.String(100), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['policy_id'], ['policies.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_policy_chunks_policy_id', 'policy_chunks', ['policy_id'])

    op.add_column(
        'policy_mappings',
        sa.Column('relevance_percentage', sa.Float(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column('policy_mappings', 'relevance_percentage')
    op.drop_index('ix_policy_chunks_policy_id', table_name='policy_chunks')
    op.drop_table('policy_chunks')
