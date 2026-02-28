"""LLM-assisted requirement scoring engine.

Implements the 7-phase scoring system:
  Phase 1  — Requirement element decomposition (pre-seeded from static JSON, never via LLM)
  Phase 2  — Control evaluation against elements (LLM call 1 per assessment run)
  Phase 3  — Deterministic Score 1 calculation
  Phase 4  — Expected mechanism extraction (LLM call 2)
  Phase 5  — Mechanism evaluation + explanations (LLM call 3)
  Phase 6  — Deterministic Score 2 (risk-based)
  Phase 7  — Deterministic Score 3 (peer alignment)

Produces three 0–100% scores per requirement:
  score1 — Requirement Met by Documentation
  score2 — Risk-Based Best Practice Adequacy
  score3 — Peer Alignment
"""

import json
import logging
import uuid
from datetime import datetime
from typing import Any

from openai import AsyncOpenAI
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.assessment import Assessment
from app.models.policy import Policy, PolicyMapping
from app.models.requirement_threshold import AssessmentRequirementThreshold
from app.models.scoring_job import RequirementElement, RequirementScore, ScoringJob
from app.models.unified_framework import AssessmentFrameworkScope, FrameworkRequirement

logger = logging.getLogger(__name__)

# ─── Status weight tables ─────────────────────────────────────────────────────

ELEMENT_STATUS_WEIGHTS: dict[str, float] = {
    "Fully Addressed": 1.0,
    "Fully Designed and Implemented": 1.0,
    "Fully Designed, Implemented, and Operating Effectively": 1.0,
    "Partially Addressed": 0.5,
    "Partially Implemented": 0.5,
    "Implemented but Not Operating Consistently": 0.5,
    "Designed but Not Implemented": 0.25,
    "Not Addressed": 0.0,
}

MECHANISM_STATUS_VALUES: dict[str, float] = {
    "Present and Robust": 1.0,
    "Present but Weak": 0.5,
    "Missing": 0.0,
}

RISK_WEIGHTS: dict[str, int] = {"High": 3, "Medium": 2, "Low": 1}

DEPTH_STATUS_VOCAB: dict[str, list[str]] = {
    "design": [
        "Fully Addressed",
        "Partially Addressed",
        "Not Addressed",
    ],
    "implementation": [
        "Fully Designed and Implemented",
        "Designed but Not Implemented",
        "Partially Implemented",
        "Not Addressed",
    ],
    "operating_effectiveness": [
        "Fully Designed, Implemented, and Operating Effectively",
        "Implemented but Not Operating Consistently",
        "Designed but Not Implemented",
        "Not Addressed",
    ],
}

# NIST SP 800-60 information type human-readable labels
INFORMATION_TYPE_LABELS: dict[str, str] = {
    "identity_auth": "Personal identity and authentication information",
    "info_security": "Information security and privacy protection data",
    "financial": "Financial and payment processing data",
    "health": "Health and medical records",
    "pii": "Personally identifiable information (PII)",
    "legal": "Legal and compliance records",
    "intellectual_property": "Intellectual property and proprietary data",
    "operational": "Operational and business process information",
    "infrastructure": "IT infrastructure and system configuration data",
    "research": "Research and development data",
}


def _resolve_info_type_labels(raw: str | None) -> list[str]:
    """Parse JSON information_types string and return human-readable labels."""
    if not raw:
        return []
    try:
        ids: list[str] = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return []
    return [INFORMATION_TYPE_LABELS.get(t, t) for t in ids if t]


# ─── Main engine ──────────────────────────────────────────────────────────────


