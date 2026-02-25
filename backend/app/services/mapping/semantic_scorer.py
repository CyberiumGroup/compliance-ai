"""Semantic relevance scoring service for policy-to-requirement mappings.

Implements the algorithm described in docs/semantic-relevance-scoring.md:
- Policy documents are split into overlapping chunks (~750 tokens each)
- Each chunk is embedded using text-embedding-3-small
- For each (policy, requirement) pair: doc_score_raw = max cosine similarity across chunks
- relevance_percentage = ((doc_score_raw + 1) / 2) * 100
- Only pairs at or above the configured threshold are stored as mappings

The source_excerpt stored for each mapping is the full text of the highest-scoring chunk.
"""

import re
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.policy import Policy, PolicyChunk, PolicyMapping
from app.models.unified_framework import FrameworkRequirement, AssessmentFrameworkScope
from app.services.audit.audit_service import AuditService
from app.services.clustering.embedding_service import EmbeddingService
from app.services.clustering.similarity_service import SimilarityService
from app.services.frameworks.requirement_service import RequirementService

class SemanticScoringService:
    """Scores policies against framework requirements using semantic similarity."""

    def __init__(self, db: Session):
        self.db = db
        self.audit_service = AuditService(db)
        self.embedding_service = EmbeddingService(db)
        self.requirement_service = RequirementService(db)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def score_assessment(
        self,
        assessment_id: uuid.UUID,
        user_id: uuid.UUID | None = None,
        threshold: float | None = None,
    ) -> dict[str, Any]:
        """Generate policy-requirement mappings for an assessment using semantic scoring.

        For each policy in the assessment, chunks the document, embeds each chunk,
        then computes the max cosine similarity against each in-scope requirement.
        Stores all pairs that meet or exceed the relevance threshold as PolicyMapping
        records (pending approval).

        Args:
            assessment_id: Assessment to score
            user_id: User triggering the scoring
            threshold: Minimum relevance_percentage to store (default from settings)

        Returns:
            Summary dict with counts of mappings created
        """
        if threshold is None:
            threshold = settings.mapping_relevance_threshold

        # 1. Get in-scope requirements
        requirements = self._get_assessment_requirements(assessment_id)
        if not requirements:
            return {"assessment_id": assessment_id, "mappings_created": 0, "policies_scored": 0}

        # 2. Ensure all requirements have embeddings
        self._ensure_requirement_embeddings(requirements)

        # 3. Get policies with content
        policies = (
            self.db.query(Policy)
            .filter(Policy.assessment_id == assessment_id, Policy.content_text.isnot(None))
            .all()
        )

        # 4. Build set of already-mapped (policy_id, requirement_id) pairs to avoid duplicates
        existing_pairs: set[tuple] = {
            (pm.policy_id, pm.requirement_id)
            for pm in self.db.query(PolicyMapping.policy_id, PolicyMapping.requirement_id)
            .join(Policy)
            .filter(Policy.assessment_id == assessment_id)
            .all()
        }

        mappings_created = 0

        for policy in policies:
            # 5. Chunk and embed policy (idempotent — reuses existing chunks)
            chunks = self._get_or_create_chunks(policy)
            if not chunks:
                continue

            # 6. Score against each requirement
            for req in requirements:
                if (policy.id, req.id) in existing_pairs:
                    continue
                if not req.embedding:
                    continue

                # Find best chunk (max cosine similarity)
                best_chunk, doc_score_raw = self._score_policy_against_requirement(
                    chunks, req.embedding
                )

                relevance_percentage = ((doc_score_raw + 1) / 2) * 100

                if relevance_percentage < threshold:
                    continue

                mapping = PolicyMapping(
                    id=uuid.uuid4(),
                    policy_id=policy.id,
                    requirement_id=req.id,
                    confidence_score=doc_score_raw,
                    relevance_percentage=round(relevance_percentage, 2),
                    source_excerpt=best_chunk.chunk_text,
                    is_approved=False,
                    created_at=datetime.utcnow(),
                )
                self.db.add(mapping)
                existing_pairs.add((policy.id, req.id))
                mappings_created += 1

        self.db.flush()

        self.audit_service.log_generation(
            entity_type="mapping",
            entity_id=assessment_id,
            generation_type="semantic_scoring",
            user_id=user_id,
            details=f"Generated {mappings_created} semantic mappings for {len(policies)} policies",
        )

        self.db.commit()

        return {
            "assessment_id": assessment_id,
            "mappings_created": mappings_created,
            "policies_scored": len(policies),
            "requirements_scored": len(requirements),
            "threshold_used": threshold,
        }

    def chunk_policy(self, policy: Policy) -> list[PolicyChunk]:
        """Chunk and embed a policy document, replacing any existing chunks.

        Args:
            policy: Policy with content_text to chunk

        Returns:
            List of stored PolicyChunk records
        """
        # Delete existing chunks for idempotency
        self.db.query(PolicyChunk).filter(PolicyChunk.policy_id == policy.id).delete()

        if not policy.content_text or not policy.content_text.strip():
            return []

        raw_chunks = self._chunk_text(policy.content_text)
        if not raw_chunks:
            return []

        # Batch-embed all chunks in one API call
        texts = [c["text"] for c in raw_chunks]
        embeddings = self.embedding_service.generate_embeddings_batch(texts)

        chunks = []
        for i, (chunk_data, embedding) in enumerate(zip(raw_chunks, embeddings)):
            chunk = PolicyChunk(
                id=uuid.uuid4(),
                policy_id=policy.id,
                chunk_index=i,
                chunk_text=chunk_data["text"],
                token_count=chunk_data["token_count"],
                embedding_vector=embedding,
                embedding_model_version=settings.embedding_model,
                created_at=datetime.utcnow(),
            )
            self.db.add(chunk)
            chunks.append(chunk)

        self.db.flush()
        return chunks

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _get_or_create_chunks(self, policy: Policy) -> list[PolicyChunk]:
        """Return existing chunks for a policy, or create them if missing."""
        existing = (
            self.db.query(PolicyChunk)
            .filter(PolicyChunk.policy_id == policy.id)
            .order_by(PolicyChunk.chunk_index)
            .all()
        )
        if existing:
            return existing
        return self.chunk_policy(policy)

    def _chunk_text(self, text: str) -> list[dict]:
        """Split text into overlapping chunks, preserving paragraph boundaries.

        Target: ~300 tokens per chunk (using 4 chars/token approximation).
        Overlap: ~12% of chunk size (~37 tokens).

        Args:
            text: Full document text

        Returns:
            List of dicts with 'text' and 'token_count' keys
        """
        chunk_size = settings.chunk_size_chars
        overlap = settings.chunk_overlap_chars

        # Split into paragraphs (prefer \n\n, fall back to \n)
        paragraphs = [p.strip() for p in re.split(r'\n\n+', text) if p.strip()]
        if not paragraphs:
            paragraphs = [p.strip() for p in text.split('\n') if p.strip()]

        chunks = []
        current_paras: list[str] = []
        current_size = 0

        for para in paragraphs:
            para_size = len(para)

            if current_size + para_size > chunk_size and current_paras:
                # Emit current chunk
                chunk_text = '\n\n'.join(current_paras)
                chunks.append({
                    "text": chunk_text,
                    "token_count": max(1, len(chunk_text) // 4),
                })

                # Build overlap: keep trailing paragraphs up to overlap_chars
                overlap_paras: list[str] = []
                overlap_size = 0
                for p in reversed(current_paras):
                    if overlap_size + len(p) <= overlap:
                        overlap_paras.insert(0, p)
                        overlap_size += len(p)
                    else:
                        break

                current_paras = overlap_paras
                current_size = overlap_size

            current_paras.append(para)
            current_size += para_size

        # Emit final chunk
        if current_paras:
            chunk_text = '\n\n'.join(current_paras)
            chunks.append({
                "text": chunk_text,
                "token_count": max(1, len(chunk_text) // 4),
            })

        return chunks

    def _score_policy_against_requirement(
        self,
        chunks: list[PolicyChunk],
        req_embedding: list[float],
    ) -> tuple[PolicyChunk, float]:
        """Return (best_chunk, max_cosine_similarity) across all chunks.

        Per spec section 3.4: aggregation is maximum only.
        """
        best_chunk = chunks[0]
        best_score = -1.0

        for chunk in chunks:
            if not chunk.embedding_vector:
                continue
            score = SimilarityService.cosine_similarity(req_embedding, chunk.embedding_vector)
            if score > best_score:
                best_score = score
                best_chunk = chunk

        return best_chunk, best_score

    def _get_assessment_requirements(
        self,
        assessment_id: uuid.UUID,
    ) -> list[FrameworkRequirement]:
        """Get all assessable requirements in scope for an assessment."""
        scopes = (
            self.db.query(AssessmentFrameworkScope)
            .filter(AssessmentFrameworkScope.assessment_id == assessment_id)
            .all()
        )

        if scopes:
            return self.requirement_service.get_requirements_in_scope(assessment_id)
        else:
            return (
                self.db.query(FrameworkRequirement)
                .filter(FrameworkRequirement.is_assessable == True)
                .all()
            )

    def _ensure_requirement_embeddings(
        self,
        requirements: list[FrameworkRequirement],
    ) -> None:
        """Generate and persist embeddings for any requirements that lack them."""
        missing = [r for r in requirements if not r.embedding]
        if not missing:
            return

        texts = [self.embedding_service.prepare_requirement_text(r) for r in missing]
        embeddings = self.embedding_service.generate_embeddings_batch(texts)

        for req, embedding in zip(missing, embeddings):
            req.embedding = embedding

        self.db.flush()
