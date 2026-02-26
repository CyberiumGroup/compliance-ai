"""Schemas for assessments."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.assessment import AssessmentStatus, AssessmentDepth


class AssessmentBase(BaseModel):
    """Base schema for Assessment."""
    name: str = Field(..., max_length=255)
    description: str | None = None
    organization_name: str = Field(..., max_length=255)


class AIPromptOverrides(BaseModel):
    """Schema for AI prompt customization."""
    mapping_prompt_suffix: str | None = None
    analysis_prompt_suffix: str | None = None


class AssessmentCreate(AssessmentBase):
    """Schema for creating an Assessment."""
    depth_level: AssessmentDepth = AssessmentDepth.DESIGN
    ai_prompt_overrides: AIPromptOverrides | None = None


class AssessmentUpdate(BaseModel):
    """Schema for updating an Assessment."""
    name: str | None = Field(default=None, max_length=255)
    description: str | None = None
    organization_name: str | None = Field(default=None, max_length=255)
    status: AssessmentStatus | None = None
    depth_level: AssessmentDepth | None = None
    ai_prompt_overrides: AIPromptOverrides | None = None
    policy_mapping_threshold: float | None = Field(default=None, ge=0.0, le=100.0)
    industry: str | None = Field(default=None, max_length=255)
    business_description: str | None = None
    product_service_description: str | None = None
    information_types: str | None = None


class AssessmentResponse(AssessmentBase):
    """Schema for Assessment response."""
    id: UUID
    status: str
    depth_level: str
    ai_prompt_overrides: dict | None = None
    policy_mapping_threshold: float | None = None
    industry: str | None = None
    business_description: str | None = None
    product_service_description: str | None = None
    information_types: str | None = None
    created_by_id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class AssessmentListResponse(BaseModel):
    """Schema for list of assessments."""
    items: list[AssessmentResponse]
    total: int


class AssessmentDetailResponse(AssessmentResponse):
    """Schema for detailed assessment response."""
    controls_count: int = 0
    policies_count: int = 0
    interviews_count: int = 0
    completion_percentage: float = 0.0
