"""Gap detection service for identifying coverage gaps."""

import uuid
from typing import Any

from sqlalchemy.orm import Session

from app.models.control import Control, ControlMapping
from app.models.policy import Policy, PolicyMapping
from app.models.unified_framework import FrameworkRequirement, AssessmentFrameworkScope
from app.services.frameworks.requirement_service import RequirementService


class GapDetectionService:
    """Service for detecting gaps in framework requirement coverage."""

    def __init__(self, db: Session):
        self.db = db
        self.requirement_service = RequirementService(db)

    def detect_gaps(self, assessment_id: uuid.UUID) -> dict[str, Any]:
        """
        Detect coverage gaps for an assessment.

        Identifies assessable requirements that are missing approved mappings:
        - Requirements with no approved mappings (policy or control)
        - Requirements with only policy mappings
        - Requirements with only control mappings

        Returns:
            Gap analysis results
        """
        # Get assessable requirements in scope for this assessment
        requirements = self._get_assessment_requirements(assessment_id)

        if not requirements:
            return {
                "assessment_id": assessment_id,
                "total_gaps": 0,
                "unmapped_requirements": 0,
                "policy_only_count": 0,
                "control_only_count": 0,
                "coverage_percentage": 0.0,
                "gaps": [],
            }

        # Get approved policy mappings for this assessment
        policy_mappings = (
            self.db.query(PolicyMapping)
            .join(Policy)
            .filter(
                Policy.assessment_id == assessment_id,
                PolicyMapping.is_approved == True,
                PolicyMapping.requirement_id.isnot(None),
            )
            .all()
        )
        policy_req_ids = {pm.requirement_id for pm in policy_mappings}

        # Get approved control mappings for this assessment
        control_mappings = (
            self.db.query(ControlMapping)
            .join(Control)
            .filter(
                Control.assessment_id == assessment_id,
                ControlMapping.is_approved == True,
                ControlMapping.requirement_id.isnot(None),
            )
            .all()
        )
        control_req_ids = {cm.requirement_id for cm in control_mappings}

        # Build name lookups
        policy_names_by_req: dict[uuid.UUID, list[str]] = {}
        for pm in policy_mappings:
            policy = self.db.query(Policy).filter(Policy.id == pm.policy_id).first()
            if policy:
                policy_names_by_req.setdefault(pm.requirement_id, []).append(policy.name)

        control_names_by_req: dict[uuid.UUID, list[str]] = {}
        for cm in control_mappings:
            control = self.db.query(Control).filter(Control.id == cm.control_id).first()
            if control:
                control_names_by_req.setdefault(cm.requirement_id, []).append(control.name)

        gaps = []
        unmapped_count = 0
        policy_only_count = 0
        control_only_count = 0

        for req in requirements:
            has_policy = req.id in policy_req_ids
            has_control = req.id in control_req_ids

            if not has_policy and not has_control:
                gap_type = "unmapped_requirement"
                unmapped_count += 1
            elif has_policy and not has_control:
                gap_type = "policy_only"
                policy_only_count += 1
            elif has_control and not has_policy:
                gap_type = "control_only"
                control_only_count += 1
            else:
                # Fully covered
                continue

            # Get parent and framework info
            parent_code = req.parent.code if req.parent else None
            framework_name = req.framework.name if req.framework else None

            gaps.append({
                "gap_type": gap_type,
                "requirement_id": req.id,
                "requirement_code": req.code,
                "requirement_name": req.name,
                "requirement_description": req.description,
                "framework_name": framework_name,
                "parent_code": parent_code,
                "has_policy": has_policy,
                "has_control": has_control,
                "policy_names": policy_names_by_req.get(req.id),
                "control_names": control_names_by_req.get(req.id),
            })

        total_requirements = len(requirements)
        covered_count = total_requirements - unmapped_count
        coverage_percentage = (covered_count / total_requirements * 100) if total_requirements > 0 else 0

        return {
            "assessment_id": assessment_id,
            "total_requirements": total_requirements,
            "total_gaps": len(gaps),
            "unmapped_requirements": unmapped_count,
            "policy_only_count": policy_only_count,
            "control_only_count": control_only_count,
            "coverage_percentage": round(coverage_percentage, 2),
            "gaps": gaps,
        }

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
            # Fall back to all assessable requirements from all active frameworks
            return (
                self.db.query(FrameworkRequirement)
                .filter(FrameworkRequirement.is_assessable == True)
                .all()
            )
