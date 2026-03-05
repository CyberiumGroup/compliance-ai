"""PolicyFact model — one row per control fact extracted from a policy/evidence document."""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from app.db.base import Base


class PolicyFact(Base):
    """A single control fact extracted from a policy or evidence document.

    Facts are extracted at document upload time by FactExtractionService and
    stored here for reuse across all scoring runs. This avoids re-reading raw
    documents during scoring — the scoring LLM only sees structured facts.

    Fact types
    ----------
    policy_control
        Extracted from policy/procedure documents (document_type == 'policy').
        Describes what the organisation has defined, committed to, or designed.
        Key attributes include: what, scope, responsible_party, frequency,
        trigger, conditions, exceptions, tools.

    evidence_observation
        Extracted from evidence artifacts (document_type == 'evidence').
        Describes what the organisation demonstrably does in practice.
        Key attributes include: what, scope, time_period, actor, result,
        anomalies.

    Filtering (Option A — document-level)
    -------------------------------------
    At scoring time, facts are selected by fetching all PolicyFact rows for
    every document that passes the requirement-level relevance threshold
    (PolicyMapping.relevance_percentage >= threshold). All facts from a
    qualifying document are passed to the scoring LLM — no fact-level
    filtering is applied.

    FUTURE — Fact-level semantic filtering (NOT YET IMPLEMENTED)
    -------------------------------------------------------------
    The `embedding_vector` column exists to support a planned upgrade to
    fact-level relevance filtering (Option B). When implemented, the process
    will be:

      1. After extraction, embed each fact's `statement` field using
         text-embedding-3-small (same model used for chunk embeddings).
      2. Store the resulting vector in `embedding_vector`.
      3. At scoring time, compute cosine similarity between each fact's
         embedding and the target requirement's embedding.
      4. Pass only the top-K most similar facts to the scoring LLM,
         replacing the current document-level filter.

    This will improve precision (fewer irrelevant facts in the scoring
    context) while maintaining high recall (facts are pre-extracted from all
    qualifying documents). Until this is implemented, `embedding_vector`
    remains NULL for all rows.

    See: docs/llm-assisted-requirement-scoring.md §Control Fact Filtering
    """

    __tablename__ = "policy_facts"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    policy_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("policies.id", ondelete="CASCADE"), nullable=False
    )

    # ── Core fields ───────────────────────────────────────────────────────────

    fact_index: Mapped[int] = mapped_column(
        Integer, nullable=False, comment="Ordering of this fact within its document"
    )
    fact_type: Mapped[str] = mapped_column(
        String(30), nullable=False, comment="'policy_control' | 'evidence_observation'"
    )
    statement: Mapped[str] = mapped_column(
        Text, nullable=False,
        comment="Atomic, independently verifiable claim in subject–verb–object form"
    )

    # ── Flexible attribute bag (differs by fact_type) ─────────────────────────
    # policy_control:    what, scope, responsible_party, frequency, trigger,
    #                    conditions, exceptions, tools
    # evidence_observation: what, scope, time_period, actor, result, anomalies
    key_attributes: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # explicit — stated directly in the document
    # implied  — strongly suggested but not stated verbatim
    # (evidence_observation facts do not use this field)
    confidence: Mapped[str | None] = mapped_column(
        String(20), nullable=True, comment="'explicit' | 'implied' (policy_control only)"
    )

    # {document_name: str, section: str}
    document_reference: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # ── Extraction metadata ───────────────────────────────────────────────────

    extraction_model: Mapped[str | None] = mapped_column(
        String(100), nullable=True, comment="Model used to extract this fact"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )

    # ── FUTURE: fact-level embedding (NOT YET IMPLEMENTED) ───────────────────
    # See class docstring for full description of the planned implementation.
    # Do not populate this column until the fact-level filtering feature is built.
    embedding_vector: Mapped[list | None] = mapped_column(
        JSON, nullable=True, default=None
    )

    # ── Relationships ─────────────────────────────────────────────────────────
    policy: Mapped["Policy"] = relationship(back_populates="facts")


from app.models.policy import Policy  # noqa: E402
