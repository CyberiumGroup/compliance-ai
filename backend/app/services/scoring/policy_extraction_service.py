"""Policy Statement Extraction Service.

Extracts specific policy statements from mapped policy documents for a given
requirement. This runs before LLM scoring phases and produces structured
statements that are saved per (assessment, requirement).

LLM call inputs:
  - The requirement (code, name, description)
  - Implementation examples for the requirement (if any, from framework metadata)
  - All qualifying mapped policy documents (same threshold logic as scoring)

LLM output: list of extracted statements, each with document title and section.
"""

import json
import logging
import math
import uuid
from datetime import datetime

from openai import AsyncOpenAI
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.assessment import Assessment
from app.models.policy import Policy, PolicyChunk, PolicyMapping
from app.models.policy_statement import PolicyStatement
from app.models.requirement_threshold import AssessmentRequirementThreshold
from app.models.unified_framework import FrameworkRequirement

logger = logging.getLogger(__name__)


def _cosine_sim(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    mag_a = math.sqrt(sum(x * x for x in a))
    mag_b = math.sqrt(sum(x * x for x in b))
    return dot / (mag_a * mag_b) if mag_a and mag_b else 0.0


class PolicyExtractionService:
    """Extracts and persists policy statements from mapped documents for a requirement."""

    def __init__(self, db: Session) -> None:
        self.db = db
        self.client = AsyncOpenAI(api_key=settings.openai_api_key)
        self.model = settings.scoring_model

    async def extract_for_requirement(
        self,
        requirement_id: uuid.UUID,
        assessment_id: uuid.UUID,
    ) -> list[dict]:
        """Run policy extraction for one requirement.

        Deletes any existing statements for this (assessment, requirement) pair,
        then calls the LLM and persists the results.

        Returns a list of statement dicts ready to send to the frontend.
        """
        req = (
            self.db.query(FrameworkRequirement)
            .filter(FrameworkRequirement.id == requirement_id)
            .first()
        )
        assessment = (
            self.db.query(Assessment)
            .filter(Assessment.id == assessment_id)
            .first()
        )
        if not req or not assessment:
            raise ValueError("Requirement or assessment not found")
        
        # Delete existing statements for this pair
        self.db.query(PolicyStatement).filter(
            PolicyStatement.assessment_id == assessment_id,
            PolicyStatement.requirement_id == requirement_id,
        ).delete(synchronize_session=False)
        self.db.flush()

        # Fetch qualifying policy documents (policy type only, not evidence)
        qualifying = self._get_qualifying_policy_docs(req.id, assessment)

        logger.info(
            "Policy extraction for requirement %s (%s): %d qualifying document(s): [%s]",
            req.code or req.id,
            req.name or "",
            len(qualifying),
            ", ".join(m.policy.name for m in qualifying if m.policy),
        )

        if not qualifying:
            self.db.commit()
            return []

        # Build prompt
        policy_docs = self._build_doc_list(qualifying, req)
        impl_examples = self._get_implementation_examples(req)
        prompt = self._build_prompt(req, policy_docs, impl_examples)

        # Call LLM
        raw_statements = await self._call_llm(prompt)

        # Persist and return
        rows = []
        for item in raw_statements:
            stmt_text = (item.get("statement") or "").strip()
            doc_title = (item.get("document_title") or "").strip()
            if not stmt_text or not doc_title:
                continue

            row = PolicyStatement(
                id=uuid.uuid4(),
                assessment_id=assessment_id,
                requirement_id=requirement_id,
                statement=stmt_text,
                document_title=doc_title,
                document_section=(item.get("document_section") or "").strip() or None,
                is_relevant=True,
                created_at=datetime.utcnow(),
            )
            self.db.add(row)
            rows.append(row)

        self.db.commit()
        return [self._row_to_dict(r) for r in rows]

    def get_statements(
        self,
        requirement_id: uuid.UUID,
        assessment_id: uuid.UUID,
    ) -> list[dict]:
        """Return all relevant statements for a requirement."""
        rows = (
            self.db.query(PolicyStatement)
            .filter(
                PolicyStatement.assessment_id == assessment_id,
                PolicyStatement.requirement_id == requirement_id,
            )
            .order_by(PolicyStatement.created_at)
            .all()
        )
        return [self._row_to_dict(r) for r in rows]

    def mark_irrelevant(
        self,
        statement_id: uuid.UUID,
        assessment_id: uuid.UUID,
    ) -> bool:
        """Mark a statement as irrelevant (soft-delete). Returns False if not found."""
        row = (
            self.db.query(PolicyStatement)
            .filter(
                PolicyStatement.id == statement_id,
                PolicyStatement.assessment_id == assessment_id,
            )
            .first()
        )
        if not row:
            return False
        self.db.delete(row)
        self.db.commit()
        return True

    # ─── Private helpers ──────────────────────────────────────────────────────

    def _get_qualifying_policy_docs(
        self,
        requirement_id: uuid.UUID,
        assessment: Assessment,
    ) -> list[PolicyMapping]:
        """Return qualifying policy-type mappings (same logic as LLM scoring engine)."""
        threshold_override = (
            self.db.query(AssessmentRequirementThreshold)
            .filter(
                AssessmentRequirementThreshold.assessment_id == assessment.id,
                AssessmentRequirementThreshold.requirement_id == requirement_id,
            )
            .first()
        )
        threshold = (
            threshold_override.threshold
            if threshold_override
            else (assessment.policy_mapping_threshold or 80.0)
        )

        mappings = (
            self.db.query(PolicyMapping)
            .join(Policy, PolicyMapping.policy_id == Policy.id)
            .filter(
                Policy.assessment_id == assessment.id,
                Policy.document_type == "policy",
                PolicyMapping.requirement_id == requirement_id,
                PolicyMapping.is_rejected == False,  # noqa: E712
            )
            .all()
        )

        return [
            m for m in mappings
            if (m.relevance_percentage is not None and m.relevance_percentage >= threshold)
            and m.policy
        ]

    def _build_doc_list(
        self,
        mappings: list[PolicyMapping],
        req: FrameworkRequirement,
    ) -> list[dict]:
        """Deduplicate by policy_id and build document dicts using top-K chunks.

        For each qualifying policy, scores its chunks against the requirement
        embedding and takes the top settings.extraction_top_k_chunks most relevant.
        Falls back to full content_text if no chunk embeddings are available.
        """
        top_k = settings.extraction_top_k_chunks
        req_embedding: list[float] | None = req.embedding
        seen: set[uuid.UUID] = set()
        docs = []
        for mapping in mappings:
            if not mapping.policy or mapping.policy_id in seen:
                continue
            seen.add(mapping.policy_id)

            content: str | None = None
            if req_embedding:
                top_chunks = self._top_k_chunks(mapping.policy, req_embedding, top_k)
                if top_chunks:
                    content = "\n\n".join(top_chunks)
                    logger.info(
                        "  %s: using %d top chunk(s) from %d available",
                        mapping.policy.name,
                        len(top_chunks),
                        len(mapping.policy.chunks),
                    )

            if content is None:
                logger.info("  %s: falling back to full content_text", mapping.policy.name)
                content = mapping.policy.content_text

            if not content:
                logger.warning("  %s: no usable content, skipping", mapping.policy.name)
                continue

            docs.append({"document_title": mapping.policy.name, "content": content})
        return docs

    def _top_k_chunks(
        self,
        policy: Policy,
        req_embedding: list[float],
        k: int,
    ) -> list[str]:
        """Return text of the top-K chunks ranked by cosine similarity to the requirement."""
        chunks = (
            self.db.query(PolicyChunk)
            .filter(
                PolicyChunk.policy_id == policy.id,
                PolicyChunk.embedding_vector.isnot(None),
            )
            .all()
        )
        if not chunks:
            return []
        scored = [
            (_cosine_sim(c.embedding_vector, req_embedding), c.chunk_text)
            for c in chunks
        ]
        scored.sort(key=lambda x: x[0], reverse=True)
        return [text for _, text in scored[:k]]

    @staticmethod
    def _get_implementation_examples(req: FrameworkRequirement) -> list[str]:
        """Extract implementation examples from requirement metadata, if any."""
        meta = req.extra_metadata or {}
        examples = meta.get("implementation_examples") or []
        if isinstance(examples, list):
            return [str(e) for e in examples if e]
        return []

    def _build_prompt(
        self,
        req: FrameworkRequirement,
        policy_docs: list[dict],
        impl_examples: list[str],
    ) -> dict:
        available_titles = [d["document_title"] for d in policy_docs]

        task = (
            "Extract every specific policy statement from the provided documents that is "
            "directly relevant to the given compliance requirement. "
            "Each policy_document contains either the full document text or the most "
            "relevant excerpts from that document. "
            "A policy statement is a concrete, specific commitment, rule, or procedure — "
            "not a vague general statement. "
            "There may be zero, one, or many relevant statements across all documents. "
            "Search through ALL provided documents regardless of whether you found "
            "statements in earlier documents — do not stop after the first match. "
            "For each statement, provide as much detail as possible, capturing the full "
            "context and specifics of the policy text. "
            "For document_title, use ONLY titles from the available_document_titles list, "
            "copied exactly character-for-character. "
            "document_title must be the title of the document the statement was physically "
            "extracted from — not the title of any other document that the statement "
            "happens to reference or mention. "
            "For document_section, identify the section, heading, or clause the statement "
            "comes from (e.g. '3.2 Access Control', 'Appendix A'). "
            "If no relevant statements exist in any document, return an empty statements list."
        )

        prompt: dict = {
            "task": task,
            "requirement": {
                "code": req.code,
                "name": req.name,
                "description": req.description or "",
            },
            "available_document_titles": available_titles,
            "policy_documents": policy_docs,
            "output_format": {
                "statements": [
                    {
                        "statement": "The full extracted policy statement text with all relevant detail",
                        "document_title": "exact title from available_document_titles",
                        "document_section": "section/heading/clause name or null",
                    }
                ]
            },
        }

        if impl_examples:
            prompt["implementation_examples"] = impl_examples
            prompt["task"] += (
                " The implementation_examples show what good implementation of this "
                "requirement looks like in practice — use them to help identify which "
                "policy statements are genuinely relevant."
            )

        return prompt

    async def _call_llm(self, prompt: dict) -> list[dict]:
        """Call the LLM and return the extracted statements list."""
        system_msg = (
            "You are a compliance documentation analyst. "
            "Respond ONLY with valid JSON matching the output_format structure. "
            "Do not include any text outside the JSON."
        )
        user_msg = json.dumps(prompt, ensure_ascii=False)

        response = await self.client.chat.completions.create(
            model=self.model,
            temperature=0.2,
            max_tokens=settings.extraction_max_output_tokens,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": system_msg},
                {"role": "user", "content": user_msg},
            ],
        )

        choice = response.choices[0]
        if choice.finish_reason == "length":
            logger.warning("Policy extraction response truncated (finish_reason=length) — increase extraction_max_output_tokens")

        content = choice.message.content or "{}"
        try:
            parsed = json.loads(content)
            return parsed.get("statements", [])
        except json.JSONDecodeError:
            logger.warning("Policy extraction LLM returned non-JSON: %s", content[:200])
            return []

    @staticmethod
    def _row_to_dict(row: PolicyStatement) -> dict:
        return {
            "id": str(row.id),
            "assessment_id": str(row.assessment_id),
            "requirement_id": str(row.requirement_id),
            "statement": row.statement,
            "document_title": row.document_title,
            "document_section": row.document_section,
            "is_relevant": row.is_relevant,
            "created_at": row.created_at.isoformat(),
        }
