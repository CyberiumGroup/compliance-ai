"""Policy endpoints."""

import uuid
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.policy import Policy, PolicyChunk
from app.models.user import User
from app.schemas.policy import (
    PolicyResponse,
    PolicyUploadResponse,
)
from app.dependencies.auth import get_current_user, require_user
from app.services.ingestion.policy_ingestion import PolicyIngestionService
from app.services.ingestion.spreadsheet_ingestion import SPREADSHEET_EXTENSIONS
from app.core.config import settings

router = APIRouter()


# Valid sections and their allowed extensions / derived document_type
_SECTION_DOCUMENT_TYPE: dict[str, str] = {
    "policy": "policy",
    "process": "policy",
    "control": "evidence",
    "interview": "evidence",
    "proof": "evidence",
}

_SECTION_ALLOWED_EXTENSIONS: dict[str, set[str]] = {
    "policy":    {".pdf", ".docx", ".doc", ".txt", ".md"},
    "process":   {".pdf", ".docx", ".doc", ".txt", ".md"},
    "control":   {".csv", ".xlsx", ".xls"},
    "interview": {".docx", ".doc", ".txt", ".md"},
    "proof":     {".pdf", ".docx", ".doc", ".txt", ".md", ".xlsx", ".xls", ".csv"},
}


@router.post(
    "/assessments/{assessment_id}/policies/upload",
    response_model=PolicyUploadResponse,
)
async def upload_policy(
    assessment_id: uuid.UUID,
    file: UploadFile = File(...),
    name: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    version: Optional[str] = Form(None),
    owner: Optional[str] = Form(None),
    section: str = Form("policy"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_user),
):
    """Upload an evidence document.

    section: one of 'policy', 'process', 'control', 'interview', 'proof'.
    Each section restricts accepted file formats and determines document_type
    (policy/process → 'policy'; control/interview/proof → 'evidence').
    """
    if section not in _SECTION_DOCUMENT_TYPE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"section must be one of: {', '.join(_SECTION_DOCUMENT_TYPE)}",
        )

    document_type = _SECTION_DOCUMENT_TYPE[section]
    allowed_exts = _SECTION_ALLOWED_EXTENSIONS[section]

    filename = file.filename or "unknown"
    ext = Path(filename).suffix.lower()
    file_format = ext.lstrip(".") if ext else None

    if ext not in allowed_exts:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File type '{ext}' is not allowed for section '{section}'. Allowed: {', '.join(sorted(allowed_exts))}",
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
        section=section,
        file_format=file_format,
    )

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
