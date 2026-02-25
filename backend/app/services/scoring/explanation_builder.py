"""Service for building explanation payloads for scores."""

from typing import Any
import uuid


class ExplanationBuilder:
    """Builder for creating transparent score explanations."""

    def build_subcategory_explanation(
        self,
        subcategory_code: str,
        score: int,
        score_breakdown: dict[str, Any],
        policy_evidence: list[dict] | None = None,
        interview_evidence: list[dict] | None = None,
    ) -> dict[str, Any]:
        """
        Build an explanation payload for a subcategory score.

        Args:
            subcategory_code: The CSF subcategory code
            score: The calculated score (0-4)
            score_breakdown: Breakdown from the rubric
            policy_evidence: List of policy mappings that contributed
            interview_evidence: List of interview responses that contributed

        Returns:
            Explanation payload dict
        """
        components = []

        # Policy component
        if policy_evidence:
            components.append({
                "type": "policy",
                "description": f"Found {len(policy_evidence)} mapped policy/policies",
                "items": [
                    {"name": p.get("name"), "confidence": p.get("confidence_score")}
                    for p in policy_evidence
                ],
            })
        else:
            components.append({
                "type": "policy",
                "description": "No policies mapped to this subcategory",
                "items": [],
            })

        # Interview component
        if interview_evidence:
            positive_responses = [
                r for r in interview_evidence
                if r.get("response_value", "").lower() in ["yes", "true", "1"]
            ]
            components.append({
                "type": "interview",
                "description": f"{len(positive_responses)}/{len(interview_evidence)} positive interview responses",
                "items": [
                    {
                        "question_type": r.get("question_type"),
                        "response": r.get("response_value"),
                        "quote": r.get("response_text", "")[:200] if r.get("response_text") else None,
                    }
                    for r in interview_evidence
                ],
            })

        # Build rationale
        rationale_parts = []

        if score == 0:
            rationale_parts.append("No evidence of policy implementation found.")
        elif score == 1:
            rationale_parts.append("Ad hoc or informal implementation detected.")
        elif score == 2:
            rationale_parts.append("Partial implementation with inconsistent execution.")
        elif score == 3:
            rationale_parts.append("Policy exists with documented, consistent execution.")
        elif score == 4:
            rationale_parts.append("Mature implementation with metrics and continuous improvement processes.")

        # Add tier info
        rationale_parts.append(f"Tier: {score_breakdown.get('tier_name', 'Unknown')}")

        # Build evidence citations
        evidence_citations = []

        if policy_evidence:
            for p in policy_evidence:
                evidence_citations.append({
                    "type": "policy",
                    "name": p.get("name"),
                    "id": str(p.get("id")) if p.get("id") else None,
                })

        if interview_evidence:
            for r in interview_evidence:
                if r.get("response_text"):
                    evidence_citations.append({
                        "type": "interview",
                        "quote": r.get("response_text", "")[:200],
                        "question_type": r.get("question_type"),
                    })

        return {
            "components": components,
            "rationale": " ".join(rationale_parts),
            "evidence_citations": evidence_citations,
            "confidence_factors": {
                "policy_coverage": 1.0 if policy_evidence else 0.0,
                "interview_coverage": len(interview_evidence or []) / 3.0 if interview_evidence else 0.0,
            },
            "score_breakdown": score_breakdown,
        }

    def build_category_explanation(
        self,
        category_code: str,
        score: float,
        subcategory_scores: list[dict],
    ) -> dict[str, Any]:
        """Build an explanation for a category score (aggregated from subcategories)."""
        components = [
            {
                "type": "subcategory",
                "code": s.get("code"),
                "score": s.get("score"),
                "tier": s.get("tier_name"),
            }
            for s in subcategory_scores
        ]

        low_scores = [s for s in subcategory_scores if s.get("score", 0) <= 1]
        high_scores = [s for s in subcategory_scores if s.get("score", 0) >= 3]

        rationale_parts = [
            f"Category score calculated as average of {len(subcategory_scores)} subcategory scores.",
        ]

        if low_scores:
            rationale_parts.append(
                f"Areas needing attention: {', '.join(s.get('code', '') for s in low_scores)}"
            )

        if high_scores:
            rationale_parts.append(
                f"Strong areas: {', '.join(s.get('code', '') for s in high_scores)}"
            )

        return {
            "components": components,
            "rationale": " ".join(rationale_parts),
            "evidence_citations": None,
            "confidence_factors": {
                "subcategory_coverage": len(subcategory_scores) / max(1, len(subcategory_scores)),
            },
        }

    def build_function_explanation(
        self,
        function_code: str,
        score: float,
        category_scores: list[dict],
    ) -> dict[str, Any]:
        """Build an explanation for a function score (aggregated from categories)."""
        components = [
            {
                "type": "category",
                "code": c.get("code"),
                "name": c.get("name"),
                "score": c.get("score"),
            }
            for c in category_scores
        ]

        rationale_parts = [
            f"Function score calculated as average of {len(category_scores)} category scores.",
        ]

        return {
            "components": components,
            "rationale": " ".join(rationale_parts),
            "evidence_citations": None,
            "confidence_factors": {
                "category_coverage": 1.0,
            },
        }
