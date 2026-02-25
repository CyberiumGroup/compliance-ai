"""Main scoring engine for calculating assessment maturity scores."""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session, joinedload

from app.models.score import SubcategoryScore, CategoryScore, FunctionScore
from app.models.policy import Policy, PolicyMapping
from app.models.interview import InterviewSession, InterviewResponse, InterviewQuestion
from app.models.framework import CSFFunction, CSFCategory, CSFSubcategory
from app.services.audit.audit_service import AuditService
from app.services.scoring.rubric import ScoringRubric
from app.services.scoring.explanation_builder import ExplanationBuilder


class ScoringEngine:
    """Engine for calculating maturity scores for assessments."""

    def __init__(self, db: Session):
        self.db = db
        self.audit_service = AuditService(db)
        self.rubric = ScoringRubric()
        self.explanation_builder = ExplanationBuilder()

    def calculate_all_scores(
        self,
        assessment_id: uuid.UUID,
        user_id: uuid.UUID | None = None,
    ) -> dict[str, Any]:
        """
        Calculate all scores for an assessment.

        Returns:
            Summary of calculated scores
        """
        # Calculate subcategory scores first
        subcat_results = self._calculate_subcategory_scores(assessment_id)

        # Calculate category scores (aggregate from subcategories)
        cat_results = self._calculate_category_scores(assessment_id)

        # Calculate function scores (aggregate from categories)
        func_results = self._calculate_function_scores(assessment_id)

        # Calculate overall maturity
        if func_results:
            overall = sum(f["score"] for f in func_results) / len(func_results)
        else:
            overall = 0.0

        # Audit log
        self.audit_service.log_calculation(
            entity_type="assessment",
            entity_id=assessment_id,
            calculation_type="scores",
            result={
                "subcategory_count": len(subcat_results),
                "category_count": len(cat_results),
                "function_count": len(func_results),
                "overall_maturity": round(overall, 2),
            },
            user_id=user_id,
        )

        self.db.commit()

        return {
            "assessment_id": assessment_id,
            "overall_maturity": round(overall, 2),
            "function_scores": func_results,
            "category_scores": cat_results,
            "calculated_at": datetime.utcnow().isoformat(),
        }

    def _calculate_subcategory_scores(
        self,
        assessment_id: uuid.UUID,
    ) -> list[dict]:
        """Calculate scores for all subcategories."""
        subcategories = self.db.query(CSFSubcategory).all()
        results = []

        for subcat in subcategories:
            evidence = self._gather_evidence(assessment_id, subcat.id)
            score, breakdown = self.rubric.calculate_score(evidence)

            # Build explanation
            explanation = self.explanation_builder.build_subcategory_explanation(
                subcategory_code=subcat.code,
                score=score,
                score_breakdown=breakdown,
                policy_evidence=evidence.get("policy_evidence"),
                interview_evidence=evidence.get("interview_evidence"),
            )

            # Upsert score
            existing = self.db.query(SubcategoryScore).filter(
                SubcategoryScore.assessment_id == assessment_id,
                SubcategoryScore.subcategory_id == subcat.id,
            ).first()

            if existing:
                existing.score = score
                existing.explanation_payload = explanation
                existing.calculated_at = datetime.utcnow()
                existing.version += 1
            else:
                score_record = SubcategoryScore(
                    id=uuid.uuid4(),
                    assessment_id=assessment_id,
                    subcategory_id=subcat.id,
                    score=score,
                    explanation_payload=explanation,
                    calculated_at=datetime.utcnow(),
                    calculated_by="scoring_engine",
                    version=1,
                )
                self.db.add(score_record)

            results.append({
                "code": subcat.code,
                "score": score,
                "tier_name": breakdown.get("tier_name"),
            })

        self.db.flush()
        return results

    def _calculate_category_scores(
        self,
        assessment_id: uuid.UUID,
    ) -> list[dict]:
        """Calculate scores for all categories (average of subcategories)."""
        categories = (
            self.db.query(CSFCategory)
            .options(joinedload(CSFCategory.subcategories))
            .all()
        )
        results = []

        for cat in categories:
            # Get subcategory scores for this category
            subcat_ids = [sc.id for sc in cat.subcategories]

            subcat_scores = (
                self.db.query(SubcategoryScore)
                .filter(
                    SubcategoryScore.assessment_id == assessment_id,
                    SubcategoryScore.subcategory_id.in_(subcat_ids),
                )
                .all()
            )

            if not subcat_scores:
                score = 0.0
            else:
                score = sum(s.score for s in subcat_scores) / len(subcat_scores)

            # Build explanation
            subcat_data = [
                {
                    "code": self.db.query(CSFSubcategory).get(s.subcategory_id).code,
                    "score": s.score,
                    "tier_name": s.explanation_payload.get("score_breakdown", {}).get("tier_name"),
                }
                for s in subcat_scores
            ]

            explanation = self.explanation_builder.build_category_explanation(
                category_code=cat.code,
                score=score,
                subcategory_scores=subcat_data,
            )

            # Upsert score
            existing = self.db.query(CategoryScore).filter(
                CategoryScore.assessment_id == assessment_id,
                CategoryScore.category_id == cat.id,
            ).first()

            if existing:
                existing.score = round(score, 2)
                existing.explanation_payload = explanation
                existing.calculated_at = datetime.utcnow()
                existing.version += 1
            else:
                score_record = CategoryScore(
                    id=uuid.uuid4(),
                    assessment_id=assessment_id,
                    category_id=cat.id,
                    score=round(score, 2),
                    explanation_payload=explanation,
                    calculated_at=datetime.utcnow(),
                    version=1,
                )
                self.db.add(score_record)

            results.append({
                "code": cat.code,
                "name": cat.name,
                "score": round(score, 2),
            })

        self.db.flush()
        return results

    def _calculate_function_scores(
        self,
        assessment_id: uuid.UUID,
    ) -> list[dict]:
        """Calculate scores for all functions (average of categories)."""
        functions = (
            self.db.query(CSFFunction)
            .options(joinedload(CSFFunction.categories))
            .all()
        )
        results = []

        for func in functions:
            # Get category scores for this function
            cat_ids = [c.id for c in func.categories]

            cat_scores = (
                self.db.query(CategoryScore)
                .filter(
                    CategoryScore.assessment_id == assessment_id,
                    CategoryScore.category_id.in_(cat_ids),
                )
                .all()
            )

            if not cat_scores:
                score = 0.0
            else:
                score = sum(s.score for s in cat_scores) / len(cat_scores)

            # Build explanation
            cat_data = [
                {
                    "code": self.db.query(CSFCategory).get(s.category_id).code,
                    "name": self.db.query(CSFCategory).get(s.category_id).name,
                    "score": s.score,
                }
                for s in cat_scores
            ]

            explanation = self.explanation_builder.build_function_explanation(
                function_code=func.code,
                score=score,
                category_scores=cat_data,
            )

            # Upsert score
            existing = self.db.query(FunctionScore).filter(
                FunctionScore.assessment_id == assessment_id,
                FunctionScore.function_id == func.id,
            ).first()

            if existing:
                existing.score = round(score, 2)
                existing.explanation_payload = explanation
                existing.calculated_at = datetime.utcnow()
                existing.version += 1
            else:
                score_record = FunctionScore(
                    id=uuid.uuid4(),
                    assessment_id=assessment_id,
                    function_id=func.id,
                    score=round(score, 2),
                    explanation_payload=explanation,
                    calculated_at=datetime.utcnow(),
                    version=1,
                )
                self.db.add(score_record)

            results.append({
                "code": func.code,
                "name": func.name,
                "score": round(score, 2),
            })

        self.db.flush()
        return results

    def _gather_evidence(
        self,
        assessment_id: uuid.UUID,
        subcategory_id: uuid.UUID,
    ) -> dict[str, Any]:
        """Gather all evidence for scoring a subcategory."""
        # Get policy mappings
        policy_mappings = (
            self.db.query(PolicyMapping)
            .join(Policy)
            .filter(
                Policy.assessment_id == assessment_id,
                PolicyMapping.subcategory_id == subcategory_id,
                PolicyMapping.is_approved == True,
            )
            .all()
        )

        policy_evidence = []
        for pm in policy_mappings:
            policy = self.db.query(Policy).filter(Policy.id == pm.policy_id).first()
            if policy:
                policy_evidence.append({
                    "id": policy.id,
                    "name": policy.name,
                    "confidence_score": pm.confidence_score,
                })

        # Get interview responses for this subcategory
        interview_evidence = []
        questions = (
            self.db.query(InterviewQuestion)
            .filter(InterviewQuestion.subcategory_id == subcategory_id)
            .all()
        )
        question_ids = [q.id for q in questions]

        if question_ids:
            # Get sessions for this assessment
            sessions = (
                self.db.query(InterviewSession)
                .filter(InterviewSession.assessment_id == assessment_id)
                .all()
            )
            session_ids = [s.id for s in sessions]

            if session_ids:
                responses = (
                    self.db.query(InterviewResponse)
                    .filter(
                        InterviewResponse.session_id.in_(session_ids),
                        InterviewResponse.question_id.in_(question_ids),
                    )
                    .all()
                )

                for resp in responses:
                    question = next((q for q in questions if q.id == resp.question_id), None)
                    interview_evidence.append({
                        "question_type": question.question_type if question else None,
                        "question_text": question.question_text if question else None,
                        "response_value": resp.response_value,
                        "response_text": resp.response_text,
                    })

        # Derive evidence flags from collected data
        evidence = self.rubric.score_from_interview_responses(interview_evidence)

        # Override with mapping evidence
        if policy_evidence:
            evidence["has_policy"] = True

        # Add raw evidence for explanation building
        evidence["policy_evidence"] = policy_evidence
        evidence["interview_evidence"] = interview_evidence

        return evidence

    def get_score_summary(
        self,
        assessment_id: uuid.UUID,
    ) -> dict[str, Any]:
        """Get a summary of all scores for an assessment."""
        func_scores = (
            self.db.query(FunctionScore)
            .filter(FunctionScore.assessment_id == assessment_id)
            .all()
        )

        if not func_scores:
            return {
                "assessment_id": assessment_id,
                "overall_maturity": 0.0,
                "function_scores": [],
                "calculated_at": None,
            }

        overall = sum(s.score for s in func_scores) / len(func_scores)

        func_data = []
        for fs in func_scores:
            func = self.db.query(CSFFunction).filter(CSFFunction.id == fs.function_id).first()
            func_data.append({
                "id": fs.id,
                "function_id": fs.function_id,
                "function_code": func.code if func else None,
                "function_name": func.name if func else None,
                "score": fs.score,
                "calculated_at": fs.calculated_at.isoformat(),
                "version": fs.version,
            })

        return {
            "assessment_id": assessment_id,
            "overall_maturity": round(overall, 2),
            "function_scores": func_data,
            "calculated_at": max(s.calculated_at for s in func_scores).isoformat(),
        }
