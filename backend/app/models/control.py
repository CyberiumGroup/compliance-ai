import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Control(Base):
    """An organization's internal control"""

    __tablename__ = "controls"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    assessment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("assessments.id"), nullable=False
    )
    identifier: Mapped[str] = mapped_column(String(100), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    owner: Mapped[str | None] = mapped_column(String(255))
    control_type: Mapped[str | None] = mapped_column(String(100))
    implementation_status: Mapped[str | None] = mapped_column(String(50))
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    assessment: Mapped["Assessment"] = relationship(back_populates="controls")
    mappings: Mapped[list["ControlMapping"]] = relationship(back_populates="control")


class ControlMapping(Base):
    """Mapping between a control and a framework requirement.

    Supports both legacy CSF subcategory mappings and new unified requirement mappings.
    """

    __tablename__ = "control_mappings"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    control_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("controls.id"), nullable=False
    )
    # Legacy: CSF subcategory reference (will be deprecated)
    subcategory_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("csf_subcategories.id"), nullable=True
    )
    # New: Unified requirement reference (use this for new code)
    requirement_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("framework_requirements.id"), nullable=True
    )
    confidence_score: Mapped[float | None] = mapped_column()
    reasoning: Mapped[str | None] = mapped_column(Text)
    is_approved: Mapped[bool] = mapped_column(default=False, nullable=False)
    approved_by_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id")
    )
    approved_at: Mapped[datetime | None] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )

    control: Mapped["Control"] = relationship(back_populates="mappings")
    subcategory: Mapped["CSFSubcategory"] = relationship()
    requirement: Mapped["FrameworkRequirement | None"] = relationship()
    approved_by: Mapped["User | None"] = relationship()

    @property
    def subcategory_code(self) -> str | None:
        return self.subcategory.code if self.subcategory else None

    @property
    def requirement_code(self) -> str | None:
        return self.requirement.code if self.requirement else None

    @property
    def requirement_name(self) -> str | None:
        return self.requirement.name if self.requirement else None

    @property
    def requirement_description(self) -> str | None:
        return self.requirement.description if self.requirement else None

    @property
    def requirement_framework_name(self) -> str | None:
        if self.requirement and self.requirement.framework:
            return self.requirement.framework.name
        return None

    @property
    def requirement_parent_code(self) -> str | None:
        if self.requirement and self.requirement.parent:
            return self.requirement.parent.code
        return None

    @property
    def control_name(self) -> str | None:
        return self.control.name if self.control else None

    @property
    def control_description(self) -> str | None:
        return self.control.description if self.control else None


from app.models.assessment import Assessment
from app.models.framework import CSFSubcategory
from app.models.unified_framework import FrameworkRequirement
from app.models.user import User
