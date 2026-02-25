"""AI-powered mapping service for policies to framework requirements."""

import uuid
from datetime import datetime
from typing import Any, Optional

from sqlalchemy.orm import Session

from app.models.policy import Policy, PolicyMapping
from app.models.unified_framework import FrameworkRequirement, AssessmentFrameworkScope
from app.core.ai_client import ai_client
from app.core.config import settings
from app.services.audit.audit_service import AuditService
from app.services.frameworks.requirement_service import RequirementService


class AIMappingService:
    """Service for generating AI-powered mapping suggestions."""

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
        """
        Generate mapping suggestions for all policies in an assessment.

        Args:
            assessment_id: Assessment to generate mappings for
            user_id: User requesting the generation
            confidence_threshold: Minimum confidence score (default from settings)

        Returns:
            Summary of generated mappings
        """
        if confidence_threshold is None:
            confidence_threshold = settings.default_confidence_threshold

        # Get requirements to map to
        requirements = self._get_assessment_requirements(assessment_id)
        req_data = [
            {
                "code": req.code,
                "description": req.description or req.name,
                "id": req.id,
                "framework_id": req.framework_id,
            }
            for req in requirements
        ]

        # Build set of existing policy→requirement pairs to skip duplicates
        existing_pm = (
            self.db.query(PolicyMapping.policy_id, PolicyMapping.requirement_id)
            .join(Policy)
            .filter(Policy.assessment_id == assessment_id)
            .all()
        )
        existing_policy_pairs: set[tuple] = {(pm.policy_id, pm.requirement_id) for pm in existing_pm}

        suggestions = []
        policy_mappings_count = 0

        policies = self.db.query(Policy).filter(
            Policy.assessment_id == assessment_id
        ).all()

        for policy in policies:
            if not policy.content_text:
                continue

            policy_suggestions = self._generate_mappings_for_entity(
                policy=policy,
                requirements=req_data,
                confidence_threshold=confidence_threshold,
            )

            for suggestion in policy_suggestions:
                req_id = suggestion["requirement_id"]
                if (policy.id, req_id) in existing_policy_pairs:
                    continue

                mapping = PolicyMapping(
                    id=uuid.uuid4(),
                    policy_id=policy.id,
                    requirement_id=req_id,
                    confidence_score=suggestion["confidence_score"],
                    reasoning=suggestion.get("reasoning"),
                    source_excerpt=suggestion.get("source_excerpt"),
                    is_approved=False,
                    created_at=datetime.utcnow(),
                )
                self.db.add(mapping)
                existing_policy_pairs.add((policy.id, req_id))
                policy_mappings_count += 1

                suggestions.append({
                    "entity_type": "policy",
                    "entity_id": policy.id,
                    "entity_name": policy.name,
                    "requirement_id": req_id,
                    "requirement_code": suggestion["requirement_code"],
                    "confidence_score": suggestion["confidence_score"],
                    "reasoning": suggestion.get("reasoning"),
                })

        self.db.flush()

        # Audit log
        self.audit_service.log_generation(
            entity_type="mapping",
            entity_id=assessment_id,
            generation_type="ai_mappings",
            user_id=user_id,
            details=f"Generated {len(suggestions)} mapping suggestions",
        )

        self.db.commit()

        return {
            "assessment_id": assessment_id,
            "suggestions_count": len(suggestions),
            "policy_mappings": policy_mappings_count,
            "suggestions": suggestions,
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

    def _get_assessment_requirements(
        self,
        assessment_id: uuid.UUID,
    ) -> list[FrameworkRequirement]:
        """Get all assessable requirements in scope for an assessment."""
        # Check if assessment has explicit scope defined
        scopes = (
            self.db.query(AssessmentFrameworkScope)
            .filter(AssessmentFrameworkScope.assessment_id == assessment_id)
            .all()
        )

        if scopes:
            # Use the requirement service to get in-scope requirements
            return self.requirement_service.get_requirements_in_scope(assessment_id)
        else:
            # Fall back to all assessable requirements from all active frameworks
            return (
                self.db.query(FrameworkRequirement)
                .filter(FrameworkRequirement.is_assessable == True)
                .all()
            )

    def _generate_mappings_for_entity(
        self,
        policy: Policy,
        requirements: list[dict],
        confidence_threshold: float,
    ) -> list[dict[str, Any]]:
        """Generate mapping suggestions for a single policy."""
        text = policy.content_text or ""

        if not text.strip():
            return []

        try:
            ai_suggestions = ai_client.generate_mapping_suggestions(
                policy_text=text,
                subcategories=[
                    {"code": req["code"], "description": req["description"]}
                    for req in requirements
                ],
            )
        except Exception:
            return []

        # Map AI suggestions to internal format
        code_to_id = {req["code"]: req["id"] for req in requirements}
        suggestions = []

        for suggestion in ai_suggestions:
            code = suggestion.get("subcategory_code")
            confidence = suggestion.get("confidence_score", 0)

            if code not in code_to_id:
                continue

            if confidence < confidence_threshold:
                continue

            suggestions.append({
                "requirement_id": code_to_id[code],
                "requirement_code": code,
                "confidence_score": confidence,
                "reasoning": suggestion.get("reasoning"),
                "source_excerpt": suggestion.get("source_excerpt"),
            })

        return suggestions

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
            requirements = self._get_assessment_requirements(assessment_id)

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
