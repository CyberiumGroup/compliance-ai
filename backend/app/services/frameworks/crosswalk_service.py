"""Service for managing cross-framework requirement mappings (crosswalks)."""

import uuid
import json
from datetime import datetime
from typing import Optional, Any

from sqlalchemy.orm import Session
from tenacity import retry, stop_after_attempt, wait_exponential

from app.core.config import settings
from app.models.unified_framework import (
    Framework,
    FrameworkRequirement,
    RequirementCrosswalk,
    MappingType,
    MappingSource,
)
from app.services.clustering.similarity_service import SimilarityService


class CrosswalkService:
    """Service for managing cross-framework requirement mappings.

    Generates and validates mappings between requirements in different
    frameworks using a combination of embedding similarity and LLM validation.
    """

    def __init__(self, db: Session):
        self.db = db
        self.similarity_service = SimilarityService(db)
        self._ai_client = None

    @property
    def ai_client(self):
        """Lazy initialization of OpenAI client for LLM validation."""
        if self._ai_client is None:
            if not settings.openai_api_key:
                raise ValueError("OPENAI_API_KEY not configured")
            from openai import OpenAI
            self._ai_client = OpenAI(api_key=settings.openai_api_key)
        return self._ai_client

    def generate_crosswalks(
        self,
        source_framework_id: uuid.UUID,
        target_framework_id: uuid.UUID,
        similarity_threshold: float = 0.75,
        top_k_per_requirement: int = 5,
        validate_with_llm: bool = True,
        auto_approve_threshold: float = 0.9,
        prompt_suffix: Optional[str] = None,
    ) -> list[RequirementCrosswalk]:
        """Generate cross-framework mappings using embeddings and optional LLM validation.

        Pipeline:
        1. Find candidate mappings using embedding similarity
        2. Optionally validate with LLM for semantic accuracy
        3. Auto-approve high confidence mappings
        4. Queue medium confidence for human review

        Args:
            source_framework_id: Source framework UUID
            target_framework_id: Target framework UUID
            similarity_threshold: Minimum embedding similarity (0.0 to 1.0)
            top_k_per_requirement: Max candidates per source requirement
            validate_with_llm: Whether to validate candidates with LLM
            auto_approve_threshold: Auto-approve if confidence >= this

        Returns:
            List of created RequirementCrosswalk objects
        """
        # Stage 1: Find candidates using embedding similarity
        candidates = self.similarity_service.find_cross_framework_candidates(
            source_framework_id=source_framework_id,
            target_framework_id=target_framework_id,
            top_k_per_requirement=top_k_per_requirement,
            threshold=similarity_threshold,
        )

        if not candidates:
            return []

        created_crosswalks = []

        for source, target, similarity in candidates:
            # Check if mapping already exists
            existing = self._get_existing_crosswalk(source.id, target.id)
            if existing:
                continue

            # Stage 2: LLM validation (optional)
            mapping_type = MappingType.RELATED
            confidence = similarity
            reasoning = None

            if validate_with_llm:
                llm_result = self._validate_mapping_with_llm(source, target, prompt_suffix=prompt_suffix)
                if llm_result:
                    mapping_type = llm_result.get("mapping_type", MappingType.RELATED)
                    # Combine embedding and LLM confidence
                    llm_confidence = llm_result.get("confidence", 0.5)
                    confidence = (similarity + llm_confidence) / 2
                    reasoning = llm_result.get("reasoning")

                    # Skip if LLM says no relationship
                    if mapping_type == "none":
                        continue

            # Stage 3: Create crosswalk
            crosswalk = RequirementCrosswalk(
                id=uuid.uuid4(),
                source_requirement_id=source.id,
                target_requirement_id=target.id,
                mapping_type=mapping_type.value if isinstance(mapping_type, MappingType) else mapping_type,
                confidence_score=confidence,
                mapping_source=MappingSource.AI_GENERATED.value,
                reasoning=reasoning,
                is_approved=confidence >= auto_approve_threshold,
                approved_at=datetime.utcnow() if confidence >= auto_approve_threshold else None,
            )
            self.db.add(crosswalk)
            created_crosswalks.append(crosswalk)

        self.db.commit()
        return created_crosswalks

    def _get_existing_crosswalk(
        self,
        source_id: uuid.UUID,
        target_id: uuid.UUID,
    ) -> Optional[RequirementCrosswalk]:
        """Check if a crosswalk already exists between two requirements."""
        return (
            self.db.query(RequirementCrosswalk)
            .filter(
                RequirementCrosswalk.source_requirement_id == source_id,
                RequirementCrosswalk.target_requirement_id == target_id,
            )
            .first()
        )

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
    )
    def _validate_mapping_with_llm(
        self,
        source: FrameworkRequirement,
        target: FrameworkRequirement,
        prompt_suffix: Optional[str] = None,
    ) -> Optional[dict[str, Any]]:
        """Use LLM to validate and classify a requirement mapping.

        Args:
            source: Source requirement
            target: Target requirement

        Returns:
            Dictionary with mapping_type, confidence, and reasoning
        """
        prompt = f"""Analyze the relationship between these two compliance requirements from different frameworks.

SOURCE REQUIREMENT ({source.code}):
Name: {source.name}
Description: {source.description or 'N/A'}
{f'Guidance: {source.guidance}' if source.guidance else ''}

TARGET REQUIREMENT ({target.code}):
Name: {target.name}
Description: {target.description or 'N/A'}
{f'Guidance: {target.guidance}' if target.guidance else ''}

Classify the relationship and respond with JSON:
{{
    "mapping_type": "equivalent" | "partial" | "related" | "none",
    "confidence": 0.0-1.0,
    "reasoning": "Brief explanation of the relationship"
}}

Definitions:
- "equivalent": Requirements are essentially the same, addressing identical objectives
- "partial": Target partially satisfies source OR source partially satisfies target
- "related": Requirements are related but distinct, covering adjacent topics
- "none": No meaningful relationship between requirements

Respond ONLY with the JSON object."""

        if prompt_suffix:
            prompt += f"\n\nAdditional context from the assessor:\n{prompt_suffix}"

        try:
            response = self.ai_client.chat.completions.create(
                model=settings.ai_model,
                max_tokens=500,
                temperature=0.2,
                messages=[{"role": "user", "content": prompt}],
            )

            content = response.choices[0].message.content.strip()
            # Handle markdown code blocks
            if content.startswith("```"):
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]

            result = json.loads(content)

            # Validate and normalize mapping_type
            valid_types = {"equivalent", "partial", "related", "none"}
            if result.get("mapping_type") not in valid_types:
                result["mapping_type"] = "related"

            return result

        except Exception as e:
            # Log error and return None to skip LLM validation
            print(f"LLM validation error: {e}")
            return None

    def approve_crosswalk(
        self,
        crosswalk_id: uuid.UUID,
        approved_by_id: uuid.UUID,
    ) -> Optional[RequirementCrosswalk]:
        """Approve a pending crosswalk mapping.

        Args:
            crosswalk_id: The crosswalk's UUID
            approved_by_id: The approving user's UUID

        Returns:
            Updated RequirementCrosswalk or None if not found
        """
        crosswalk = (
            self.db.query(RequirementCrosswalk)
            .filter(RequirementCrosswalk.id == crosswalk_id)
            .first()
        )

        if not crosswalk:
            return None

        crosswalk.is_approved = True
        crosswalk.approved_by_id = approved_by_id
        crosswalk.approved_at = datetime.utcnow()
        self.db.commit()

        return crosswalk

    def reject_crosswalk(
        self,
        crosswalk_id: uuid.UUID,
    ) -> bool:
        """Reject (delete) a pending crosswalk mapping.

        Args:
            crosswalk_id: The crosswalk's UUID

        Returns:
            True if deleted, False if not found
        """
        result = (
            self.db.query(RequirementCrosswalk)
            .filter(RequirementCrosswalk.id == crosswalk_id)
            .delete()
        )
        self.db.commit()
        return result > 0

    def create_manual_crosswalk(
        self,
        source_requirement_id: uuid.UUID,
        target_requirement_id: uuid.UUID,
        mapping_type: MappingType,
        reasoning: Optional[str] = None,
        created_by_id: Optional[uuid.UUID] = None,
    ) -> RequirementCrosswalk:
        """Create a manual crosswalk mapping.

        Args:
            source_requirement_id: Source requirement UUID
            target_requirement_id: Target requirement UUID
            mapping_type: Type of mapping relationship
            reasoning: Optional explanation
            created_by_id: Optional user who created the mapping

        Returns:
            Created RequirementCrosswalk
        """
        crosswalk = RequirementCrosswalk(
            id=uuid.uuid4(),
            source_requirement_id=source_requirement_id,
            target_requirement_id=target_requirement_id,
            mapping_type=mapping_type.value,
            confidence_score=1.0,  # Manual mappings have full confidence
            mapping_source=MappingSource.MANUAL.value,
            reasoning=reasoning,
            is_approved=True,
            approved_by_id=created_by_id,
            approved_at=datetime.utcnow(),
        )
        self.db.add(crosswalk)
        self.db.commit()
        return crosswalk

    def get_crosswalk(
        self,
        crosswalk_id: uuid.UUID,
    ) -> Optional[RequirementCrosswalk]:
        """Get a crosswalk by ID."""
        return (
            self.db.query(RequirementCrosswalk)
            .filter(RequirementCrosswalk.id == crosswalk_id)
            .first()
        )

    def list_crosswalks(
        self,
        source_framework_id: Optional[uuid.UUID] = None,
        target_framework_id: Optional[uuid.UUID] = None,
        is_approved: Optional[bool] = None,
        mapping_type: Optional[MappingType] = None,
        min_confidence: Optional[float] = None,
    ) -> list[RequirementCrosswalk]:
        """List crosswalks with optional filters.

        Args:
            source_framework_id: Filter by source framework
            target_framework_id: Filter by target framework
            is_approved: Filter by approval status
            mapping_type: Filter by mapping type
            min_confidence: Minimum confidence score

        Returns:
            List of RequirementCrosswalk objects
        """
        query = self.db.query(RequirementCrosswalk)

        if source_framework_id:
            query = query.join(
                FrameworkRequirement,
                RequirementCrosswalk.source_requirement_id == FrameworkRequirement.id,
            ).filter(FrameworkRequirement.framework_id == source_framework_id)

        if target_framework_id:
            # Need a second join for target
            target_req = self.db.query(FrameworkRequirement).filter(
                FrameworkRequirement.framework_id == target_framework_id
            ).subquery()
            query = query.filter(
                RequirementCrosswalk.target_requirement_id.in_(
                    self.db.query(target_req.c.id)
                )
            )

        if is_approved is not None:
            query = query.filter(RequirementCrosswalk.is_approved == is_approved)

        if mapping_type:
            query = query.filter(
                RequirementCrosswalk.mapping_type == mapping_type.value
            )

        if min_confidence is not None:
            query = query.filter(
                RequirementCrosswalk.confidence_score >= min_confidence
            )

        return query.order_by(RequirementCrosswalk.confidence_score.desc()).all()

    def get_mappings_for_requirement(
        self,
        requirement_id: uuid.UUID,
        as_source: bool = True,
        as_target: bool = True,
        is_approved: Optional[bool] = None,
    ) -> list[RequirementCrosswalk]:
        """Get all crosswalks involving a requirement.

        Args:
            requirement_id: The requirement's UUID
            as_source: Include mappings where requirement is source
            as_target: Include mappings where requirement is target
            is_approved: Optional filter by approval status

        Returns:
            List of RequirementCrosswalk objects
        """
        conditions = []

        if as_source:
            conditions.append(
                RequirementCrosswalk.source_requirement_id == requirement_id
            )

        if as_target:
            conditions.append(
                RequirementCrosswalk.target_requirement_id == requirement_id
            )

        if not conditions:
            return []

        from sqlalchemy import or_
        query = self.db.query(RequirementCrosswalk).filter(or_(*conditions))

        if is_approved is not None:
            query = query.filter(RequirementCrosswalk.is_approved == is_approved)

        return query.all()

    def get_equivalent_requirements(
        self,
        requirement_id: uuid.UUID,
        transitive: bool = False,
    ) -> list[FrameworkRequirement]:
        """Get all requirements that are equivalent to the given requirement.

        Args:
            requirement_id: The requirement's UUID
            transitive: If True, follow transitive equivalence chains

        Returns:
            List of equivalent FrameworkRequirement objects
        """
        equivalent_ids = set()

        # Direct equivalents
        crosswalks = self.get_mappings_for_requirement(
            requirement_id,
            is_approved=True,
        )

        for cw in crosswalks:
            if cw.mapping_type == MappingType.EQUIVALENT.value:
                if cw.source_requirement_id == requirement_id:
                    equivalent_ids.add(cw.target_requirement_id)
                else:
                    equivalent_ids.add(cw.source_requirement_id)

        if transitive:
            # BFS to find transitive equivalents
            queue = list(equivalent_ids)
            visited = equivalent_ids.copy()
            visited.add(requirement_id)

            while queue:
                current_id = queue.pop(0)
                cws = self.get_mappings_for_requirement(current_id, is_approved=True)

                for cw in cws:
                    if cw.mapping_type == MappingType.EQUIVALENT.value:
                        other_id = (
                            cw.target_requirement_id
                            if cw.source_requirement_id == current_id
                            else cw.source_requirement_id
                        )
                        if other_id not in visited:
                            visited.add(other_id)
                            equivalent_ids.add(other_id)
                            queue.append(other_id)

        # Fetch requirements
        if not equivalent_ids:
            return []

        return (
            self.db.query(FrameworkRequirement)
            .filter(FrameworkRequirement.id.in_(equivalent_ids))
            .all()
        )

    def get_crosswalk_statistics(
        self,
        framework_ids: Optional[list[uuid.UUID]] = None,
    ) -> dict:
        """Get statistics about crosswalks.

        Args:
            framework_ids: Optional list of frameworks to analyze

        Returns:
            Dictionary with crosswalk statistics
        """
        query = self.db.query(RequirementCrosswalk)

        total = query.count()
        approved = query.filter(RequirementCrosswalk.is_approved == True).count()
        pending = total - approved

        # Count by type
        by_type = {}
        for mt in MappingType:
            count = query.filter(
                RequirementCrosswalk.mapping_type == mt.value
            ).count()
            by_type[mt.value] = count

        # Count by source
        by_source = {}
        for ms in MappingSource:
            count = query.filter(
                RequirementCrosswalk.mapping_source == ms.value
            ).count()
            by_source[ms.value] = count

        # Average confidence
        from sqlalchemy import func
        avg_confidence = (
            self.db.query(func.avg(RequirementCrosswalk.confidence_score))
            .scalar()
        )

        return {
            "total_crosswalks": total,
            "approved": approved,
            "pending_review": pending,
            "by_type": by_type,
            "by_source": by_source,
            "average_confidence": round(avg_confidence or 0, 3),
        }
