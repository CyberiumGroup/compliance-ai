"""Mapping service — delegates generation to SemanticScoringService."""

import uuid
from datetime import datetime
from typing import Any, Optional

from sqlalchemy.orm import Session

from app.models.policy import Policy, PolicyMapping
from app.models.unified_framework import FrameworkRequirement
from app.core.config import settings
from app.services.audit.audit_service import AuditService
from app.services.frameworks.requirement_service import RequirementService


class AIMappingService:
    """Mapping service. Generation now delegates to SemanticScoringService."""

    def __init__(self, db: Session):
        self.db = db
        self.audit_service = AuditService(db)
        self.requirement_service = RequirementService(db)

    def generate_mappings_for_assessment(
        self,
        assessment_id: uuid.UUID,
        user_id: uuid.UUID | None = None,
        confidence_threshold: float | None = None,
    ) -> dict[str, Any]:
        """Generate policy-requirement mappings using semantic relevance scoring.

        Delegates to SemanticScoringService which implements the algorithm
        described in docs/semantic-relevance-scoring.md.
        """
        from app.services.mapping.semantic_scorer import SemanticScoringService

        scorer = SemanticScoringService(self.db)
        result = scorer.score_assessment(
            assessment_id=assessment_id,
            user_id=user_id,
            threshold=confidence_threshold,
        )

        # Normalise return shape to match what the API endpoint expects
        return {
            "assessment_id": result["assessment_id"],
            "suggestions_count": result["mappings_created"],
            "policy_mappings": result["mappings_created"],
            "suggestions": [],  # individual suggestions not returned for performance
        }

    def clear_all_mappings(
        self,
        assessment_id: uuid.UUID,
        user_id: uuid.UUID | None = None,
    ) -> dict[str, int]:
        """Delete all policy mappings for an assessment."""
        policy_ids = self.db.query(Policy.id).filter(Policy.assessment_id == assessment_id).subquery()
        policy_count = (
            self.db.query(PolicyMapping)
            .filter(PolicyMapping.policy_id.in_(self.db.query(policy_ids)))
            .delete(synchronize_session=False)
        )

        self.audit_service.log_delete(
            entity_type="all_mappings",
            entity_id=assessment_id,
            old_values={
                "policy_mappings_deleted": policy_count,
            },
            user_id=user_id,
        )

        self.db.commit()

        return {
            "policy_mappings_deleted": policy_count,
            "total_deleted": policy_count,
        }

    def approve_mapping(
        self,
        mapping_id: uuid.UUID,
        mapping_type: str,
        approved: bool,
        user_id: uuid.UUID,
    ) -> dict[str, Any]:
        """Approve or reject a mapping suggestion."""
        mapping = self.db.query(PolicyMapping).filter(PolicyMapping.id == mapping_id).first()

        if not mapping:
            return {"success": False, "error": "Mapping not found"}

        mapping.is_approved = approved
        mapping.approved_by_id = user_id
        mapping.approved_at = datetime.utcnow() if approved else None

        # Audit log
        self.audit_service.log_approval(
            entity_type="policy_mapping",
            entity_id=mapping_id,
            approved=approved,
            user_id=user_id,
        )

        self.db.commit()

        return {
            "mapping_id": mapping_id,
            "mapping_type": "policy",
            "is_approved": approved,
            "approved_at": mapping.approved_at.isoformat() if mapping.approved_at else None,
        }

    def create_manual_mapping(
        self,
        entity_id: uuid.UUID,
        requirement_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> dict[str, Any]:
        """Create a manual mapping (auto-approved)."""
        mapping = PolicyMapping(
            id=uuid.uuid4(),
            policy_id=entity_id,
            requirement_id=requirement_id,
            confidence_score=1.0,
            is_approved=True,
            approved_by_id=user_id,
            approved_at=datetime.utcnow(),
            created_at=datetime.utcnow(),
        )

        self.db.add(mapping)

        self.audit_service.log_create(
            entity_type="policy_mapping",
            entity_id=mapping.id,
            new_values={
                "entity_id": str(entity_id),
                "requirement_id": str(requirement_id),
                "is_manual": True,
            },
            user_id=user_id,
        )

        self.db.commit()

        return {
            "mapping_id": mapping.id,
            "entity_type": "policy",
            "is_approved": True,
        }

    def get_mapping_coverage(
        self,
        assessment_id: uuid.UUID,
        framework_id: Optional[uuid.UUID] = None,
    ) -> dict[str, Any]:
        """Get mapping coverage statistics for an assessment."""
        # Get requirements in scope
        if framework_id:
            requirements = self.requirement_service.get_assessable_requirements(framework_id)
        else:
            from app.services.mapping.semantic_scorer import SemanticScoringService
            scorer = SemanticScoringService(self.db)
            requirements = scorer._get_assessment_requirements(assessment_id)

        requirement_ids = {str(req.id) for req in requirements}

        # Get approved mappings
        policy_mappings = (
            self.db.query(PolicyMapping)
            .join(Policy)
            .filter(
                Policy.assessment_id == assessment_id,
                PolicyMapping.is_approved == True,
            )
            .all()
        )

        # Count covered requirements
        covered = set()
        for mapping in policy_mappings:
            req_id = str(mapping.requirement_id or mapping.subcategory_id)
            if req_id in requirement_ids:
                covered.add(req_id)

        uncovered = requirement_ids - covered

        return {
            "total_requirements": len(requirements),
            "covered_requirements": len(covered),
            "uncovered_requirements": len(uncovered),
            "coverage_percentage": (
                len(covered) / len(requirements) * 100
                if requirements else 0
            ),
            "uncovered_requirement_ids": list(uncovered),
        }
