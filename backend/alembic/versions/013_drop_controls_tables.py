"""Drop control_mappings and controls tables

Revision ID: 013
Revises: 012
Create Date: 2026-02-24

Controls have been removed from the application. This migration drops the
control_mappings and controls tables, which are no longer used.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '013'
down_revision = '012'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Drop control_mappings first (has FK to controls)
    op.drop_table('control_mappings')
    # Drop controls table
    op.drop_table('controls')


def downgrade() -> None:
    # Recreate controls table
    op.create_table(
        'controls',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('assessment_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('identifier', sa.String(100), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('owner', sa.String(255), nullable=True),
        sa.Column('control_type', sa.String(100), nullable=True),
        sa.Column('implementation_status', sa.String(50), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['assessment_id'], ['assessments.id']),
        sa.PrimaryKeyConstraint('id'),
    )

    # Recreate control_mappings table
    op.create_table(
        'control_mappings',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('control_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('subcategory_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('requirement_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('confidence_score', sa.Float(), nullable=True),
        sa.Column('reasoning', sa.Text(), nullable=True),
        sa.Column('is_approved', sa.Boolean(), nullable=False),
        sa.Column('approved_by_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('approved_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['approved_by_id'], ['users.id']),
        sa.ForeignKeyConstraint(['control_id'], ['controls.id']),
        sa.ForeignKeyConstraint(['requirement_id'], ['framework_requirements.id']),
        sa.ForeignKeyConstraint(['subcategory_id'], ['csf_subcategories.id']),
        sa.PrimaryKeyConstraint('id'),
    )
