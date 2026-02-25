"""Dashboard API endpoints."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.db.session import get_db
from app.dependencies.auth import require_user
from app.models.user import User
from app.models.assessment import Assessment, AssessmentStatus
from app.models.deviation import Deviation, DeviationStatus, DeviationSeverity
from app.models.audit import AuditLog
from app.models.score import FunctionScore
from app.models.unified_framework import (
    Framework,
    FrameworkRequirement,
    RequirementCrosswalk,
    AssessmentFrameworkScope,
)
from app.schemas.dashboard import (
    DashboardSummary,
    AssessmentCountByStatus,
    FrameworkCoverage,
    DeviationSummary,
    RecentAssessment,
    ActionItem,
    ActivityEntry,
)

router = APIRouter()


@router.get("/summary", response_model=DashboardSummary)
async def get_dashboard_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_user),
):
    """
    Get dashboard summary with compliance overview.

    Returns aggregated statistics including:
    - Assessment counts by status
    - Overall maturity score
    - Framework coverage
    - Deviation summary
    - Recent assessments
    - Pending action items
    - Activity feed
    """
    # Assessment counts by status
    status_counts = (
        db.query(Assessment.status, func.count(Assessment.id))
        .group_by(Assessment.status)
        .all()
    )
    status_map = {status: count for status, count in status_counts}

    assessments_by_status = AssessmentCountByStatus(
        draft=status_map.get(AssessmentStatus.DRAFT.value, 0),
        in_progress=status_map.get(AssessmentStatus.IN_PROGRESS.value, 0),
        review=status_map.get(AssessmentStatus.REVIEW.value, 0),
        completed=status_map.get(AssessmentStatus.COMPLETED.value, 0),
        archived=status_map.get(AssessmentStatus.ARCHIVED.value, 0),
    )

    total_assessments = sum(status_map.values())

    # Calculate overall maturity score from completed assessments
    overall_maturity = None
    completed_scores = (
        db.query(func.avg(FunctionScore.score))
        .join(Assessment, FunctionScore.assessment_id == Assessment.id)
        .filter(Assessment.status == AssessmentStatus.COMPLETED.value)
        .scalar()
    )
    if completed_scores is not None:
        overall_maturity = round(float(completed_scores), 2)

    # Framework coverage
    framework_coverage = []
    active_frameworks = (
        db.query(Framework).filter(Framework.is_active == True).all()
    )

    for framework in active_frameworks:
        total_reqs = (
            db.query(func.count(FrameworkRequirement.id))
            .filter(
                FrameworkRequirement.framework_id == framework.id,
                FrameworkRequirement.is_assessable == True,
            )
            .scalar()
            or 0
        )

        # Count requirements that have scores in any assessment
        assessed_reqs = (
            db.query(func.count(func.distinct(FrameworkRequirement.id)))
            .join(
                AssessmentFrameworkScope,
                AssessmentFrameworkScope.framework_id == FrameworkRequirement.framework_id,
            )
            .filter(
                FrameworkRequirement.framework_id == framework.id,
                FrameworkRequirement.is_assessable == True,
            )
            .scalar()
            or 0
        )

        coverage_pct = (assessed_reqs / total_reqs * 100) if total_reqs > 0 else 0

        framework_coverage.append(
            FrameworkCoverage(
                framework_id=framework.id,
                framework_code=framework.code,
                framework_name=framework.name,
                total_requirements=total_reqs,
                assessed_requirements=assessed_reqs,
                coverage_percentage=round(coverage_pct, 1),
            )
        )

    # Deviation summary
    deviation_counts = (
        db.query(Deviation.severity, func.count(Deviation.id))
        .filter(Deviation.status == DeviationStatus.OPEN.value)
        .group_by(Deviation.severity)
        .all()
    )
    deviation_map = {severity: count for severity, count in deviation_counts}

    deviation_summary = DeviationSummary(
        critical=deviation_map.get(DeviationSeverity.CRITICAL.value, 0),
        high=deviation_map.get(DeviationSeverity.HIGH.value, 0),
        medium=deviation_map.get(DeviationSeverity.MEDIUM.value, 0),
        low=deviation_map.get(DeviationSeverity.LOW.value, 0),
        total=sum(deviation_map.values()),
    )

    open_deviations = sum(deviation_map.values())

    # Recent assessments (last 5)
    recent_assessments_query = (
        db.query(Assessment)
        .order_by(Assessment.updated_at.desc())
        .limit(5)
        .all()
    )

    recent_assessments = []
    for assessment in recent_assessments_query:
        # Get average function score for this assessment
        avg_score = (
            db.query(func.avg(FunctionScore.score))
            .filter(FunctionScore.assessment_id == assessment.id)
            .scalar()
        )

        recent_assessments.append(
            RecentAssessment(
                id=assessment.id,
                name=assessment.name,
                organization_name=assessment.organization_name,
                status=assessment.status,
                maturity_score=round(float(avg_score), 2) if avg_score else None,
                updated_at=assessment.updated_at,
            )
        )

    # Pending approvals (crosswalks)
    pending_crosswalks = (
        db.query(func.count(RequirementCrosswalk.id))
        .filter(RequirementCrosswalk.is_approved == False)
        .scalar()
        or 0
    )

    pending_approvals = pending_crosswalks

    # Action items (up to 10)
    action_items = []

    # Get pending crosswalks
    pending_xwalks = (
        db.query(RequirementCrosswalk)
        .filter(RequirementCrosswalk.is_approved == False)
        .order_by(RequirementCrosswalk.created_at.desc())
        .limit(5)
        .all()
    )

    for xwalk in pending_xwalks:
        action_items.append(
            ActionItem(
                id=xwalk.id,
                type="crosswalk_approval",
                title="Cross-framework mapping needs approval",
                assessment_name=None,
                created_at=xwalk.created_at,
            )
        )

    # Sort action items by date
    action_items.sort(key=lambda x: x.created_at, reverse=True)
    action_items = action_items[:10]

    # Recent activity (last 10 entries)
    recent_logs = (
        db.query(AuditLog, User.name)
        .outerjoin(User, AuditLog.user_id == User.id)
        .order_by(AuditLog.timestamp.desc())
        .limit(10)
        .all()
    )

    recent_activity = [
        ActivityEntry(
            id=log.id,
            action=log.action,
            entity_type=log.entity_type,
            user_name=user_name,
            timestamp=log.timestamp,
            details=log.details,
        )
        for log, user_name in recent_logs
    ]

    return DashboardSummary(
        total_assessments=total_assessments,
        assessments_by_status=assessments_by_status,
        overall_maturity_score=overall_maturity,
        overall_maturity_trend=None,  # TODO: Calculate from historical data
        framework_coverage=framework_coverage,
        deviation_summary=deviation_summary,
        open_deviations=open_deviations,
        recent_assessments=recent_assessments,
        pending_approvals=pending_approvals,
        action_items=action_items,
        recent_activity=recent_activity,
    )
