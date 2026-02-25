"""Mapping endpoints."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.policy import PolicyMapping
from app.models.user import User
from app.schemas.mapping import (
    MappingGenerateRequest,
    MappingGenerateResponse,
    GapListResponse,
    BulkMappingRequest,
    BulkMappingResponse,
)
from app.schemas.policy import PolicyMappingResponse
from app.dependencies.auth import get_current_user, require_user
from app.services.mapping.ai_mapper import AIMappingService
from app.services.mapping.gap_detector import GapDetectionService

router = APIRouter()


@router.post(
    "/assessments/{assessment_id}/generate",
    response_model=MappingGenerateResponse,
)
async def generate_mappings(
    assessment_id: uuid.UUID,
    request: MappingGenerateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_user),
):
    """Generate AI-powered mapping suggestions for an assessment."""
    mapper = AIMappingService(db)

    result = mapper.generate_mappings_for_assessment(
        assessment_id=assessment_id,
        user_id=current_user.id,
        confidence_threshold=request.confidence_threshold,
    )

    return MappingGenerateResponse(**result)


@router.get("/assessments/{assessment_id}/policies")
async def get_policy_mappings(
    assessment_id: uuid.UUID,
    approved_only: bool = False,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_current_user),
):
    """Get all policy mappings for an assessment."""
    from app.models.policy import Policy

    query = (
        db.query(PolicyMapping)
        .join(Policy)
        .filter(Policy.assessment_id == assessment_id)
    )

    if approved_only:
        query = query.filter(PolicyMapping.is_approved == True)

    mappings = query.all()

    return [PolicyMappingResponse.model_validate(m) for m in mappings]


@router.post("/{mapping_id}/approve")
async def approve_mapping(
    mapping_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_user),
):
    """Approve a mapping suggestion."""
    mapper = AIMappingService(db)

    result = mapper.approve_mapping(
        mapping_id=mapping_id,
        mapping_type="policy",
        approved=True,
        user_id=current_user.id,
    )

    if "error" in result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=result["error"],
        )

    return result


@router.post("/{mapping_id}/reject")
async def reject_mapping(
    mapping_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_user),
):
    """Soft-reject a mapping suggestion (marks is_rejected=True, not deleted)."""
    from datetime import datetime
    from app.services.audit.audit_service import AuditService

    mapping = db.query(PolicyMapping).filter(PolicyMapping.id == mapping_id).first()

    if not mapping:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Mapping not found",
        )

    mapping.is_rejected = True
    mapping.rejected_at = datetime.utcnow()

    audit_service = AuditService(db)
    audit_service.log_update(
        entity_type="policy_mapping",
        entity_id=mapping_id,
        old_values={"is_rejected": False},
        new_values={"is_rejected": True},
        user_id=current_user.id,
    )

    db.commit()

    return {"mapping_id": str(mapping_id), "is_rejected": True}


@router.post("/{mapping_id}/unreject")
async def unreject_mapping(
    mapping_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_user),
):
    """Unreject a mapping (moves it back to Pending: is_rejected=False)."""
    from app.services.audit.audit_service import AuditService

    mapping = db.query(PolicyMapping).filter(PolicyMapping.id == mapping_id).first()

    if not mapping:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Mapping not found",
        )

    mapping.is_rejected = False
    mapping.rejected_at = None

    audit_service = AuditService(db)
    audit_service.log_update(
        entity_type="policy_mapping",
        entity_id=mapping_id,
        old_values={"is_rejected": True},
        new_values={"is_rejected": False},
        user_id=current_user.id,
    )

    db.commit()

    return {"mapping_id": str(mapping_id), "is_rejected": False}


@router.delete("/assessments/{assessment_id}/all")
async def clear_all_mappings(
    assessment_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_user),
):
    """Delete all mappings (both approved and pending) for an assessment."""
    mapper = AIMappingService(db)
    result = mapper.clear_all_mappings(
        assessment_id=assessment_id,
        user_id=current_user.id,
    )
    return result


@router.get("/assessments/{assessment_id}/gaps", response_model=GapListResponse)
async def get_gaps(
    assessment_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_current_user),
):
    """Get coverage gaps for an assessment."""
    gap_detector = GapDetectionService(db)
    result = gap_detector.detect_gaps(assessment_id)

    return GapListResponse(**result)


@router.post("/bulk-approve", response_model=BulkMappingResponse)
async def bulk_approve_mappings(
    request: BulkMappingRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_user),
):
    """
    Bulk approve multiple mappings.

    Approves all valid mappings and reports any failures.
    """
    from datetime import datetime
    from app.services.audit.audit_service import AuditService

    results = []
    successful = 0
    failed = 0

    audit_service = AuditService(db)

    for mapping_id in request.mapping_ids:
        try:
            mapping = db.query(PolicyMapping).filter(
                PolicyMapping.id == mapping_id
            ).first()

            if not mapping:
                results.append({
                    "mapping_id": mapping_id,
                    "success": False,
                    "error": "Mapping not found",
                })
                failed += 1
                continue

            mapping.is_approved = True
            mapping.approved_by_id = current_user.id
            mapping.approved_at = datetime.utcnow()

            audit_service.log_update(
                entity_type="policy_mapping",
                entity_id=mapping_id,
                old_values={"is_approved": False},
                new_values={"is_approved": True},
                user_id=current_user.id,
            )

            results.append({
                "mapping_id": mapping_id,
                "success": True,
                "error": None,
            })
            successful += 1

        except Exception as e:
            results.append({
                "mapping_id": mapping_id,
                "success": False,
                "error": str(e),
            })
            failed += 1

    db.commit()

    return BulkMappingResponse(
        total=len(request.mapping_ids),
        successful=successful,
        failed=failed,
        results=results,
    )


@router.post("/bulk-reject", response_model=BulkMappingResponse)
async def bulk_reject_mappings(
    request: BulkMappingRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_user),
):
    """
    Bulk soft-reject multiple mappings (marks is_rejected=True, not deleted).
    """
    from datetime import datetime
    from app.services.audit.audit_service import AuditService

    results = []
    successful = 0
    failed = 0

    audit_service = AuditService(db)
    now = datetime.utcnow()

    for mapping_id in request.mapping_ids:
        try:
            mapping = db.query(PolicyMapping).filter(
                PolicyMapping.id == mapping_id
            ).first()

            if not mapping:
                results.append({
                    "mapping_id": mapping_id,
                    "success": False,
                    "error": "Mapping not found",
                })
                failed += 1
                continue

            mapping.is_rejected = True
            mapping.rejected_at = now

            audit_service.log_update(
                entity_type="policy_mapping",
                entity_id=mapping_id,
                old_values={"is_rejected": False},
                new_values={"is_rejected": True},
                user_id=current_user.id,
            )

            results.append({
                "mapping_id": mapping_id,
                "success": True,
                "error": None,
            })
            successful += 1

        except Exception as e:
            results.append({
                "mapping_id": mapping_id,
                "success": False,
                "error": str(e),
            })
            failed += 1

    db.commit()

    return BulkMappingResponse(
        total=len(request.mapping_ids),
        successful=successful,
        failed=failed,
        results=results,
    )
