"""Scoring rubric aligned with NIST maturity tiers."""

from enum import IntEnum
from typing import Any


class MaturityTier(IntEnum):
    """NIST-aligned maturity tiers (0-4)."""
    NON_EXISTENT = 0  # No policy, no evidence
    PARTIAL = 1  # Ad hoc, informal, no documentation
    RISK_INFORMED = 2  # Policy exists, inconsistent execution
    REPEATABLE = 3  # Policy documented, consistent execution
    ADAPTIVE = 4  # All of 3 + metrics, continuous improvement


class ScoringRubric:
    """Rubric for determining maturity scores based on evidence."""

    # Criteria for each score level
    CRITERIA = {
        0: {
            "name": "Non-existent",
            "tier": "Tier 0",
            "description": "No policy, no evidence of implementation",
            "requirements": {
                "has_policy": False,
                "has_documentation": False,
                "has_operation": False,
            },
        },
        1: {
            "name": "Partial",
            "tier": "Tier 1",
            "description": "Ad hoc implementation, informal processes, no documentation",
            "requirements": {
                "has_policy": False,
                "has_documentation": False,
                "has_operation": "partial",
            },
        },
        2: {
            "name": "Risk-Informed",
            "tier": "Tier 2",
            "description": "Policy exists, but implementation is inconsistent",
            "requirements": {
                "has_policy": True,
                "has_documentation": "partial",
                "has_operation": "partial",
            },
        },
        3: {
            "name": "Repeatable",
            "tier": "Tier 3",
            "description": "Policy exists, documented, consistent execution",
            "requirements": {
                "has_policy": True,
                "has_documentation": True,
                "has_operation": True,
            },
        },
        4: {
            "name": "Adaptive",
            "tier": "Tier 4",
            "description": "All Tier 3 requirements plus metrics and continuous improvement",
            "requirements": {
                "has_policy": True,
                "has_documentation": True,
                "has_operation": True,
                "has_metrics": True,
                "has_improvement": True,
            },
        },
    }

    def calculate_score(
        self,
        evidence: dict[str, Any],
        depth_level: str | None = None,
    ) -> tuple[int, dict]:
        """
        Calculate a maturity score based on evidence.

        Args:
            evidence: Dictionary containing:
                - has_policy: bool
                - has_documentation: bool or "partial"
                - has_operation: bool or "partial"
                - has_metrics: bool (optional)
                - has_improvement: bool (optional)
                - interview_responses: list[dict] (optional)
            depth_level: Assessment depth ("design" or "implementation").
                Design-only assessments don't penalize for missing operation evidence.

        Returns:
            Tuple of (score, score_breakdown)
        """
        has_policy = evidence.get("has_policy", False)
        has_documentation = evidence.get("has_documentation", False)
        has_operation = evidence.get("has_operation", False)
        has_metrics = evidence.get("has_metrics", False)
        has_improvement = evidence.get("has_improvement", False)

        # For design-only assessments, assume operation is satisfied if
        # policy is in place (don't penalize for missing operational evidence)
        if depth_level == "design" and not has_operation:
            if has_policy:
                has_operation = True

        breakdown = {
            "has_policy": has_policy,
            "has_documentation": has_documentation,
            "has_operation": has_operation,
            "has_metrics": has_metrics,
            "has_improvement": has_improvement,
        }

        # Score determination logic
        if not has_policy:
            # Check if there's any evidence at all
            if has_operation == "partial" or has_documentation == "partial":
                score = MaturityTier.PARTIAL
            else:
                score = MaturityTier.NON_EXISTENT
        elif has_policy and has_documentation and has_operation:
            # At least Tier 3
            if has_metrics and has_improvement:
                score = MaturityTier.ADAPTIVE
            else:
                score = MaturityTier.REPEATABLE
        elif has_policy:
            # Tier 2 - policy exists but not fully documented/operational
            score = MaturityTier.RISK_INFORMED
        else:
            score = MaturityTier.PARTIAL

        breakdown["score"] = int(score)
        breakdown["tier_name"] = self.CRITERIA[int(score)]["name"]
        breakdown["tier_description"] = self.CRITERIA[int(score)]["description"]

        return int(score), breakdown

    def get_tier_info(self, score: int) -> dict[str, Any]:
        """Get information about a maturity tier."""
        score = max(0, min(4, score))
        return self.CRITERIA[score]

    def score_from_interview_responses(
        self,
        responses: list[dict],
    ) -> dict[str, Any]:
        """
        Derive scoring evidence from interview responses.

        Args:
            responses: List of response dicts with question_type and response_value

        Returns:
            Evidence dict suitable for calculate_score
        """
        evidence = {
            "has_policy": False,
            "has_documentation": False,
            "has_operation": False,
            "has_metrics": False,
            "has_improvement": False,
        }

        for resp in responses:
            q_type = resp.get("question_type", "")
            value = resp.get("response_value", "").lower()

            is_positive = value in ["yes", "true", "1", "partial"]
            is_strong_positive = value in ["yes", "true", "1"]

            if q_type == "existence":
                # Existence questions indicate presence of policy
                if is_positive:
                    evidence["has_policy"] = True

            elif q_type == "documentation":
                if is_strong_positive:
                    evidence["has_documentation"] = True
                elif is_positive:
                    evidence["has_documentation"] = "partial"

            elif q_type == "operation":
                if is_strong_positive:
                    evidence["has_operation"] = True
                elif is_positive:
                    evidence["has_operation"] = "partial"

            elif q_type == "design":
                # Design questions can indicate policy quality
                pass  # Captured in the overall assessment

        return evidence
