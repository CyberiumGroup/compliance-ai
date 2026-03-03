"""Policy endpoints."""

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.policy import Policy
from app.models.user import User
from app.schemas.policy import (
    PolicyResponse,
    PolicyUploadResponse,
)
from app.dependencies.auth import get_current_user, require_user
from app.services.ingestion.policy_ingestion import PolicyIngestionService
from app.core.config import settings

router = APIRouter()


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
    extension = "." + filename.lower().split(".")[-1]

    if extension not in settings.allowed_policy_extensions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid file type. Allowed: {settings.allowed_policy_extensions}",
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
