"""Policy statement model — extracted policy statements per requirement."""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.assessment import Assessment
    from app.models.unified_framework import FrameworkRequirement


class PolicyStatement(Base):
    """A policy statement extracted from mapped policy documents for a requirement.

    Created by the Policy Extraction stage (pre-scoring). Statements are extracted
    via LLM from all qualifying policy documents mapped to the requirement.

    When a user re-runs extraction, all existing statements for that
    (assessment_id, requirement_id) pair are deleted and replaced.
    """

    __tablename__ = "policy_statements"

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

    # The extracted statement text
    statement: Mapped[str] = mapped_column(Text, nullable=False)
    # Title of the source document (matches PolicyMapping → Policy.name)
    document_title: Mapped[str] = mapped_column(String(500), nullable=False)
    # Section of the document the statement was extracted from
    document_section: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # User can mark a statement as irrelevant (soft-delete from scoring)
    is_relevant: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )

    assessment: Mapped["Assessment"] = relationship()
    requirement: Mapped["FrameworkRequirement"] = relationship()
