import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from app.db.base import Base


class PolicyChunk(Base):
    """A semantic chunk of a policy document, used for relevance scoring."""

    __tablename__ = "policy_chunks"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    policy_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("policies.id", ondelete="CASCADE"), nullable=False
    )
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    chunk_text: Mapped[str] = mapped_column(Text, nullable=False)
    token_count: Mapped[int] = mapped_column(Integer, nullable=False)
    embedding_vector: Mapped[list | None] = mapped_column(JSON, nullable=True)
    embedding_model_version: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )

    policy: Mapped["Policy"] = relationship(back_populates="chunks")


class Policy(Base):
    """An organization's policy document"""

    __tablename__ = "policies"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    assessment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("assessments.id"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    version: Mapped[str | None] = mapped_column(String(50))
    owner: Mapped[str | None] = mapped_column(String(255))
    document_type: Mapped[str] = mapped_column(String(20), nullable=False, default="policy")
    section: Mapped[str | None] = mapped_column(String(20), nullable=True)
    file_format: Mapped[str | None] = mapped_column(String(20), nullable=True)
    chunk_strategy: Mapped[str | None] = mapped_column(String(20), nullable=True)
    file_path: Mapped[str | None] = mapped_column(String(500))
    content_text: Mapped[str | None] = mapped_column(Text)
    summary: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    assessment: Mapped["Assessment"] = relationship(back_populates="policies")
    mappings: Mapped[list["PolicyMapping"]] = relationship(back_populates="policy", cascade="all, delete-orphan")
    chunks: Mapped[list["PolicyChunk"]] = relationship(back_populates="policy", cascade="all, delete-orphan")


class PolicyMapping(Base):
    """Mapping between a policy and a framework requirement.

    Supports both legacy CSF subcategory mappings and new unified requirement mappings.
    """

    __tablename__ = "policy_mappings"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    policy_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("policies.id"), nullable=False
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
    relevance_percentage: Mapped[float | None] = mapped_column(Float, nullable=True)
    reasoning: Mapped[str | None] = mapped_column(Text)
    source_excerpt: Mapped[str | None] = mapped_column(Text)
    is_approved: Mapped[bool] = mapped_column(default=False, nullable=False)
    approved_by_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id")
    )
    approved_at: Mapped[datetime | None] = mapped_column(DateTime)
    is_rejected: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    rejected_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )

    policy: Mapped["Policy"] = relationship(back_populates="mappings")
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
    def requirement_level(self) -> int | None:
        return self.requirement.level if self.requirement else None

    @property
    def requirement_ancestors(self) -> list[dict] | None:
        """Ordered list of ancestors from root to immediate parent: [{code, name, display_order}, ...]."""
        if not self.requirement:
            return None
        ancestors = []
        node = self.requirement.parent
        while node is not None:
            ancestors.append({"code": node.code, "name": node.name, "display_order": node.display_order})
            node = node.parent
        ancestors.reverse()
        return ancestors if ancestors else None

    @property
    def requirement_display_order(self) -> int | None:
        return self.requirement.display_order if self.requirement else None

    @property
    def requirement_guidance(self) -> str | None:
        return self.requirement.guidance if self.requirement else None

    @property
    def policy_name(self) -> str | None:
        return self.policy.name if self.policy else None

    @property
    def policy_description(self) -> str | None:
        return self.policy.description if self.policy else None

    @property
    def policy_summary(self) -> str | None:
        return self.policy.summary if self.policy else None

    @property
    def policy_document_type(self) -> str | None:
        return self.policy.document_type if self.policy else None

    @property
    def policy_section(self) -> str | None:
        return self.policy.section if self.policy else None


from app.models.assessment import Assessment
from app.models.framework import CSFSubcategory
from app.models.unified_framework import FrameworkRequirement
from app.models.user import User