class LLMScoringEngine:
    """Orchestrates per-requirement LLM scoring for a compliance assessment."""

    def __init__(self, db: Session) -> None:
        self.db = db
        self.client = AsyncOpenAI(api_key=settings.openai_api_key)
        self.model = settings.scoring_model
        self.max_output_tokens = settings.scoring_max_output_tokens

    # ─────────────────────────────────────────────────────────────────────────
    # Public API
    # ─────────────────────────────────────────────────────────────────────────

    async def run_job(self, job_id: uuid.UUID, assessment_id: uuid.UUID) -> None:
        """Execute a scoring job for all in-scope assessable requirements."""
        logger.info("Starting scoring job %s for assessment %s", job_id, assessment_id)
        job = self.db.query(ScoringJob).filter(ScoringJob.id == job_id).first()
        assessment = self.db.query(Assessment).filter(Assessment.id == assessment_id).first()
        if not job or not assessment:
            logger.error("Scoring job or assessment not found: job=%s assessment=%s", job_id, assessment_id)
            return

        requirements = self._get_assessable_requirements(assessment_id)
        logger.info("Found %d assessable requirements for job %s", len(requirements), job_id)

        job.status = "running"
        job.total_requirements = len(requirements)
        job.started_at = datetime.utcnow()
        self.db.commit()

        for req in requirements:
            try:
                qualifying_policies = self._get_qualifying_policies(req.id, assessment)
                if not qualifying_policies:
                    self._upsert_requirement_score(
                        assessment_id=assessment_id,
                        requirement_id=req.id,
                        job_id=job_id,
                        status="skipped",
                        skip_reason="missing_documentation",
                    )
                    job.completed_requirements += 1
                    self.db.commit()
                    continue

                score_data = await self._score_requirement(req, assessment, qualifying_policies)

                self._upsert_requirement_score(
                    assessment_id=assessment_id,
                    requirement_id=req.id,
                    job_id=job_id,
                    status="completed",
                    **score_data,
                )
                job.completed_requirements += 1
            except Exception as exc:
                logger.exception("Error scoring requirement %s: %s", req.id, exc)
                self._upsert_requirement_score(
                    assessment_id=assessment_id,
                    requirement_id=req.id,
                    job_id=job_id,
                    status="failed",
                    error_message=str(exc),
                )
                job.failed_requirements += 1
                job.completed_requirements += 1

            self.db.commit()

        # Mark failed only if there were requirements and ALL of them failed
        all_failed = job.total_requirements > 0 and job.failed_requirements == job.total_requirements
        job.status = "failed" if all_failed else "completed"
        job.completed_at = datetime.utcnow()
        self.db.commit()
        logger.info(
            "Scoring job %s finished: status=%s total=%d completed=%d failed=%d",
            job_id, job.status, job.total_requirements, job.completed_requirements, job.failed_requirements,
        )

    async def score_single_requirement(
        self, requirement_id: uuid.UUID, assessment_id: uuid.UUID, job_id: uuid.UUID | None = None
    ) -> dict[str, Any]:
        """Score a single requirement (used for re-run)."""
        req = self.db.query(FrameworkRequirement).filter(FrameworkRequirement.id == requirement_id).first()
        assessment = self.db.query(Assessment).filter(Assessment.id == assessment_id).first()
        if not req or not assessment:
            raise ValueError("Requirement or assessment not found")

        qualifying_policies = self._get_qualifying_policies(req.id, assessment)
        if not qualifying_policies:
            result = self._upsert_requirement_score(
                assessment_id=assessment_id,
                requirement_id=req.id,
                job_id=job_id,
                status="skipped",
                skip_reason="missing_documentation",
            )
            self.db.commit()
            return result

        score_data = await self._score_requirement(req, assessment, qualifying_policies)
        result = self._upsert_requirement_score(
            assessment_id=assessment_id,
            requirement_id=req.id,
            job_id=job_id,
            status="completed",
            **score_data,
        )
        self.db.commit()
        return result

    # ─────────────────────────────────────────────────────────────────────────
    # Internal scoring flow
    # ─────────────────────────────────────────────────────────────────────────

    async def _score_requirement(
        self,
        req: FrameworkRequirement,
        assessment: Assessment,
        qualifying_policies: list[PolicyMapping],
    ) -> dict[str, Any]:
        """Run the full 3-call LLM scoring flow for one requirement."""
        info_types = _resolve_info_type_labels(assessment.information_types)
        has_risk_profile = bool(info_types)
        has_company_profile = any([
            assessment.industry,
            assessment.business_description,
            assessment.product_service_description,
        ])

        # Build control documentation snippets (truncated, never summarised)
        control_docs = self._build_control_docs(qualifying_policies)

        # Load pre-seeded Phase 1 elements (never generated on-demand via LLM)
        elements = self._load_elements(req.id)
        if not elements:
            raise ValueError(
                f"No Phase 1 elements found for requirement {req.code!r}. "
                "Load element data for this framework before running scoring."
            )
        phase1_output = {"elements": [{"id": e.element_id, "description": e.description} for e in elements]}

        # ── Call 1: Phase 2 — element evaluation ──
        depth = assessment.depth_level or "design"
        status_vocab = DEPTH_STATUS_VOCAB.get(depth, DEPTH_STATUS_VOCAB["design"])

        phase2_prompt = self._build_phase2_prompt(req, depth, phase1_output["elements"], control_docs, status_vocab)
        phase2_output = await self._call_llm(phase2_prompt)

        element_evaluations = phase2_output.get("element_evaluations", [])

        # ── Phase 3: Deterministic Score 1 ──
        score1 = self._calculate_score1(element_evaluations)

        # Score 1 explanation always comes from Phase 2 (no risk profile needed).
        # Phase 5 will override this with a richer version when it runs.
        score1_explanation: dict | None = phase2_output.get("score1_explanation")

        # ── Call 2: Phase 4 — expected mechanisms ──
        phase4_output: dict[str, Any] = {}
        score2: float | None = None
        score3: float | None = None
        score2_explanation: dict | None = None
        score3_explanation: dict | None = None
        phase5_output: dict[str, Any] = {}

        if has_risk_profile:
            phase4_prompt = self._build_phase4_prompt(
                req, info_types, assessment, has_company_profile
            )
            phase4_output = await self._call_llm(phase4_prompt)

            # ── Call 3: Phase 5 — mechanism evaluation + explanations ──
            phase5_prompt = self._build_phase5_prompt(
                req, depth, control_docs, element_evaluations,
                phase4_output, score1, has_company_profile
            )
            phase5_output = await self._call_llm(phase5_prompt)

            risk_mechs = phase4_output.get("risk_based_mechanisms", [])
            risk_evals = phase5_output.get("risk_mechanism_evaluations", [])
            score2 = self._calculate_weighted_score(risk_mechs, risk_evals)

            if has_company_profile:
                peer_mechs = phase4_output.get("peer_based_mechanisms", [])
                peer_evals = phase5_output.get("peer_mechanism_evaluations", [])
                score3 = self._calculate_weighted_score(peer_mechs, peer_evals)

            # Phase 5 provides a more comprehensive score1_explanation (with risk context).
            # Fall back to the Phase 2 version if Phase 5 didn't return one.
            score1_explanation = phase5_output.get("score1_explanation") or score1_explanation
            score2_explanation = phase5_output.get("score2_explanation")
            score3_explanation = phase5_output.get("score3_explanation")

        return {
            "score1": score1,
            "score2": score2,
            "score3": score3,
            "phase1_output": phase1_output,
            "phase2_output": phase2_output,
            "phase4_output": phase4_output if phase4_output else None,
            "phase5_output": phase5_output if phase5_output else None,
            "score1_explanation": score1_explanation,
            "score2_explanation": score2_explanation,
            "score3_explanation": score3_explanation,
            "model_used": self.model,
            "llm_calls_used": 3 if has_risk_profile else 1,
            "scored_at": datetime.utcnow(),
        }

    def _load_elements(self, requirement_id: uuid.UUID) -> list[RequirementElement]:
        return (
            self.db.query(RequirementElement)
            .filter(RequirementElement.requirement_id == requirement_id)
            .order_by(RequirementElement.element_id)
            .all()
        )

    # ─────────────────────────────────────────────────────────────────────────
    # Phase 2 prompt builder
    # ─────────────────────────────────────────────────────────────────────────

    def _build_phase2_prompt(
        self,
        req: FrameworkRequirement,
        depth: str,
        elements: list[dict],
        control_docs: list[dict],
        status_vocab: list[str],
    ) -> dict:
        return {
            "task": (
                "Evaluate the provided control documentation against each element of the "
                "compliance requirement. For each element, select the status that best "
                "describes what the documentation demonstrates. Use ONLY the status values "
                f"listed: {status_vocab}. "
                "Then provide a concise explanation summarising the overall finding."
            ),
            "requirement": {
                "code": req.code,
                "name": req.name,
                "description": req.description or "",
            },
            "elements": elements,
            "control_documentation": control_docs,
            "output_format": {
                "element_evaluations": [
                    {
                        "id": "E1",
                        "status": f"one of: {', '.join(status_vocab)}",
                        "evidence_reference": "quote from docs or 'None found'",
                        "deficiency_summary": "what is missing or 'null' if fully addressed",
                    }
                ],
                "score1_explanation": {
                    "executive_summary": "2-3 sentences summarising overall documentation coverage of this requirement",
                    "deficiencies": [{"element_id": "E1", "issue": "description of gap"}],
                    "improvements": [{"level": "Tactical|Strategic|Long-term", "action": "recommended action"}],
                },
            },
        }

    # ─────────────────────────────────────────────────────────────────────────
    # Phase 3 — Deterministic Score 1
    # ─────────────────────────────────────────────────────────────────────────

    def _calculate_score1(self, element_evaluations: list[dict]) -> float:
        if not element_evaluations:
            return 0.0
        total = sum(
            ELEMENT_STATUS_WEIGHTS.get(e.get("status", "Not Addressed"), 0.0)
            for e in element_evaluations
        )
        return round(total / len(element_evaluations) * 100, 1)

    # ─────────────────────────────────────────────────────────────────────────
    # Phase 4 prompt builder
    # ─────────────────────────────────────────────────────────────────────────

    def _build_phase4_prompt(
        self,
        req: FrameworkRequirement,
        info_types: list[str],
        assessment: Assessment,
        include_company_profile: bool,
    ) -> dict:
        prompt: dict[str, Any] = {
            "task": (
                "Based on the requirement, risk profile, and (if provided) company profile, "
                "identify the specific security/compliance mechanisms that SHOULD be present. "
                "For risk_based_mechanisms, derive from North American industry best practices "
                "for the given information types. "
                + ("For peer_based_mechanisms, consider what organisations similar to the "
                   "described company typically implement." if include_company_profile else "")
            ),
            "requirement": {
                "code": req.code,
                "name": req.name,
                "description": req.description or "",
            },
            "risk_profile": {
                "information_types": info_types,
            },
        }

        if include_company_profile:
            prompt["company_profile"] = {
                "industry": assessment.industry or "",
                "business_description": assessment.business_description or "",
                "product_service_description": assessment.product_service_description or "",
            }

        output_format: dict[str, Any] = {
            "risk_based_mechanisms": [
                {"id": "M1", "description": "string", "criticality": "High|Medium|Low"}
            ]
        }
        if include_company_profile:
            output_format["peer_based_mechanisms"] = [
                {"id": "P1", "description": "string", "criticality": "High|Medium|Low"}
            ]
        prompt["output_format"] = output_format

        return prompt

    # ─────────────────────────────────────────────────────────────────────────
    # Phase 5 prompt builder
    # ─────────────────────────────────────────────────────────────────────────

    def _build_phase5_prompt(
        self,
        req: FrameworkRequirement,
        depth: str,
        control_docs: list[dict],
        element_evaluations: list[dict],
        phase4_output: dict,
        score1: float,
        include_peer: bool,
    ) -> dict:
        risk_mechs = phase4_output.get("risk_based_mechanisms", [])
        peer_mechs = phase4_output.get("peer_based_mechanisms", [])

        prompt: dict[str, Any] = {
            "task": (
                "Evaluate whether each expected mechanism is present in the control documentation. "
                "Then provide concise explanation summaries for each score. "
                "status for mechanisms: 'Present and Robust', 'Present but Weak', or 'Missing'."
            ),
            "requirement": {
                "code": req.code,
                "name": req.name,
                "description": req.description or "",
            },
            "depth": depth,
            "control_documentation": control_docs,
            "element_evaluations": element_evaluations,
            "risk_based_mechanisms": risk_mechs,
            "score1": score1,
        }

        if include_peer and peer_mechs:
            prompt["peer_based_mechanisms"] = peer_mechs

        mechanism_eval_schema = [
            {
                "id": "M1",
                "status": "Present and Robust|Present but Weak|Missing",
                "gap_explanation": "string or null",
                "recommendation": "string or null",
                "depth_commentary": "string or null",
            }
        ]

        explanation_schema = {
            "executive_summary": "≤3 sentences",
            "deficiencies": [{"element_id": "E1", "issue": "string"}],
            "improvements": [{"level": "string", "action": "string"}],
        }

        output_format: dict[str, Any] = {
            "risk_mechanism_evaluations": mechanism_eval_schema,
            "score1_explanation": explanation_schema,
            "score2_explanation": explanation_schema,
        }
        if include_peer and peer_mechs:
            peer_eval_schema = [{**s, "id": "P1"} for s in mechanism_eval_schema]
            output_format["peer_mechanism_evaluations"] = peer_eval_schema
            output_format["score3_explanation"] = explanation_schema

        prompt["output_format"] = output_format
        return prompt

    # ─────────────────────────────────────────────────────────────────────────
    # Phase 6+7 — Deterministic Score 2 + Score 3
    # ─────────────────────────────────────────────────────────────────────────

    def _calculate_weighted_score(
        self, mechanisms: list[dict], evaluations: list[dict]
    ) -> float | None:
        if not mechanisms or not evaluations:
            return None
        evals = {e["id"]: e for e in evaluations}
        numerator = 0.0
        denominator = 0
        for mech in mechanisms:
            mid = mech.get("id")
            crit = mech.get("criticality", "Medium")
            weight = RISK_WEIGHTS.get(crit, 2)
            eval_status = evals.get(mid, {}).get("status", "Missing")
            value = MECHANISM_STATUS_VALUES.get(eval_status, 0.0)
            numerator += value * weight
            denominator += weight
        if denominator == 0:
            return None
        return round((numerator / denominator) * 100, 1)

    # ─────────────────────────────────────────────────────────────────────────
    # Helpers
    # ─────────────────────────────────────────────────────────────────────────

    def _get_assessable_requirements(self, assessment_id: uuid.UUID) -> list[FrameworkRequirement]:
        """Get all in-scope assessable requirements for an assessment."""
        scope_rows = (
            self.db.query(AssessmentFrameworkScope)
            .filter(AssessmentFrameworkScope.assessment_id == assessment_id)
            .all()
        )
        if not scope_rows:
            return []

        all_requirements: list[FrameworkRequirement] = []
        for scope in scope_rows:
            query = (
                self.db.query(FrameworkRequirement)
                .filter(
                    FrameworkRequirement.framework_id == scope.framework_id,
                    FrameworkRequirement.is_assessable == True,  # noqa: E712
                )
            )
            reqs = query.all()

            if not scope.include_all:
                included = set(str(i) for i in (scope.included_requirement_ids or []))
                reqs = [r for r in reqs if str(r.id) in included]
            else:
                excluded = set(str(i) for i in (scope.excluded_requirement_ids or []))
                reqs = [r for r in reqs if str(r.id) not in excluded]

            all_requirements.extend(reqs)

        return all_requirements

    def _get_qualifying_policies(
        self, requirement_id: uuid.UUID, assessment: Assessment
    ) -> list[PolicyMapping]:
        """Get policy mappings that qualify as control documentation for scoring.

        A mapping qualifies if:
        - is_approved = True
        - is_rejected = False
        - relevance_percentage >= threshold (per-req override → assessment default → 80)
        - The linked policy has content_text
        """
        # Look up per-requirement threshold override
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

        # Fetch all non-rejected mappings for this requirement in this assessment.
        # Approval status is not required — any non-rejected, above-threshold mapping counts.
        mappings = (
            self.db.query(PolicyMapping)
            .join(Policy, PolicyMapping.policy_id == Policy.id)
            .filter(
                Policy.assessment_id == assessment.id,
                PolicyMapping.requirement_id == requirement_id,
                PolicyMapping.is_rejected == False,  # noqa: E712
            )
            .all()
        )

        qualifying = [
            m for m in mappings
            if (m.relevance_percentage is not None and m.relevance_percentage >= threshold)
            and m.policy
            and m.policy.content_text
        ]

        return qualifying

    def _build_control_docs(self, qualifying_policies: list[PolicyMapping]) -> list[dict]:
        """Build truncated control documentation snippets from qualifying policies.

        Takes the first scoring_max_doc_chars characters of each policy.
        Multiple mappings to the same policy are deduplicated.
        """
        seen_policy_ids: set[uuid.UUID] = set()
        docs: list[dict] = []
        for mapping in qualifying_policies:
            if not mapping.policy or mapping.policy_id in seen_policy_ids:
                continue
            seen_policy_ids.add(mapping.policy_id)
            docs.append({
                "policy_name": mapping.policy.name,
                "content": mapping.policy.content_text or "",
            })
        return docs

    def _upsert_requirement_score(
        self,
        assessment_id: uuid.UUID,
        requirement_id: uuid.UUID,
        job_id: uuid.UUID | None,
        status: str,
        skip_reason: str | None = None,
        error_message: str | None = None,
        score1: float | None = None,
        score2: float | None = None,
        score3: float | None = None,
        phase1_output: dict | None = None,
        phase2_output: dict | None = None,
        phase4_output: dict | None = None,
        phase5_output: dict | None = None,
        score1_explanation: dict | None = None,
        score2_explanation: dict | None = None,
        score3_explanation: dict | None = None,
        model_used: str | None = None,
        llm_calls_used: int | None = None,
        scored_at: datetime | None = None,
    ) -> dict:
        existing = (
            self.db.query(RequirementScore)
            .filter(
                RequirementScore.assessment_id == assessment_id,
                RequirementScore.requirement_id == requirement_id,
            )
            .first()
        )

        if existing:
            row = existing
        else:
            row = RequirementScore(
                id=uuid.uuid4(),
                assessment_id=assessment_id,
                requirement_id=requirement_id,
            )
            self.db.add(row)

        row.scoring_job_id = job_id
        row.status = status
        row.skip_reason = skip_reason
        row.error_message = error_message
        row.score1 = score1
        row.score2 = score2
        row.score3 = score3
        row.phase1_output = phase1_output
        row.phase2_output = phase2_output
        row.phase4_output = phase4_output
        row.phase5_output = phase5_output
        row.score1_explanation = score1_explanation
        row.score2_explanation = score2_explanation
        row.score3_explanation = score3_explanation
        row.model_used = model_used or self.model
        row.llm_calls_used = llm_calls_used
        row.scored_at = scored_at or (datetime.utcnow() if status == "completed" else None)

        return {
            "id": str(row.id),
            "assessment_id": str(assessment_id),
            "requirement_id": str(requirement_id),
            "status": status,
            "skip_reason": skip_reason,
            "score1": score1,
            "score2": score2,
            "score3": score3,
        }

    async def _call_llm(self, prompt: dict) -> dict:
        """Make a single structured JSON LLM call."""
        system_msg = (
            "You are a compliance assessment expert. "
            "Respond ONLY with valid JSON matching the output_format structure provided. "
            "Do not include any explanation outside the JSON."
        )
        user_msg = json.dumps(prompt, ensure_ascii=False)

        response = await self.client.chat.completions.create(
            model=self.model,
            temperature=0,
            max_tokens=self.max_output_tokens,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": system_msg},
                {"role": "user", "content": user_msg},
            ],
        )

        content = response.choices[0].message.content or "{}"
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            logger.warning("LLM returned non-JSON content: %s", content[:200])
            return {}
