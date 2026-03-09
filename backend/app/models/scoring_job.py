"""LLM scoring job and requirement score models."""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.assessment import Assessment
    from app.models.unified_framework import FrameworkRequirement


class RequirementElement(Base):
    """A decomposed element of a framework requirement (Phase 1 output).

    Cached per requirement — shared across all assessments. Once populated,
    elements are reused for all future scoring runs without additional LLM calls.
    """

    __tablename__ = "requirement_elements"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    requirement_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("framework_requirements.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    element_id: Mapped[str] = mapped_column(String(20), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )

    __table_args__ = (
        UniqueConstraint("requirement_id", "element_id", name="uq_requirement_element"),
    )

    requirement: Mapped["FrameworkRequirement"] = relationship()


class ScoringJob(Base):
    """Background scoring job tracking for an assessment."""

    __tablename__ = "scoring_jobs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    assessment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("assessments.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    status: Mapped[str] = mapped_column(String(20), default="pending", nullable=False)
    total_requirements: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    completed_requirements: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    failed_requirements: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )

    assessment: Mapped["Assessment"] = relationship()
    requirement_scores: Mapped[list["RequirementScore"]] = relationship(
        back_populates="scoring_job"
    )


class RequirementScore(Base):
    """LLM-computed scores for a single requirement in an assessment.

    Stores three 0–100% scores:
      score1 — Requirement Met by Documentation
      score2 — Risk-Based Best Practice Adequacy
      score3 — Peer Alignment
    """

    __tablename__ = "requirement_scores"

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
        index=True,
    )
    scoring_job_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("scoring_jobs.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Three scores (0.0–100.0)
    score1: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    score2: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    score3: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Full phase outputs (stored for transparency/debugging)
    phase2_output: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)  # Documentation score phase
    phase4_output: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    phase5_output: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    # Explanations
    score1_explanation: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    score2_explanation: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    score3_explanation: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    # Metadata
    model_used: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    llm_calls_used: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    scored_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="pending", nullable=False)
    skip_reason: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    __table_args__ = (
        UniqueConstraint(
            "assessment_id", "requirement_id", name="uq_assessment_requirement_score"
        ),
    )

    assessment: Mapped["Assessment"] = relationship()
    requirement: Mapped["FrameworkRequirement"] = relationship()
    scoring_job: Mapped[Optional["ScoringJob"]] = relationship(
        back_populates="requirement_scores"
    )
