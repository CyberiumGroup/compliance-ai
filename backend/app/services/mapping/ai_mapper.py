"""AI-powered mapping service for policies and controls to framework requirements."""

import uuid
from datetime import datetime
from typing import Any, Optional

from sqlalchemy.orm import Session

from app.models.control import Control, ControlMapping
from app.models.policy import Policy, PolicyMapping
from app.models.framework import CSFSubcategory
from app.models.unified_framework import FrameworkRequirement, AssessmentFrameworkScope
from app.core.ai_client import ai_client
from app.core.config import settings
from app.services.audit.audit_service import AuditService
from app.services.frameworks.requirement_service import RequirementService


class AIMappingService:
    """Service for generating AI-powered mapping suggestions.

    Supports mapping to both legacy CSF subcategories and unified framework requirements.
    """

    def __init__(self, db: Session):
        self.db = db
        self.audit_service = AuditService(db)
        self.requirement_service = RequirementService(db)

    def generate_mappings_for_assessment(
        self,
        assessment_id: uuid.UUID,
        user_id: uuid.UUID | None = None,
        include_policies: bool = True,
        include_controls: bool = True,
        confidence_threshold: float | None = None,
        use_unified_framework: bool = True,
    ) -> dict[str, Any]:
        """
        Generate mapping suggestions for all policies and controls in an assessment.

        Args:
            assessment_id: Assessment to generate mappings for
            user_id: User requesting the generation
            include_policies: Whether to generate policy mappings
            include_controls: Whether to generate control mappings
            confidence_threshold: Minimum confidence score (default from settings)
            use_unified_framework: If True, map to unified requirements; else legacy CSF

        Returns:
            Summary of generated mappings
        """
        if confidence_threshold is None:
            confidence_threshold = settings.default_confidence_threshold

        # Get requirements to map to
        if use_unified_framework:
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
        else:
            # Legacy: use CSF subcategories
            subcategories = self.db.query(CSFSubcategory).all()
            req_data = [
                {"code": sc.code, "description": sc.description, "id": sc.id}
                for sc in subcategories
            ]

        # Delete existing mappings for this assessment before regenerating
        if include_controls:
            existing_control_mappings = (
                self.db.query(ControlMapping)
                .join(Control)
                .filter(Control.assessment_id == assessment_id)
                .all()
            )
            for m in existing_control_mappings:
                self.db.delete(m)

        if include_policies:
            existing_policy_mappings = (
                self.db.query(PolicyMapping)
                .join(Policy)
                .filter(Policy.assessment_id == assessment_id)
                .all()
            )
            for m in existing_policy_mappings:
                self.db.delete(m)

        self.db.flush()

        suggestions = []
        policy_mappings_count = 0
        control_mappings_count = 0

        # Generate policy mappings
        if include_policies:
            policies = self.db.query(Policy).filter(
                Policy.assessment_id == assessment_id
            ).all()

            for policy in policies:
                if not policy.content_text:
                    continue

                policy_suggestions = self._generate_mappings_for_entity(
                    entity=policy,
                    entity_type="policy",
                    requirements=req_data,
                    confidence_threshold=confidence_threshold,
                )

                for suggestion in policy_suggestions:
                    # Create policy mapping
                    mapping = PolicyMapping(
                        id=uuid.uuid4(),
                        policy_id=policy.id,
                        subcategory_id=suggestion["requirement_id"] if not use_unified_framework else None,
                        requirement_id=suggestion["requirement_id"] if use_unified_framework else None,
                        confidence_score=suggestion["confidence_score"],
                        reasoning=suggestion.get("reasoning"),
                        source_excerpt=suggestion.get("source_excerpt"),
                        is_approved=False,
                        created_at=datetime.utcnow(),
                    )
                    self.db.add(mapping)
                    policy_mappings_count += 1

                    suggestions.append({
                        "entity_type": "policy",
                        "entity_id": policy.id,
                        "entity_name": policy.name,
                        "requirement_id": suggestion["requirement_id"],
                        "requirement_code": suggestion["requirement_code"],
                        "confidence_score": suggestion["confidence_score"],
                        "reasoning": suggestion.get("reasoning"),
                    })

        # Generate control mappings
        if include_controls:
            controls = self.db.query(Control).filter(
                Control.assessment_id == assessment_id
            ).all()

            for control in controls:
                control_text = f"{control.name}\n{control.description or ''}"
                if not control_text.strip():
                    continue

                control_suggestions = self._generate_mappings_for_entity(
                    entity=control,
                    entity_type="control",
                    requirements=req_data,
                    confidence_threshold=confidence_threshold,
                )

                for suggestion in control_suggestions:
                    # Create control mapping
                    mapping = ControlMapping(
                        id=uuid.uuid4(),
                        control_id=control.id,
                        subcategory_id=suggestion["requirement_id"] if not use_unified_framework else None,
                        requirement_id=suggestion["requirement_id"] if use_unified_framework else None,
                        confidence_score=suggestion["confidence_score"],
                        reasoning=suggestion.get("reasoning"),
                        is_approved=False,
                        created_at=datetime.utcnow(),
                    )
                    self.db.add(mapping)
                    control_mappings_count += 1

                    suggestions.append({
                        "entity_type": "control",
                        "entity_id": control.id,
                        "entity_name": control.name,
                        "requirement_id": suggestion["requirement_id"],
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
            "control_mappings": control_mappings_count,
            "suggestions": suggestions,
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
        entity: Policy | Control,
        entity_type: str,
        requirements: list[dict],
        confidence_threshold: float,
    ) -> list[dict[str, Any]]:
        """Generate mapping suggestions for a single entity."""
        if entity_type == "policy":
            text = entity.content_text or ""
        else:
            text = f"{entity.name}\n{entity.description or ''}"

        if not text.strip():
            return []

        try:
            ai_suggestions = ai_client.generate_mapping_suggestions(
                entity_text=text,
                entity_type=entity_type,
                subcategories=[
                    {"code": req["code"], "description": req["description"]}
                    for req in requirements
                ],
            )
        except Exception:
            # If AI fails, return empty list
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
        """
        Approve or reject a mapping suggestion.

        Args:
            mapping_id: ID of the mapping to approve/reject
            mapping_type: "policy" or "control"
            approved: Whether to approve
            user_id: User making the decision

        Returns:
            Updated mapping information
        """
        if mapping_type == "policy":
            mapping = self.db.query(PolicyMapping).filter(PolicyMapping.id == mapping_id).first()
        else:
            mapping = self.db.query(ControlMapping).filter(ControlMapping.id == mapping_id).first()

        if not mapping:
            return {"success": False, "error": "Mapping not found"}

        mapping.is_approved = approved
        mapping.approved_by_id = user_id
        mapping.approved_at = datetime.utcnow() if approved else None

        # Audit log
        self.audit_service.log_approval(
            entity_type=f"{mapping_type}_mapping",
            entity_id=mapping_id,
            approved=approved,
            user_id=user_id,
        )

        self.db.commit()

        return {
            "mapping_id": mapping_id,
            "mapping_type": mapping_type,
            "is_approved": approved,
            "approved_at": mapping.approved_at.isoformat() if mapping.approved_at else None,
        }

    def create_manual_mapping(
        self,
        entity_id: uuid.UUID,
        entity_type: str,
        requirement_id: uuid.UUID,
        user_id: uuid.UUID,
        use_unified_framework: bool = True,
    ) -> dict[str, Any]:
        """Create a manual mapping (auto-approved).

        Args:
            entity_id: ID of the policy or control
            entity_type: "policy" or "control"
            requirement_id: ID of the requirement to map to
            user_id: User creating the mapping
            use_unified_framework: If True, set requirement_id; else only subcategory_id

        Returns:
            Created mapping information
        """
        if entity_type == "policy":
            mapping = PolicyMapping(
                id=uuid.uuid4(),
                policy_id=entity_id,
                subcategory_id=requirement_id,  # For backward compat
                requirement_id=requirement_id if use_unified_framework else None,
                confidence_score=1.0,
                is_approved=True,
                approved_by_id=user_id,
                approved_at=datetime.utcnow(),
                created_at=datetime.utcnow(),
            )
        else:
            mapping = ControlMapping(
                id=uuid.uuid4(),
                control_id=entity_id,
                subcategory_id=requirement_id,  # For backward compat
                requirement_id=requirement_id if use_unified_framework else None,
                confidence_score=1.0,
                is_approved=True,
                approved_by_id=user_id,
                approved_at=datetime.utcnow(),
                created_at=datetime.utcnow(),
            )

        self.db.add(mapping)

        self.audit_service.log_create(
            entity_type=f"{entity_type}_mapping",
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
            "entity_type": entity_type,
            "is_approved": True,
        }

    def get_mapping_coverage(
        self,
        assessment_id: uuid.UUID,
        framework_id: Optional[uuid.UUID] = None,
    ) -> dict[str, Any]:
        """Get mapping coverage statistics for an assessment.

        Args:
            assessment_id: Assessment to analyze
            framework_id: Optional filter to specific framework

        Returns:
            Coverage statistics
        """
        # Get requirements in scope
        if framework_id:
            requirements = self.requirement_service.get_assessable_requirements(framework_id)
        else:
            requirements = self._get_assessment_requirements(assessment_id)

        requirement_ids = {str(req.id) for req in requirements}

        # Get approved mappings
        control_mappings = (
            self.db.query(ControlMapping)
            .join(Control)
            .filter(
                Control.assessment_id == assessment_id,
                ControlMapping.is_approved == True,
            )
            .all()
        )

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
        covered_by_control = set()
        covered_by_policy = set()

        for mapping in control_mappings:
            req_id = str(mapping.requirement_id or mapping.subcategory_id)
            if req_id in requirement_ids:
                covered_by_control.add(req_id)

        for mapping in policy_mappings:
            req_id = str(mapping.requirement_id or mapping.subcategory_id)
            if req_id in requirement_ids:
                covered_by_policy.add(req_id)

        covered = covered_by_control | covered_by_policy
        uncovered = requirement_ids - covered

        return {
            "total_requirements": len(requirements),
            "covered_requirements": len(covered),
            "uncovered_requirements": len(uncovered),
            "coverage_percentage": (
                len(covered) / len(requirements) * 100
                if requirements else 0
            ),
            "covered_by_control_only": len(covered_by_control - covered_by_policy),
            "covered_by_policy_only": len(covered_by_policy - covered_by_control),
            "covered_by_both": len(covered_by_control & covered_by_policy),
            "uncovered_requirement_ids": list(uncovered),
        }
