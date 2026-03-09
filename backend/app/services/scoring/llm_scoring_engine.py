"""LLM-assisted requirement scoring engine.

Implements the scoring system:
  Policy Extraction  — User-triggered pre-scoring stage (PolicyExtractionService)
  Phase 2  — Documentation Score: single LLM call evaluating policy statements
             (+ evidence at implementation depth) → Covered / Partial / Gap
  Phase 3  — Deterministic Score 1: Covered=100, Partial=50, Gap=0
  Phase 4  — Expected mechanism extraction (LLM call, risk profile required)
  Phase 5  — Mechanism evaluation + explanations (LLM call)
  Phase 6  — Deterministic Score 2 (risk-based)
  Phase 7  — Deterministic Score 3 (peer alignment)

Produces per requirement:
  score1 — Documentation Coverage (0 / 50 / 100)
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
from app.models.policy_statement import PolicyStatement
from app.services.ingestion.spreadsheet_ingestion import SpreadsheetIngestionService
from app.models.requirement_threshold import AssessmentRequirementThreshold
from app.models.scoring_job import RequirementScore, ScoringJob
from app.models.unified_framework import AssessmentFrameworkScope, FrameworkRequirement

logger = logging.getLogger(__name__)

# ─── Score tables ─────────────────────────────────────────────────────────────

COVERAGE_LABEL_SCORES: dict[str, float] = {
    "Covered": 100.0,
    "Partial": 50.0,
    "Gap": 0.0,
}

MECHANISM_STATUS_VALUES: dict[str, float] = {
    "Present and Robust": 1.0,
    "Present but Weak": 0.5,
    "Missing": 0.0,
}

RISK_WEIGHTS: dict[str, int] = {"High": 3, "Medium": 2, "Low": 1}

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
                await self._score_and_save_requirement(req, assessment, job_id)
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

        result = await self._score_and_save_requirement(req, assessment, job_id)
        self.db.commit()
        return result

    # ─────────────────────────────────────────────────────────────────────────
    # Internal scoring flow
    # ─────────────────────────────────────────────────────────────────────────

    async def _score_and_save_requirement(
        self,
        req: FrameworkRequirement,
        assessment: Assessment,
        job_id: uuid.UUID | None,
    ) -> dict[str, Any]:
        depth = assessment.depth_level or "design"
        assessment_id = assessment.id

        policy_statements = self._get_policy_statements(req.id, assessment_id)
        evidence_docs = (
            self._get_qualifying_docs(req.id, assessment, "evidence")
            if depth == "implementation"
            else []
        )

        # Skip logic
        if depth == "design" and not policy_statements:
            return self._upsert_requirement_score(
                assessment_id=assessment_id,
                requirement_id=req.id,
                job_id=job_id,
                status="skipped",
                skip_reason="no_policy_statements",
            )

        if depth == "implementation" and not policy_statements and not evidence_docs:
            return self._upsert_requirement_score(
                assessment_id=assessment_id,
                requirement_id=req.id,
                job_id=job_id,
                status="skipped",
                skip_reason="no_documentation",
            )

        score_data = await self._score_requirement(req, assessment, policy_statements, evidence_docs)
        return self._upsert_requirement_score(
            assessment_id=assessment_id,
            requirement_id=req.id,
            job_id=job_id,
            status="completed",
            **score_data,
        )

    async def _score_requirement(
        self,
        req: FrameworkRequirement,
        assessment: Assessment,
        policy_statements: list[PolicyStatement],
        evidence_docs: list[PolicyMapping],
    ) -> dict[str, Any]:
        """Run the full scoring flow for one requirement."""
        depth = assessment.depth_level or "design"
        info_types = _resolve_info_type_labels(assessment.information_types)
        has_risk_profile = bool(info_types)
        has_company_profile = any([
            assessment.industry,
            assessment.business_description,
            assessment.product_service_description,
        ])

        impl_examples = self._get_implementation_examples(req)

        # ── Phase 2 — Documentation Score ──────────────────────────────────
        built_evidence = self._build_control_docs(evidence_docs, "evidence") if evidence_docs else []
        doc_prompt = self._build_documentation_prompt(
            req, policy_statements, built_evidence, impl_examples, depth
        )
        phase2_output = await self._call_llm(doc_prompt)

        coverage_label = phase2_output.get("coverage_label", "Gap")
        if coverage_label not in COVERAGE_LABEL_SCORES:
            coverage_label = "Gap"

        score1 = COVERAGE_LABEL_SCORES[coverage_label]

        # Build per-statement evaluations — always included so UI can expand and inspect
        stmt_evals_by_id: dict[str, dict] = {
            e["id"]: e
            for e in phase2_output.get("policy_statement_evaluations", [])
            if isinstance(e, dict) and e.get("id")
        }
        stmt_eval_list = []
        for i, stmt in enumerate(policy_statements):
            sid = f"S{i + 1}"
            eval_entry = stmt_evals_by_id.get(sid, {})
            supporting = eval_entry.get("supporting_evidence", []) if depth == "implementation" else []
            if not isinstance(supporting, list):
                supporting = []
            stmt_eval_list.append({
                "statement_id": sid,
                "statement": stmt.statement,
                "document_title": stmt.document_title,
                **({"document_section": stmt.document_section} if stmt.document_section else {}),
                "has_evidence": bool(supporting),
                "supporting_evidence": supporting,
            })

        score1_explanation = {
            "coverage_label": coverage_label,
            "explanation": phase2_output.get("explanation", ""),
            "recommendations": phase2_output.get("recommendations", []),
        }
        if stmt_eval_list:
            score1_explanation["policy_statement_evaluations"] = stmt_eval_list

        # ── Compliance picture for Phase 4/5 ───────────────────────────────
        compliance_picture = self._build_compliance_picture(
            policy_statements, phase2_output, depth
        )

        # ── Phase 4/5 (Score 2/3) ──────────────────────────────────────────
        phase4_output: dict[str, Any] = {}
        score2: float | None = None
        score3: float | None = None
        score2_explanation: dict | None = None
        score3_explanation: dict | None = None
        phase5_output: dict[str, Any] = {}

        if has_risk_profile:
            phase4_prompt = self._build_phase4_prompt(req, info_types, assessment, has_company_profile)
            phase4_output = await self._call_llm(phase4_prompt)

            phase5_prompt = self._build_phase5_prompt(
                req, depth, compliance_picture,
                phase4_output, score1, has_company_profile,
            )
            phase5_output = await self._call_llm(phase5_prompt)

            risk_mechs = phase4_output.get("risk_based_mechanisms", [])
            risk_evals = phase5_output.get("risk_mechanism_evaluations", [])
            score2 = self._calculate_weighted_score(risk_mechs, risk_evals)

            if has_company_profile:
                peer_mechs = phase4_output.get("peer_based_mechanisms", [])
                peer_evals = phase5_output.get("peer_mechanism_evaluations", [])
                score3 = self._calculate_weighted_score(peer_mechs, peer_evals)

            score2_explanation = phase5_output.get("score2_explanation")
            score3_explanation = phase5_output.get("score3_explanation")

        llm_calls = 1  # Phase 2
        if has_risk_profile:
            llm_calls += 2  # Phase 4 + 5

        return {
            "score1": score1,
            "score2": score2,
            "score3": score3,
            "phase2_output": phase2_output if phase2_output else None,
            "phase4_output": phase4_output if phase4_output else None,
            "phase5_output": phase5_output if phase5_output else None,
            "score1_explanation": score1_explanation,
            "score2_explanation": score2_explanation,
            "score3_explanation": score3_explanation,
            "model_used": self.model,
            "llm_calls_used": llm_calls,
            "scored_at": datetime.utcnow(),
        }

    # ─────────────────────────────────────────────────────────────────────────
    # Phase 2 — Documentation Score prompt builder
    # ─────────────────────────────────────────────────────────────────────────

    def _build_documentation_prompt(
        self,
        req: FrameworkRequirement,
        policy_statements: list[PolicyStatement],
        evidence_docs: list[dict],
        impl_examples: list[str],
        depth: str,
    ) -> dict:
        has_statements = bool(policy_statements)
        has_evidence = bool(evidence_docs)
        is_implementation = depth == "implementation"

        requirement_block = {
            "code": req.code,
            "name": req.name,
            "description": req.description or "",
        }

        # Build statement list with sequential IDs for the LLM to reference back
        statement_list = [
            {
                "id": f"S{i + 1}",
                "statement": s.statement,
                "document_title": s.document_title,
                **({"document_section": s.document_section} if s.document_section else {}),
            }
            for i, s in enumerate(policy_statements)
        ]

        # ── Design depth ──────────────────────────────────────────────────
        if not is_implementation:
            task = (
                "Evaluate the provided policy statements against the compliance requirement. "
                "Determine whether the policy statements collectively and adequately cover "
                "the requirement, then assign a coverage label using the rubric provided. "
                "Give a specific explanation referencing the actual policy statements and "
                "any gaps you identify. Provide concrete recommendations for improvement."
            )
            rubric = {
                "Covered": (
                    "The policy statements collectively and completely address all aspects "
                    "of the requirement with sufficient specificity and clarity."
                ),
                "Partial": (
                    "The policy statements address the requirement but are incomplete, vague, "
                    "or only partially cover it — some aspects of the requirement are missing "
                    "or inadequately addressed."
                ),
                "Gap": (
                    "The policy statements do not meaningfully address the requirement, "
                    "are entirely absent, or are so generic as to provide no real coverage."
                ),
            }
            output_format: dict[str, Any] = {
                "coverage_label": "Covered|Partial|Gap",
                "explanation": (
                    "Specific explanation of why this label was chosen, identifying exactly "
                    "which aspects of the requirement are covered or missing."
                ),
                "recommendations": [
                    {"type": "Policy", "action": "Specific policy improvement action"}
                ],
            }
            prompt: dict[str, Any] = {
                "task": task,
                "requirement": requirement_block,
                "policy_statements": statement_list,
                "rubric": rubric,
                "output_format": output_format,
            }
            if impl_examples:
                prompt["implementation_examples"] = impl_examples

            return prompt

        # ── Implementation depth — with statements ────────────────────────
        if has_statements:
            task = (
                "Evaluate the provided policy statements and implementation evidence against "
                "the compliance requirement. "
                "For each policy statement, identify which evidence documents (if any) "
                "support it — provide the document title and a specific explanation of what "
                "the evidence demonstrates for that statement. Leave supporting_evidence empty "
                "if no evidence confirms that statement. "
                "Evidence can support a policy statement in two ways: it can SHOW the policy "
                "in action (e.g. a log, screenshot, or configuration export demonstrating the "
                "control operating), OR it can TELL that the policy is in action (e.g. an "
                "audit report, attestation, or internal review stating that the practice is "
                "followed). Both forms count as supporting evidence. "
                "Then assign an overall coverage label using the rubric and provide a specific "
                "explanation and concrete recommendations."
            )
            if evidence_docs:
                available_evidence_titles = [d["document_name"] for d in evidence_docs]
                task += (
                    " For document_title in supporting_evidence, use ONLY titles from the "
                    "evidence documents provided, copied exactly character-for-character. "
                    "Policy documents (the source of the policy statements) are NOT valid "
                    "evidence references — only the separately provided evidence_documentation "
                    "files may appear as supporting_evidence document_title values."
                )
            rubric = {
                "Covered": (
                    "The policy statements completely address all aspects of the requirement "
                    "AND every policy statement has at least one piece of supporting evidence "
                    "confirming it is actively implemented."
                ),
                "Partial": (
                    "The policy statements partially cover the requirement and/or one or more "
                    "statements lack supporting evidence confirming active implementation."
                ),
                "Gap": (
                    "No policy statements address the requirement and no evidence documents "
                    "cover it, OR the documentation and evidence together are entirely "
                    "insufficient to demonstrate compliance."
                ),
            }
            stmt_eval_schema = [
                {
                    "id": "S1",
                    "supporting_evidence": [
                        {
                            "document_title": "exact evidence document title",
                            "explanation": "what this evidence demonstrates for this statement",
                        }
                    ],
                }
            ]
            output_format = {
                "policy_statement_evaluations": stmt_eval_schema,
                "coverage_label": "Covered|Partial|Gap",
                "explanation": (
                    "Specific explanation identifying which statements are backed by evidence "
                    "and which are not, and any other coverage gaps."
                ),
                "recommendations": [
                    {"type": "Policy|Evidence", "action": "Specific improvement action"}
                ],
            }
            prompt = {
                "task": task,
                "requirement": requirement_block,
                "policy_statements": statement_list,
                "rubric": rubric,
                "output_format": output_format,
            }
            if impl_examples:
                prompt["implementation_examples"] = impl_examples
            if evidence_docs:
                prompt["available_evidence_titles"] = available_evidence_titles
                prompt["evidence_documentation"] = evidence_docs

            return prompt

        # ── Implementation depth — no statements, evidence only ───────────
        task = (
            "No policy statements have been extracted for this requirement. "
            "Evaluate the available implementation evidence against the compliance requirement "
            "to determine how much of the requirement is addressed by evidence alone. "
            "Note in your explanation that policy documentation is missing and that this "
            "represents a gap regardless of evidence quality. "
            "Provide an overall coverage label and specific recommendations for both "
            "policy documentation and evidence."
        )
        rubric = {
            "Covered": (
                "Not achievable without policy statements — cannot be Covered when policy "
                "documentation is missing."
            ),
            "Partial": (
                "Implementation evidence addresses the requirement to some meaningful degree, "
                "but policy documentation is absent."
            ),
            "Gap": (
                "No evidence documents address the requirement, or the evidence is entirely "
                "insufficient — and policy documentation is also missing."
            ),
        }
        output_format = {
            "coverage_label": "Covered|Partial|Gap",
            "explanation": (
                "Specific explanation of what evidence was found and what is missing. "
                "Note that policy documentation is absent."
            ),
            "recommendations": [
                {"type": "Policy|Evidence", "action": "Specific improvement action"}
            ],
        }
        prompt = {
            "task": task,
            "requirement": requirement_block,
            "rubric": rubric,
            "output_format": output_format,
        }
        if impl_examples:
            prompt["implementation_examples"] = impl_examples
        if evidence_docs:
            prompt["evidence_documentation"] = evidence_docs

        return prompt

    # ─────────────────────────────────────────────────────────────────────────
    # Compliance picture for Phase 4/5
    # ─────────────────────────────────────────────────────────────────────────

    def _build_compliance_picture(
        self,
        policy_statements: list[PolicyStatement],
        phase2_output: dict,
        depth: str,
    ) -> dict:
        """Build structured compliance context for Phase 4/5 (Score 2/3).

        Contains only objective factual information — no coverage label,
        no subjective scores.
        """
        stmt_evals_by_id: dict[str, dict] = {
            e["id"]: e
            for e in phase2_output.get("policy_statement_evaluations", [])
        }

        statements_out = []
        for i, stmt in enumerate(policy_statements):
            sid = f"S{i + 1}"
            eval_entry = stmt_evals_by_id.get(sid, {})
            entry: dict[str, Any] = {
                "statement": stmt.statement,
                "document_title": stmt.document_title,
            }
            if depth == "implementation":
                supporting = eval_entry.get("supporting_evidence", [])
                entry["supporting_evidence"] = supporting
                entry["evidence_supported"] = bool(supporting)
            statements_out.append(entry)

        picture: dict[str, Any] = {"policy_statements": statements_out}

        explanation = phase2_output.get("explanation", "")
        if explanation:
            picture["coverage_summary"] = explanation

        return picture

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
            "risk_profile": {"information_types": info_types},
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
        compliance_picture: dict,
        phase4_output: dict,
        score1: float,
        include_peer: bool,
    ) -> dict:
        risk_mechs = phase4_output.get("risk_based_mechanisms", [])
        peer_mechs = phase4_output.get("peer_based_mechanisms", [])

        prompt: dict[str, Any] = {
            "task": (
                "Evaluate whether each expected mechanism is present based on the company's "
                "compliance picture (policy statements and their supporting evidence). "
                "Then provide concise explanation summaries for each score. "
                "Status for mechanisms: 'Present and Robust', 'Present but Weak', or 'Missing'."
            ),
            "requirement": {
                "code": req.code,
                "name": req.name,
                "description": req.description or "",
            },
            "depth": depth,
            "company_compliance_picture": compliance_picture,
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

    def _get_policy_statements(
        self, requirement_id: uuid.UUID, assessment_id: uuid.UUID
    ) -> list[PolicyStatement]:
        """Fetch all saved policy statements for this requirement (user-curated set)."""
        return (
            self.db.query(PolicyStatement)
            .filter(
                PolicyStatement.assessment_id == assessment_id,
                PolicyStatement.requirement_id == requirement_id,
            )
            .order_by(PolicyStatement.created_at)
            .all()
        )

    def _get_qualifying_docs(
        self,
        requirement_id: uuid.UUID,
        assessment: Assessment,
        doc_type: str,
    ) -> list[PolicyMapping]:
        """Get evidence-type mappings that qualify for scoring (threshold + content check)."""
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

        mappings = (
            self.db.query(PolicyMapping)
            .join(Policy, PolicyMapping.policy_id == Policy.id)
            .filter(
                Policy.assessment_id == assessment.id,
                Policy.document_type == doc_type,
                PolicyMapping.requirement_id == requirement_id,
                PolicyMapping.is_rejected == False,  # noqa: E712
            )
            .all()
        )

        return [
            m for m in mappings
            if (m.relevance_percentage is not None and m.relevance_percentage >= threshold)
            and m.policy
            and m.policy.content_text
        ]

    @staticmethod
    def _get_implementation_examples(req: FrameworkRequirement) -> list[str]:
        meta = req.extra_metadata or {}
        examples = meta.get("implementation_examples") or []
        if isinstance(examples, list):
            return [str(e) for e in examples if e]
        return []

    def _build_control_docs(self, qualifying_mappings: list[PolicyMapping], doc_type: str = "policy") -> list[dict]:
        seen_policy_ids: set[uuid.UUID] = set()
        docs: list[dict] = []
        for mapping in qualifying_mappings:
            if not mapping.policy or mapping.policy_id in seen_policy_ids:
                continue
            seen_policy_ids.add(mapping.policy_id)

            raw = mapping.policy.content_text or ""
            is_spreadsheet = SpreadsheetIngestionService.is_supported(mapping.policy.name or "")

            entry: dict = {
                "document_name": mapping.policy.name,
                "document_type": "evidence_artifact",
            }

            if is_spreadsheet:
                try:
                    entry["content_format"] = "spreadsheet_json"
                    entry["content"] = json.loads(raw)
                except (json.JSONDecodeError, ValueError):
                    entry["content_format"] = "text"
                    entry["content"] = raw
            else:
                entry["content_format"] = "text"
                entry["content"] = raw

            docs.append(entry)
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
