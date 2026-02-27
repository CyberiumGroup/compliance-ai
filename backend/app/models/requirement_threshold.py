"""Per-requirement threshold model."""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Float, ForeignKey, UniqueConstraint, CheckConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.assessment import Assessment
    from app.models.unified_framework import FrameworkRequirement


class AssessmentRequirementThreshold(Base):
    """Per-requirement relevance threshold override for an assessment.

    When a threshold is set here it overrides assessment.policy_mapping_threshold
    for that specific requirement during scoring.
    """

    __tablename__ = "assessment_requirement_thresholds"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    assessment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("assessments.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    requirement_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("framework_requirements.id", ondelete="CASCADE"),
        nullable=False,
    )
    threshold: Mapped[float] = mapped_column(Float, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    __table_args__ = (
        UniqueConstraint("assessment_id", "requirement_id", name="uq_assessment_requirement_threshold"),
        CheckConstraint("threshold >= 0 AND threshold <= 100", name="threshold_range_check"),
    )

    assessment: Mapped["Assessment"] = relationship()
    requirement: Mapped["FrameworkRequirement"] = relationship()
