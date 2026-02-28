"""LLM-assisted scoring endpoints.

All routes are mounted under /assessments/{assessment_id}/scoring/... via the
router prefix in api/v1/__init__.py.
"""

import logging
import uuid
from datetime import datetime

logger = logging.getLogger(__name__)

from fastapi import APIRouter, BackgroundTasks, Body, Depends, HTTPException, status
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.assessment import Assessment
from app.models.scoring_job import RequirementScore, ScoringJob
from app.models.unified_framework import AssessmentFrameworkScope, FrameworkRequirement
from app.models.user import User
from app.dependencies.auth import get_current_user, require_user
from app.services.scoring.llm_scoring_engine import LLMScoringEngine
from app.services.report.excel_generator import generate_scoring_export

router = APIRouter()


def _job_to_dict(job: ScoringJob) -> dict:
    return {
        "id": str(job.id),
        "assessment_id": str(job.assessment_id),
        "status": job.status,
        "total_requirements": job.total_requirements,
        "completed_requirements": job.completed_requirements,
        "failed_requirements": job.failed_requirements,
        "error_message": job.error_message,
        "started_at": job.started_at.isoformat() if job.started_at else None,
        "completed_at": job.completed_at.isoformat() if job.completed_at else None,
        "created_at": job.created_at.isoformat(),
    }


def _build_ancestors(req: FrameworkRequirement | None, req_map: dict) -> list[dict]:
    """Return the ancestor chain from root to immediate parent (excluding req itself)."""
    if not req or not req.parent_id:
        return []
    chain: list[dict] = []
    current = req_map.get(req.parent_id)
    while current:
        chain.insert(0, {
            "id": str(current.id),
            "code": current.code,
            "name": current.name,
        })
        current = req_map.get(current.parent_id) if current.parent_id else None
    return chain


def _req_sort_key(req: FrameworkRequirement, req_map: dict) -> tuple:
    """DFS pre-order sort key based on display_order at each ancestor level."""
    path: list[tuple] = []
    current: FrameworkRequirement | None = req
    while current:
        path.insert(0, (current.display_order or 0, current.code or ""))
        current = req_map.get(current.parent_id) if current.parent_id else None
    return tuple(v for pair in path for v in pair)


def _req_to_unscored_dict(req: FrameworkRequirement, req_map: dict) -> dict:
    """Return a synthetic 'not_scored' entry for a requirement that has no score row."""
    ancestors = _build_ancestors(req, req_map)
    return {
        "id": str(req.id),          # use requirement_id as id — consistent with requirement_id
        "assessment_id": None,
        "requirement_id": str(req.id),
        "framework_id": str(req.framework_id),
        "requirement_code": req.code,
        "requirement_name": req.name,
        "requirement_description": req.description,
        "ancestors": ancestors,
        "score1": None,
        "score2": None,
        "score3": None,
        "phase1_output": None,
        "phase2_output": None,
        "phase4_output": None,
        "phase5_output": None,
        "score1_explanation": None,
        "score2_explanation": None,
        "score3_explanation": None,
        "model_used": None,
        "llm_calls_used": None,
        "status": "not_scored",
        "skip_reason": None,
        "error_message": None,
        "scored_at": None,
    }


def _score_to_dict(score: RequirementScore, req_map: dict | None = None) -> dict:
    req: FrameworkRequirement | None = score.requirement
    ancestors = _build_ancestors(req, req_map) if req_map else []
    return {
        "id": str(score.id),
        "assessment_id": str(score.assessment_id),
        "requirement_id": str(score.requirement_id),
        "framework_id": str(req.framework_id) if req else None,
        "requirement_code": req.code if req else None,
        "requirement_name": req.name if req else None,
        "requirement_description": req.description if req else None,
        "ancestors": ancestors,
        "score1": score.score1,
        "score2": score.score2,
        "score3": score.score3,
        "phase1_output": score.phase1_output,
        "phase2_output": score.phase2_output,
        "phase4_output": score.phase4_output,
        "phase5_output": score.phase5_output,
        "score1_explanation": score.score1_explanation,
        "score2_explanation": score.score2_explanation,
        "score3_explanation": score.score3_explanation,
        "model_used": score.model_used,
        "llm_calls_used": score.llm_calls_used,
        "status": score.status,
        "skip_reason": score.skip_reason,
        "error_message": score.error_message,
        "scored_at": score.scored_at.isoformat() if score.scored_at else None,
    }


async def _run_job_background(job_id: uuid.UUID, assessment_id: uuid.UUID) -> None:
    """Async background task that runs the full scoring job in a new DB session."""
    from app.db.session import SessionLocal

    logger.info("Background scoring task started: job=%s assessment=%s", job_id, assessment_id)
    db = SessionLocal()
    try:
        engine = LLMScoringEngine(db)
        await engine.run_job(job_id, assessment_id)
    except Exception as exc:
        logger.exception("Background scoring task failed: job=%s error=%s", job_id, exc)
        try:
            job = db.query(ScoringJob).filter(ScoringJob.id == job_id).first()
            if job:
                job.status = "failed"
                job.error_message = str(exc)
                job.completed_at = datetime.utcnow()
                db.commit()
        except Exception:
            pass
    finally:
        db.close()


