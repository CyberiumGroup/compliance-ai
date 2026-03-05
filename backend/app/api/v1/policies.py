"""Policy endpoints."""

import uuid
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status, UploadFile, File, Form
from sqlalchemy.orm import Session

from app.db.session import get_db, SessionLocal
from app.models.policy import Policy, PolicyChunk
from app.models.policy_fact import PolicyFact
from app.models.user import User
from app.schemas.policy import (
    PolicyResponse,
    PolicyUploadResponse,
)
from app.dependencies.auth import get_current_user, require_user
from app.services.ingestion.policy_ingestion import PolicyIngestionService
from app.services.ingestion.spreadsheet_ingestion import SPREADSHEET_EXTENSIONS
from app.services.extraction.fact_extraction_service import FactExtractionService
from app.core.config import settings

router = APIRouter()


async def _run_fact_extraction(policy_id: uuid.UUID) -> None:
    """Background task: extract facts for a newly uploaded document.

    Uses its own DB session (independent of the request session which has
    already closed by the time the background task runs).
    """
    import logging
    _log = logging.getLogger(__name__)
    db = SessionLocal()
    try:
        service = FactExtractionService(db)
        await service.extract_and_store(policy_id)
    except Exception:
        # extract_and_store handles its own error logging; this catches anything
        # that escapes (e.g. DB connection failure) without spamming tracebacks
        # for expected transient LLM errors.
        _log.error("Fact extraction background task failed for policy %s", policy_id, exc_info=True)
    finally:
        db.close()


@router.post(
    "/assessments/{assessment_id}/policies/upload",
    response_model=PolicyUploadResponse,
)
async def upload_policy(
    assessment_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    name: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    version: Optional[str] = Form(None),
    owner: Optional[str] = Form(None),
    document_type: str = Form("policy"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_user),
):
    """Upload a policy document (PDF, DOCX, TXT, MD).

    document_type: 'policy' (design-level documentation, default) or
                   'evidence' (implementation evidence / audit artefacts).
    """
    if document_type not in ("policy", "evidence"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="document_type must be 'policy' or 'evidence'",
        )

    # Validate file extension
    filename = file.filename or "unknown"
    ext = Path(filename).suffix.lower()

    if ext in SPREADSHEET_EXTENSIONS:
        if document_type != "evidence":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Spreadsheet files (.xlsx, .xls, .csv) may only be uploaded as evidence documents.",
            )
    elif ext not in {e.lower() for e in settings.allowed_policy_extensions}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File type '{ext}' is not supported. Allowed: {', '.join(sorted(settings.allowed_policy_extensions))}",
        )

    # Check file size
    content = await file.read()
    if len(content) > settings.max_upload_size_mb * 1024 * 1024:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File too large. Maximum size: {settings.max_upload_size_mb}MB",
        )

    # Process the file
    ingestion_service = PolicyIngestionService(db)
    result = ingestion_service.ingest_file(
        file_content=content,
        filename=filename,
        assessment_id=assessment_id,
        user_id=current_user.id,
        name=name,
        description=description,
        version=version,
        owner=owner,
        document_type=document_type,
    )

    # Trigger fact extraction as a background task (non-blocking)
    if result.get("text_extracted"):
        policy_id = result["policy"].id
        background_tasks.add_task(_run_fact_extraction, policy_id)

    return PolicyUploadResponse(
        policy=PolicyResponse.model_validate(result["policy"]),
        text_extracted=result["text_extracted"],
        text_length=result.get("text_length"),
        extraction_error=result.get("extraction_error"),
    )


@router.get("/assessments/{assessment_id}/policies", response_model=list[PolicyResponse])
async def list_policies(
    assessment_id: uuid.UUID,
    document_type: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_current_user),
):
    """List all policies for an assessment.

    Optionally filter by document_type ('policy' or 'evidence').
    """
    query = db.query(Policy).filter(Policy.assessment_id == assessment_id)
    if document_type:
        query = query.filter(Policy.document_type == document_type)
    return query.all()


@router.get("/policies/{policy_id}", response_model=PolicyResponse)
async def get_policy(
    policy_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_current_user),
):
    """Get a policy by ID."""
    policy = db.query(Policy).filter(Policy.id == policy_id).first()

    if not policy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Policy not found",
        )

    return policy


@router.delete("/policies/{policy_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_policy(
    policy_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_user),
):
    """Delete a policy."""
    policy = db.query(Policy).filter(Policy.id == policy_id).first()

    if not policy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Policy not found",
        )

    db.delete(policy)
    db.commit()


@router.get("/assessments/{assessment_id}/policies/{policy_id}/facts")
async def get_policy_facts(
    assessment_id: uuid.UUID,
    policy_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user),
):
    """Return extracted control facts for a policy document.

    Returns:
        {
          "facts_extracted_at": ISO timestamp | null,
          "facts": [ { id, fact_index, fact_type, statement, key_attributes,
                       confidence, document_reference, extraction_model } ]
        }
    """
    policy = db.query(Policy).filter(
        Policy.id == policy_id,
        Policy.assessment_id == assessment_id,
    ).first()
    if not policy:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Policy not found")

    facts = (
        db.query(PolicyFact)
        .filter(PolicyFact.policy_id == policy_id)
        .order_by(PolicyFact.fact_index)
        .all()
    )
    return {
        "facts_extracted_at": policy.facts_extracted_at.isoformat() if policy.facts_extracted_at else None,
        "facts": [
            {
                "id": str(f.id),
                "fact_index": f.fact_index,
                "fact_type": f.fact_type,
                "statement": f.statement,
                "key_attributes": f.key_attributes,
                "confidence": f.confidence,
                "document_reference": f.document_reference,
                "extraction_model": f.extraction_model,
            }
            for f in facts
        ],
    }


@router.post("/assessments/{assessment_id}/policies/{policy_id}/facts/regenerate")
async def regenerate_policy_facts(
    assessment_id: uuid.UUID,
    policy_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_user),
):
    """Re-run fact extraction for a document in the background.

    Returns immediately with {"queued": true}. Poll GET /facts to check completion
    via the facts_extracted_at timestamp.
    """
    policy = db.query(Policy).filter(
        Policy.id == policy_id,
        Policy.assessment_id == assessment_id,
    ).first()
    if not policy:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Policy not found")

    if not policy.content_text:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Policy has no extractable content — cannot run fact extraction.",
        )

    # Clear the timestamp so the UI shows "pending" while the task runs
    policy.facts_extracted_at = None
    db.commit()

    background_tasks.add_task(_run_fact_extraction, policy_id)
    return {"queued": True}


@router.get("/assessments/{assessment_id}/policies/{policy_id}/chunks")
async def get_policy_chunks(
    assessment_id: uuid.UUID,
    policy_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user),
):
    """Return pre-stored chunks for a policy (no embeddings included)."""
    chunks = (
        db.query(PolicyChunk)
        .filter(PolicyChunk.policy_id == policy_id)
        .order_by(PolicyChunk.chunk_index)
        .all()
    )
    return [
        {
            "chunk_index": c.chunk_index,
            "chunk_text": c.chunk_text,
            "token_count": c.token_count,
            "has_embedding": c.embedding_vector is not None,
        }
        for c in chunks
    ]
