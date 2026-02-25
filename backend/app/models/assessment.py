import uuid
from datetime import datetime
from enum import Enum

from sqlalchemy import DateTime, ForeignKey, String, Text, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import Optional

from app.db.base import Base


class AssessmentStatus(str, Enum):
    DRAFT = "draft"
    IN_PROGRESS = "in_progress"
    REVIEW = "review"
    COMPLETED = "completed"
    ARCHIVED = "archived"


class AssessmentDepth(str, Enum):
    DESIGN = "design"
    IMPLEMENTATION = "implementation"


class Assessment(Base):
    """A compliance assessment for an organization"""

    __tablename__ = "assessments"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    organization_name: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(
        String(50), default=AssessmentStatus.DRAFT.value, nullable=False
    )
    depth_level: Mapped[str] = mapped_column(
        String(50), default=AssessmentDepth.DESIGN.value, nullable=False
    )
    ai_prompt_overrides: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    created_by_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    created_by: Mapped["User"] = relationship()
    policies: Mapped[list["Policy"]] = relationship(back_populates="assessment")
    interview_sessions: Mapped[list["InterviewSession"]] = relationship(back_populates="assessment")
    subcategory_scores: Mapped[list["SubcategoryScore"]] = relationship(back_populates="assessment")
    category_scores: Mapped[list["CategoryScore"]] = relationship(back_populates="assessment")
    function_scores: Mapped[list["FunctionScore"]] = relationship(back_populates="assessment")
    deviations: Mapped[list["Deviation"]] = relationship(back_populates="assessment")
    reports: Mapped[list["Report"]] = relationship(back_populates="assessment")


from app.models.user import User
from app.models.policy import Policy
from app.models.interview import InterviewSession
from app.models.score import SubcategoryScore, CategoryScore, FunctionScore
from app.models.deviation import Deviation
from app.models.report import Report
