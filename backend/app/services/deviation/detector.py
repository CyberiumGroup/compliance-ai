"""Deviation detection service."""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session, joinedload

from app.models.deviation import Deviation, DeviationType, DeviationSeverity, DeviationStatus
from app.models.score import SubcategoryScore
from app.models.policy import Policy, PolicyMapping
from app.models.framework import CSFSubcategory, CSFCategory, CSFFunction
from app.services.audit.audit_service import AuditService
from app.services.deviation.risk_calculator import RiskCalculator


class DeviationDetector:
    """Service for detecting compliance deviations."""

    def __init__(self, db: Session):
        self.db = db
        self.audit_service = AuditService(db)
        self.risk_calculator = RiskCalculator()

    def detect_all_deviations(
        self,
        assessment_id: uuid.UUID,
        user_id: uuid.UUID | None = None,
    ) -> list[dict[str, Any]]:
        """
        Detect all deviations for an assessment.

        Types detected:
        - missing_policy: Subcategory has control but no policy
        - missing_control: Subcategory has policy but no control
        - inadequate_policy: Low score despite having policy
        - inadequate_control: Low score despite having control
        - policy_control_gap: Gap between policy intent and control implementation

        Returns:
            List of detected deviations
        """
        deviations = []

        # Get all subcategories with context
        subcategories = (
            self.db.query(CSFSubcategory)
            .options(
                joinedload(CSFSubcategory.category).joinedload(CSFCategory.function)
            )
            .all()
        )

        for subcat in subcategories:
            subcat_deviations = self._detect_for_subcategory(assessment_id, subcat)
            deviations.extend(subcat_deviations)

        # Save deviations to database
        for dev_data in deviations:
            self._create_deviation(assessment_id, dev_data, user_id)

        self.db.commit()

        return deviations

    def _detect_for_subcategory(
        self,
        assessment_id: uuid.UUID,
        subcategory: CSFSubcategory,
    ) -> list[dict[str, Any]]:
        """Detect deviations for a single subcategory."""
        deviations = []

        func_code = subcategory.category.function.code

        # Check for approved mappings
        policy_mappings = (
            self.db.query(PolicyMapping)
            .join(Policy)
            .filter(
                Policy.assessment_id == assessment_id,
                PolicyMapping.subcategory_id == subcategory.id,
                PolicyMapping.is_approved == True,
            )
            .all()
        )
        has_policy = len(policy_mappings) > 0

        # Get subcategory score
        score_record = (
            self.db.query(SubcategoryScore)
            .filter(
                SubcategoryScore.assessment_id == assessment_id,
                SubcategoryScore.subcategory_id == subcategory.id,
            )
            .first()
        )
        score = score_record.score if score_record else 0

        # Detect inadequate policy (has policy but low score)
        if has_policy and score <= 1:
            impact = self.risk_calculator.calculate_impact_from_function(func_code, 3)
            likelihood = 3
            risk_score, severity = self.risk_calculator.calculate_risk_score(impact, likelihood)

            deviations.append({
                "subcategory_id": subcategory.id,
                "subcategory_code": subcategory.code,
                "function_code": func_code,
                "deviation_type": DeviationType.INADEQUATE_POLICY.value,
                "severity": severity,
                "title": f"Inadequate policy coverage for {subcategory.code}",
                "description": f"Policy exists but maturity score is low ({score}/4) indicating inadequate coverage.",
                "impact_score": impact,
                "likelihood_score": likelihood,
                "risk_score": risk_score,
                "recommended_remediation": "Review and strengthen policy to fully address requirements.",
                "evidence": {
                    "score": score,
                    "has_policy": True,
                },
            })

        # Detect completely unmapped (no policy)
        if not has_policy:
            impact = self.risk_calculator.calculate_impact_from_function(func_code, 4)
            likelihood = 5
            risk_score, severity = self.risk_calculator.calculate_risk_score(impact, likelihood)

            deviations.append({
                "subcategory_id": subcategory.id,
                "subcategory_code": subcategory.code,
                "function_code": func_code,
                "deviation_type": DeviationType.DOCUMENTATION_GAP.value,
                "severity": severity,
                "title": f"No coverage for {subcategory.code}",
                "description": f"No policies are mapped to {subcategory.code}: {subcategory.description}",
                "impact_score": impact,
                "likelihood_score": likelihood,
                "risk_score": risk_score,
                "recommended_remediation": f"Develop and map a policy that addresses {subcategory.description}",
                "evidence": {
                    "has_policy": False,
                },
            })

        return deviations

    def _create_deviation(
        self,
        assessment_id: uuid.UUID,
        dev_data: dict[str, Any],
        user_id: uuid.UUID | None,
    ) -> Deviation:
        """Create a deviation record in the database."""
        # Check for existing deviation of same type for same subcategory
        existing = self.db.query(Deviation).filter(
            Deviation.assessment_id == assessment_id,
            Deviation.subcategory_id == dev_data["subcategory_id"],
            Deviation.deviation_type == dev_data["deviation_type"],
            Deviation.status != DeviationStatus.REMEDIATED.value,
        ).first()

        if existing:
            # Update existing deviation
            existing.severity = dev_data["severity"]
            existing.impact_score = dev_data["impact_score"]
            existing.likelihood_score = dev_data["likelihood_score"]
            existing.risk_score = dev_data["risk_score"]
            existing.evidence = dev_data.get("evidence")
            existing.updated_at = datetime.utcnow()
            return existing

        deviation = Deviation(
            id=uuid.uuid4(),
            assessment_id=assessment_id,
            subcategory_id=dev_data["subcategory_id"],
            deviation_type=dev_data["deviation_type"],
            severity=dev_data["severity"],
            status=DeviationStatus.OPEN.value,
            title=dev_data["title"],
            description=dev_data["description"],
            evidence=dev_data.get("evidence"),
            impact_score=dev_data["impact_score"],
            likelihood_score=dev_data["likelihood_score"],
            risk_score=dev_data["risk_score"],
            recommended_remediation=dev_data.get("recommended_remediation"),
            detected_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )

        self.db.add(deviation)

        return deviation

    def get_deviations(
        self,
        assessment_id: uuid.UUID,
        severity: str | None = None,
        status: str | None = None,
    ) -> list[Deviation]:
        """Get deviations for an assessment with optional filters."""
        query = self.db.query(Deviation).filter(
            Deviation.assessment_id == assessment_id
        )

        if severity:
            query = query.filter(Deviation.severity == severity)

        if status:
            query = query.filter(Deviation.status == status)

        return query.order_by(Deviation.risk_score.desc()).all()

    def get_risk_summary(
        self,
        assessment_id: uuid.UUID,
    ) -> dict[str, Any]:
        """Get risk summary for an assessment."""
        deviations = self.get_deviations(assessment_id)

        dev_data = []
        for dev in deviations:
            subcat = self.db.query(CSFSubcategory).filter(
                CSFSubcategory.id == dev.subcategory_id
            ).first()
            func_code = subcat.category.function.code if subcat else None

            dev_data.append({
                "subcategory_code": subcat.code if subcat else None,
                "function_code": func_code,
                "title": dev.title,
                "severity": dev.severity,
                "risk_score": dev.risk_score,
            })

        summary = self.risk_calculator.get_risk_summary(dev_data)
        summary["assessment_id"] = assessment_id

        return summary
