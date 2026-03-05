"""Add policy_facts table and facts_extracted_at to policies

Revision ID: 027
Revises: 026
Create Date: 2026-03-04

Introduces control-fact extraction storage:

policy_facts
    One row per atomic control fact extracted from a policy or evidence document.
    fact_type distinguishes design facts ('policy_control') extracted from policy
    documents and implementation facts ('evidence_observation') extracted from
    evidence documents.

    embedding_vector is reserved for future fact-level semantic filtering (Option B)
    but is NOT yet populated. All rows will have NULL embedding_vector until that
    feature is implemented.

policies.facts_extracted_at
    Timestamp set when fact extraction completes for a document (NULL = not yet run).
    Zero facts extracted still sets this timestamp (extraction ran but found nothing).
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


revision = '027'
down_revision = '026'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── policy_facts ─────────────────────────────────────────────────────────
    op.create_table(
        'policy_facts',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column(
            'policy_id',
            UUID(as_uuid=True),
            sa.ForeignKey('policies.id', ondelete='CASCADE'),
            nullable=False,
        ),
        # Core fields
        sa.Column(
            'fact_index', sa.Integer, nullable=False,
            comment='Ordering of this fact within its document',
        ),
        sa.Column(
            'fact_type', sa.String(30), nullable=False,
            comment="'policy_control' | 'evidence_observation'",
        ),
        sa.Column(
            'statement', sa.Text, nullable=False,
            comment='Atomic, independently verifiable claim in subject–verb–object form',
        ),
        # Flexible attribute bag — schema differs by fact_type
        sa.Column('key_attributes', sa.JSON, nullable=True),
        sa.Column(
            'confidence', sa.String(20), nullable=True,
            comment="'explicit' | 'implied' — policy_control only",
        ),
        sa.Column(
            'document_reference', sa.JSON, nullable=True,
            comment='{document_name: str, section: str}',
        ),
        # Extraction metadata
        sa.Column('extraction_model', sa.String(100), nullable=True),
        sa.Column(
            'created_at', sa.DateTime,
            server_default=sa.func.now(), nullable=False,
        ),
        # FUTURE: fact-level semantic embedding (NOT YET POPULATED — see model docstring)
        sa.Column('embedding_vector', sa.JSON, nullable=True),
    )

    op.create_index(
        'ix_policy_facts_policy_id',
        'policy_facts',
        ['policy_id'],
    )
    op.create_index(
        'ix_policy_facts_policy_id_fact_index',
        'policy_facts',
        ['policy_id', 'fact_index'],
    )

    # ── policies.facts_extracted_at ───────────────────────────────────────────
    op.add_column(
        'policies',
        sa.Column('facts_extracted_at', sa.DateTime, nullable=True),
    )


def downgrade() -> None:
    op.drop_column('policies', 'facts_extracted_at')
    op.drop_index('ix_policy_facts_policy_id_fact_index', table_name='policy_facts')
    op.drop_index('ix_policy_facts_policy_id', table_name='policy_facts')
    op.drop_table('policy_facts')
