"""Schemas for controls and control mappings."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class ControlBase(BaseModel):
    """Base schema for Control."""
    identifier: str = Field(..., max_length=100)
    name: str = Field(..., max_length=255)
    description: str | None = None
    owner: str | None = Field(default=None, max_length=255)
    control_type: str | None = Field(default=None, max_length=100)
    implementation_status: str | None = Field(default=None, max_length=50)


class ControlCreate(ControlBase):
    """Schema for creating a Control."""
    assessment_id: UUID


class ControlUpdate(BaseModel):
    """Schema for updating a Control."""
    identifier: str | None = Field(default=None, max_length=100)
    name: str | None = Field(default=None, max_length=255)
    description: str | None = None
    owner: str | None = Field(default=None, max_length=255)
    control_type: str | None = Field(default=None, max_length=100)
    implementation_status: str | None = Field(default=None, max_length=50)


class ControlResponse(ControlBase):
    """Schema for Control response."""
    id: UUID
    assessment_id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ControlMappingBase(BaseModel):
    """Base schema for Control Mapping."""
    control_id: UUID
    subcategory_id: UUID | None = None
    requirement_id: UUID | None = None
    confidence_score: float | None = Field(default=None, ge=0.0, le=1.0)


class ControlMappingCreate(ControlMappingBase):
    """Schema for creating a Control Mapping."""
    pass


class ControlMappingResponse(ControlMappingBase):
    """Schema for Control Mapping response."""
    id: UUID
    is_approved: bool
    approved_by_id: UUID | None = None
    approved_at: datetime | None = None
    created_at: datetime
    subcategory_code: str | None = None
    requirement_code: str | None = None
    requirement_name: str | None = None
    requirement_description: str | None = None
    requirement_framework_name: str | None = None
    requirement_parent_code: str | None = None
    reasoning: str | None = None
    control_name: str | None = None
    control_description: str | None = None

    model_config = {"from_attributes": True}


class ControlUploadResponse(BaseModel):
    """Response for control file upload."""
    total_rows: int
    successful: int
    failed: int
    errors: list[dict] | None = None
    controls: list[ControlResponse]


class ControlUploadError(BaseModel):
    """Error detail for control upload."""
    row: int
    field: str | None = None
    message: str
