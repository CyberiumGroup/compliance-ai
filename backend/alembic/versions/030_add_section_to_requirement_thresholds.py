"""Add section column to assessment_requirement_thresholds.

Revision ID: 030
Revises: 029
Create Date: 2026-03-19
"""

from alembic import op
import sqlalchemy as sa

revision = "030"
down_revision = "029"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add section column, defaulting existing rows to 'policy'
    op.add_column(
        "assessment_requirement_thresholds",
        sa.Column("section", sa.String(20), nullable=False, server_default="policy"),
    )
    # Drop old unique constraint (assessment_id, requirement_id)
    op.drop_constraint(
        "uq_assessment_requirement_threshold",
        "assessment_requirement_thresholds",
        type_="unique",
    )
    # Add new unique constraint (assessment_id, requirement_id, section)
    op.create_unique_constraint(
        "uq_assessment_requirement_threshold_section",
        "assessment_requirement_thresholds",
        ["assessment_id", "requirement_id", "section"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_assessment_requirement_threshold_section",
        "assessment_requirement_thresholds",
        type_="unique",
    )
    op.create_unique_constraint(
        "uq_assessment_requirement_threshold",
        "assessment_requirement_thresholds",
        ["assessment_id", "requirement_id"],
    )
    op.drop_column("assessment_requirement_thresholds", "section")
