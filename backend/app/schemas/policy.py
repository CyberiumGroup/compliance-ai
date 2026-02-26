"""Schemas for policies and policy mappings."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class PolicyBase(BaseModel):
    """Base schema for Policy."""
    name: str = Field(..., max_length=255)
    description: str | None = None
    version: str | None = Field(default=None, max_length=50)
    owner: str | None = Field(default=None, max_length=255)


class PolicyCreate(PolicyBase):
    """Schema for creating a Policy."""
    assessment_id: UUID
    file_path: str | None = None
    content_text: str | None = None


class PolicyUpdate(BaseModel):
    """Schema for updating a Policy."""
    name: str | None = Field(default=None, max_length=255)
    description: str | None = None
    version: str | None = Field(default=None, max_length=50)
    owner: str | None = Field(default=None, max_length=255)


class PolicyResponse(PolicyBase):
    """Schema for Policy response."""
    id: UUID
    assessment_id: UUID
    file_path: str | None = None
    content_text: str | None = None
    summary: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class PolicyMappingBase(BaseModel):
    """Base schema for Policy Mapping."""
    policy_id: UUID
    subcategory_id: UUID | None = None
    requirement_id: UUID | None = None
    confidence_score: float | None = Field(default=None, ge=0.0, le=1.0)


class PolicyMappingCreate(PolicyMappingBase):
    """Schema for creating a Policy Mapping."""
    pass


class PolicyMappingResponse(PolicyMappingBase):
    """Schema for Policy Mapping response."""
    id: UUID
    is_approved: bool
    approved_by_id: UUID | None = None
    approved_at: datetime | None = None
    is_rejected: bool = False
    rejected_at: datetime | None = None
    created_at: datetime
    subcategory_code: str | None = None
    requirement_code: str | None = None
    requirement_name: str | None = None
    requirement_description: str | None = None
    requirement_framework_name: str | None = None
    requirement_parent_code: str | None = None
    requirement_level: int | None = None
    requirement_ancestors: list | None = None
    requirement_guidance: str | None = None
    relevance_percentage: float | None = None
    reasoning: str | None = None
    source_excerpt: str | None = None
    policy_name: str | None = None
    policy_description: str | None = None
    policy_summary: str | None = None

    model_config = {"from_attributes": True}


class PolicyUploadResponse(BaseModel):
    """Response for policy file upload."""
    policy: PolicyResponse
    text_extracted: bool
    text_length: int | None = None
    extraction_error: str | None = None
