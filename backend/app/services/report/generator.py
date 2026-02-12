"""Report generation service."""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from app.models.report import Report, ReportType
from app.models.assessment import Assessment
from app.models.score import SubcategoryScore, CategoryScore, FunctionScore
from app.models.deviation import Deviation
from app.models.framework import CSFFunction, CSFCategory, CSFSubcategory
from app.services.audit.audit_service import AuditService
from app.services.scoring.scoring_engine import ScoringEngine
from app.services.deviation.detector import DeviationDetector


class ReportGenerator:
    """Service for generating assessment reports."""

    def __init__(self, db: Session):
        self.db = db
        self.audit_service = AuditService(db)
        self.scoring_engine = ScoringEngine(db)
        self.deviation_detector = DeviationDetector(db)

    def generate_full_report(
        self,
        assessment_id: uuid.UUID,
        user_id: uuid.UUID | None = None,
    ) -> Report:
        """Generate a full assessment report."""
        assessment = self.db.query(Assessment).filter(
            Assessment.id == assessment_id
        ).first()

        if not assessment:
            raise ValueError(f"Assessment {assessment_id} not found")

        # Gather all data
        score_summary = self.scoring_engine.get_score_summary(assessment_id)
        risk_summary = self.deviation_detector.get_risk_summary(assessment_id)
        deviations = self.deviation_detector.get_deviations(assessment_id)

        # Build report content
        content = self._build_report_content(
            assessment=assessment,
            score_summary=score_summary,
            risk_summary=risk_summary,
            deviations=deviations,
        )

        # Create report record
        report = Report(
            id=uuid.uuid4(),
            assessment_id=assessment_id,
            report_type=ReportType.FULL_ASSESSMENT.value,
            title=f"Compliance Assessment Report - {assessment.organization_name}",
            content=content,
            generated_at=datetime.utcnow(),
            generated_by_id=user_id,
            version=1,
            is_final=False,
        )

        self.db.add(report)

        # Audit log
        self.audit_service.log_generation(
            entity_type="report",
            entity_id=report.id,
            generation_type="full_assessment",
            user_id=user_id,
        )

        self.db.commit()

        return report

    def _build_report_content(
        self,
        assessment: Assessment,
        score_summary: dict[str, Any],
        risk_summary: dict[str, Any],
        deviations: list[Deviation],
    ) -> dict[str, Any]:
        """Build the full report content structure."""
        # Executive Summary
        overall_maturity = score_summary.get("overall_maturity", 0)

        key_strengths = []
        critical_gaps = []

        for fs in score_summary.get("function_scores", []):
            if fs.get("score", 0) >= 3:
                key_strengths.append(f"{fs.get('function_name', '')} ({fs.get('function_code', '')}): Score {fs.get('score')}")
            elif fs.get("score", 0) <= 1:
                critical_gaps.append(f"{fs.get('function_name', '')} ({fs.get('function_code', '')}): Score {fs.get('score')}")

        executive_summary = {
            "overall_maturity": overall_maturity,
            "key_strengths": key_strengths[:5],
            "critical_gaps": critical_gaps[:5],
            "recommendations_summary": self._generate_recommendations_summary(
                overall_maturity, risk_summary
            ),
        }

        # Maturity Summary
        maturity_summary = {
            "by_function": score_summary.get("function_scores", []),
            "by_category": self._get_category_scores(assessment.id),
        }

        # Deviation Summary
        severity_counts = {
            "critical": risk_summary.get("critical_count", 0),
            "high": risk_summary.get("high_count", 0),
            "medium": risk_summary.get("medium_count", 0),
            "low": risk_summary.get("low_count", 0),
        }

        deviation_list = []
        for dev in sorted(deviations, key=lambda x: x.risk_score, reverse=True):
            subcat = self.db.query(CSFSubcategory).filter(
                CSFSubcategory.id == dev.subcategory_id
            ).first()

            deviation_list.append({
                "id": str(dev.id),
                "subcategory_code": subcat.code if subcat else None,
                "deviation_type": dev.deviation_type,
                "severity": dev.severity,
                "title": dev.title,
                "description": dev.description,
                "risk_score": dev.risk_score,
                "recommended_remediation": dev.recommended_remediation,
                "status": dev.status,
            })

        deviation_summary = {
            "total_count": len(deviations),
            "by_severity": severity_counts,
            "risk_ranked_list": deviation_list,
        }

        # Recommendations
        recommendations = self._generate_recommendations(deviations, overall_maturity)

        # Function Details
        function_details = self._build_function_details(assessment.id)

        return {
            "executive_summary": executive_summary,
            "maturity_summary": maturity_summary,
            "deviations": deviation_summary,
            "recommendations": recommendations,
            "function_details": function_details,
            "metadata": {
                "assessment_id": str(assessment.id),
                "organization_name": assessment.organization_name,
                "assessment_name": assessment.name,
                "generated_at": datetime.utcnow().isoformat(),
                "framework": "multi-framework",
            },
        }

    def _get_category_scores(self, assessment_id: uuid.UUID) -> list[dict]:
        """Get category scores for the report."""
        cat_scores = self.db.query(CategoryScore).filter(
            CategoryScore.assessment_id == assessment_id
        ).all()

        result = []
        for cs in cat_scores:
            cat = self.db.query(CSFCategory).filter(CSFCategory.id == cs.category_id).first()
            if cat:
                result.append({
                    "category_code": cat.code,
                    "category_name": cat.name,
                    "score": cs.score,
                })

        return result

    def _generate_recommendations_summary(
        self,
        overall_maturity: float,
        risk_summary: dict[str, Any],
    ) -> str:
        """Generate a brief recommendations summary."""
        if overall_maturity < 2:
            return "Significant improvements needed across all compliance areas. Priority should be given to establishing foundational policies and controls."
        elif overall_maturity < 3:
            return "Organization shows partial maturity. Focus on formalizing existing practices and addressing critical gaps."
        else:
            return "Organization demonstrates solid maturity. Continue monitoring and focus on adaptive improvements."

    def _generate_recommendations(
        self,
        deviations: list[Deviation],
        overall_maturity: float,
    ) -> dict[str, Any]:
        """Generate prioritized recommendations."""
        immediate = []
        short_term = []
        long_term = []

        for dev in deviations:
            rec = {
                "subcategory_code": None,
                "action": dev.recommended_remediation,
                "rationale": dev.description,
                "risk_score": dev.risk_score,
            }

            subcat = self.db.query(CSFSubcategory).filter(
                CSFSubcategory.id == dev.subcategory_id
            ).first()
            if subcat:
                rec["subcategory_code"] = subcat.code

            if dev.severity in ["critical", "high"]:
                immediate.append(rec)
            elif dev.severity == "medium":
                short_term.append(rec)
            else:
                long_term.append(rec)

        # Add general recommendations based on maturity
        if overall_maturity < 2:
            immediate.append({
                "subcategory_code": None,
                "action": "Establish a cybersecurity governance framework",
                "rationale": "Foundational governance is needed before other improvements can be effective",
                "risk_score": 25,
            })

        return {
            "immediate": sorted(immediate, key=lambda x: x.get("risk_score", 0), reverse=True)[:10],
            "short_term": sorted(short_term, key=lambda x: x.get("risk_score", 0), reverse=True)[:10],
            "long_term": sorted(long_term, key=lambda x: x.get("risk_score", 0), reverse=True)[:10],
        }

    def _build_function_details(
        self,
        assessment_id: uuid.UUID,
    ) -> list[dict[str, Any]]:
        """Build detailed breakdown by function."""
        functions = self.db.query(CSFFunction).all()
        details = []

        for func in functions:
            func_score = self.db.query(FunctionScore).filter(
                FunctionScore.assessment_id == assessment_id,
                FunctionScore.function_id == func.id,
            ).first()

            categories = []
            for cat in func.categories:
                cat_score = self.db.query(CategoryScore).filter(
                    CategoryScore.assessment_id == assessment_id,
                    CategoryScore.category_id == cat.id,
                ).first()

                subcategories = []
                for subcat in cat.subcategories:
                    subcat_score = self.db.query(SubcategoryScore).filter(
                        SubcategoryScore.assessment_id == assessment_id,
                        SubcategoryScore.subcategory_id == subcat.id,
                    ).first()

                    subcategories.append({
                        "code": subcat.code,
                        "description": subcat.description,
                        "score": subcat_score.score if subcat_score else 0,
                    })

                categories.append({
                    "code": cat.code,
                    "name": cat.name,
                    "score": cat_score.score if cat_score else 0,
                    "subcategories": subcategories,
                })

            details.append({
                "code": func.code,
                "name": func.name,
                "description": func.description,
                "score": func_score.score if func_score else 0,
                "categories": categories,
            })

        return details

    def get_report(self, report_id: uuid.UUID) -> Report | None:
        """Get a report by ID."""
        return self.db.query(Report).filter(Report.id == report_id).first()

    def list_reports(self, assessment_id: uuid.UUID) -> list[Report]:
        """List all reports for an assessment."""
        return self.db.query(Report).filter(
            Report.assessment_id == assessment_id
        ).order_by(Report.generated_at.desc()).all()