@router.post("/{assessment_id}/scoring/run")
async def run_scoring(
    assessment_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_user),
):
    """Start a background scoring job for all in-scope assessable requirements."""
    assessment = db.query(Assessment).filter(Assessment.id == assessment_id).first()
    if not assessment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assessment not found")

    # Create job record
    job = ScoringJob(
        id=uuid.uuid4(),
        assessment_id=assessment_id,
        status="pending",
        created_at=datetime.utcnow(),
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    # Launch async background task (FastAPI schedules it on the running event loop)
    background_tasks.add_task(_run_job_background, job.id, assessment_id)

    return {"job_id": str(job.id), "status": "pending"}


@router.get("/{assessment_id}/scoring/job")
async def get_scoring_job(
    assessment_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_current_user),
):
    """Get the latest scoring job for an assessment."""
    assessment = db.query(Assessment).filter(Assessment.id == assessment_id).first()
    if not assessment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assessment not found")

    job = (
        db.query(ScoringJob)
        .filter(ScoringJob.assessment_id == assessment_id)
        .order_by(ScoringJob.created_at.desc())
        .first()
    )

    if not job:
        return None

    return _job_to_dict(job)


@router.get("/{assessment_id}/scoring/requirements")
async def get_requirement_scores(
    assessment_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_current_user),
):
    """Return all in-scope assessable requirements, merged with any existing score data.

    Requirements that have never been scored are returned with status='not_scored'.
    Results are ordered by framework hierarchy (DFS display_order).
    """
    assessment = db.query(Assessment).filter(Assessment.id == assessment_id).first()
    if not assessment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assessment not found")

    # Load all in-scope framework requirements for sort keys and ancestor resolution
    scope_rows = (
        db.query(AssessmentFrameworkScope)
        .filter(AssessmentFrameworkScope.assessment_id == assessment_id)
        .all()
    )
    if not scope_rows:
        return []

    scope_fw_ids = [s.framework_id for s in scope_rows]
    req_map: dict[uuid.UUID, FrameworkRequirement] = {
        r.id: r
        for r in db.query(FrameworkRequirement)
        .filter(FrameworkRequirement.framework_id.in_(scope_fw_ids))
        .all()
    }

    # Collect all in-scope assessable requirements respecting include/exclude lists
    in_scope_reqs: list[FrameworkRequirement] = []
    for scope in scope_rows:
        reqs = [
            r for r in req_map.values()
            if r.framework_id == scope.framework_id and r.is_assessable
        ]
        if not scope.include_all:
            included = set(str(i) for i in (scope.included_requirement_ids or []))
            reqs = [r for r in reqs if str(r.id) in included]
        else:
            excluded = set(str(i) for i in (scope.excluded_requirement_ids or []))
            reqs = [r for r in reqs if str(r.id) not in excluded]
        in_scope_reqs.extend(reqs)

    # Sort by hierarchy order (DFS display_order)
    in_scope_reqs.sort(key=lambda r: _req_sort_key(r, req_map))

    # Index existing score rows by requirement_id
    scores_by_req_id: dict[uuid.UUID, RequirementScore] = {
        s.requirement_id: s
        for s in db.query(RequirementScore)
        .filter(RequirementScore.assessment_id == assessment_id)
        .all()
    }

    # Merge: every in-scope requirement gets an entry (scored or not_scored)
    return [
        _score_to_dict(scores_by_req_id[req.id], req_map)
        if req.id in scores_by_req_id
        else _req_to_unscored_dict(req, req_map)
        for req in in_scope_reqs
    ]


@router.post("/{assessment_id}/scoring/requirements/{requirement_id}/rerun")
async def rerun_requirement_score(
    assessment_id: uuid.UUID,
    requirement_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_user),
):
    """Re-score a single requirement using the latest context (runs synchronously)."""
    assessment = db.query(Assessment).filter(Assessment.id == assessment_id).first()
    if not assessment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assessment not found")

    req = db.query(FrameworkRequirement).filter(FrameworkRequirement.id == requirement_id).first()
    if not req:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Requirement not found")

    engine = LLMScoringEngine(db)
    result = await engine.score_single_requirement(requirement_id, assessment_id)

    # Fetch the updated score row for full response
    score = (
        db.query(RequirementScore)
        .filter(
            RequirementScore.assessment_id == assessment_id,
            RequirementScore.requirement_id == requirement_id,
        )
        .first()
    )

    if score:
        scope_fw_ids = [
            s.framework_id
            for s in db.query(AssessmentFrameworkScope)
            .filter(AssessmentFrameworkScope.assessment_id == assessment_id)
            .all()
        ]
        req_map: dict[uuid.UUID, FrameworkRequirement] = {
            r.id: r
            for r in db.query(FrameworkRequirement)
            .filter(FrameworkRequirement.framework_id.in_(scope_fw_ids))
            .all()
        }
        return _score_to_dict(score, req_map)

    return result


@router.delete("/{assessment_id}/scoring/requirements")
async def clear_requirement_scores(
    assessment_id: uuid.UUID,
    requirement_ids: list[uuid.UUID] = Body(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_user),
):
    """Delete RequirementScore rows for the given requirement IDs within this assessment."""
    assessment = db.query(Assessment).filter(Assessment.id == assessment_id).first()
    if not assessment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assessment not found")

    deleted = (
        db.query(RequirementScore)
        .filter(
            RequirementScore.assessment_id == assessment_id,
            RequirementScore.requirement_id.in_(requirement_ids),
        )
        .delete(synchronize_session=False)
    )
    db.commit()
    return {"deleted": deleted}


@router.get("/{assessment_id}/scoring/export")
async def export_scoring_excel(
    assessment_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_current_user),
):
    """Download all scoring results for an assessment as an Excel workbook."""
    assessment = db.query(Assessment).filter(Assessment.id == assessment_id).first()
    if not assessment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assessment not found")

    try:
        xlsx_bytes = generate_scoring_export(db, assessment_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))

    filename = f"compliance-scores-{assessment_id}.xlsx"
    return Response(
        content=xlsx_bytes,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
