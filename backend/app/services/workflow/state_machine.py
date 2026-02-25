"""Assessment workflow state machine."""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from app.models.assessment import Assessment, AssessmentStatus
from app.services.audit.audit_service import AuditService


# Valid state transitions
VALID_TRANSITIONS = {
    AssessmentStatus.DRAFT.value: [
        AssessmentStatus.IN_PROGRESS.value,
        AssessmentStatus.ARCHIVED.value,
    ],
    AssessmentStatus.IN_PROGRESS.value: [
        AssessmentStatus.REVIEW.value,
        AssessmentStatus.DRAFT.value,
        AssessmentStatus.ARCHIVED.value,
    ],
    AssessmentStatus.REVIEW.value: [
        AssessmentStatus.COMPLETED.value,
        AssessmentStatus.IN_PROGRESS.value,
        AssessmentStatus.ARCHIVED.value,
    ],
    AssessmentStatus.COMPLETED.value: [
        AssessmentStatus.ARCHIVED.value,
        AssessmentStatus.IN_PROGRESS.value,  # Reopen for updates
    ],
    AssessmentStatus.ARCHIVED.value: [
        AssessmentStatus.DRAFT.value,  # Restore
    ],
}

# Transition requirements
TRANSITION_REQUIREMENTS = {
    (AssessmentStatus.IN_PROGRESS.value, AssessmentStatus.REVIEW.value): [
        "has_policies",
        "has_mappings",
    ],
    (AssessmentStatus.REVIEW.value, AssessmentStatus.COMPLETED.value): [
        "has_scores",
        "has_approved_mappings",
    ],
}


class AssessmentStateMachine:
    """State machine for assessment workflow transitions."""

    def __init__(self, db: Session):
        self.db = db
        self.audit_service = AuditService(db)

    def can_transition(
        self,
        assessment: Assessment,
        new_status: str,
    ) -> tuple[bool, str | None]:
        """
        Check if a transition is allowed.

        Returns:
            Tuple of (is_allowed, error_message)
        """
        current_status = assessment.status

        # Check if transition is valid
        valid_next = VALID_TRANSITIONS.get(current_status, [])
        if new_status not in valid_next:
            return False, f"Cannot transition from {current_status} to {new_status}"

        # Check requirements for specific transitions
        requirements = TRANSITION_REQUIREMENTS.get((current_status, new_status), [])

        for req in requirements:
            is_met, error = self._check_requirement(assessment, req)
            if not is_met:
                return False, error

        return True, None

    def transition(
        self,
        assessment_id: uuid.UUID,
        new_status: str,
        user_id: uuid.UUID | None = None,
    ) -> dict[str, Any]:
        """
        Transition an assessment to a new status.

        Returns:
            Result dict with success status and details
        """
        assessment = self.db.query(Assessment).filter(
            Assessment.id == assessment_id
        ).first()

        if not assessment:
            return {"success": False, "error": "Assessment not found"}

        # Validate transition
        can_do, error = self.can_transition(assessment, new_status)
        if not can_do:
            return {"success": False, "error": error}

        old_status = assessment.status

        # Perform transition
        assessment.status = new_status
        assessment.updated_at = datetime.utcnow()

        # Audit log
        self.audit_service.log_state_change(
            entity_type="assessment",
            entity_id=assessment_id,
            old_state=old_status,
            new_state=new_status,
            user_id=user_id,
        )

        self.db.commit()

        return {
            "success": True,
            "assessment_id": assessment_id,
            "old_status": old_status,
            "new_status": new_status,
        }

    def _check_requirement(
        self,
        assessment: Assessment,
        requirement: str,
    ) -> tuple[bool, str | None]:
        """Check a specific requirement for transition."""
        from app.models.policy import Policy, PolicyMapping
        from app.models.score import FunctionScore

        if requirement == "has_policies":
            policies = self.db.query(Policy).filter(
                Policy.assessment_id == assessment.id
            ).count()

            if policies == 0:
                return False, "Assessment must have at least one policy"

            return True, None

        elif requirement == "has_mappings":
            policy_mappings = (
                self.db.query(PolicyMapping)
                .join(Policy)
                .filter(Policy.assessment_id == assessment.id)
                .count()
            )

            if policy_mappings == 0:
                return False, "Assessment must have at least one mapping"

            return True, None

        elif requirement == "has_scores":
            scores = self.db.query(FunctionScore).filter(
                FunctionScore.assessment_id == assessment.id
            ).count()

            if scores == 0:
                return False, "Assessment must have calculated scores"

            return True, None

        elif requirement == "has_approved_mappings":
            approved_policy = (
                self.db.query(PolicyMapping)
                .join(Policy)
                .filter(
                    Policy.assessment_id == assessment.id,
                    PolicyMapping.is_approved == True,
                )
                .count()
            )

            if approved_policy == 0:
                return False, "Assessment must have at least one approved mapping"

            return True, None

        return True, None

    def get_available_transitions(
        self,
        assessment: Assessment,
    ) -> list[dict[str, Any]]:
        """Get list of available transitions for an assessment."""
        current_status = assessment.status
        valid_next = VALID_TRANSITIONS.get(current_status, [])

        transitions = []
        for next_status in valid_next:
            can_do, error = self.can_transition(assessment, next_status)
            transitions.append({
                "status": next_status,
                "allowed": can_do,
                "blocked_reason": error if not can_do else None,
            })

        return transitions
