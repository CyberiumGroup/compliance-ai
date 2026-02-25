"""Schemas for mapping operations."""

from uuid import UUID
from typing import Literal

from pydantic import BaseModel, Field


class MappingGenerateRequest(BaseModel):
    """Request to generate AI mappings."""
    confidence_threshold: float = Field(default=0.5, ge=0.0, le=1.0)


class MappingSuggestion(BaseModel):
    """A single mapping suggestion from AI."""
    entity_type: Literal["policy"]
    entity_id: UUID
    entity_name: str
    requirement_id: UUID
    requirement_code: str
    confidence_score: float
    reasoning: str | None = None


class MappingGenerateResponse(BaseModel):
    """Response from mapping generation."""
    assessment_id: UUID
    suggestions_count: int
    policy_mappings: int
    suggestions: list[MappingSuggestion]


class MappingApproveRequest(BaseModel):
    """Request to approve or reject a mapping."""
    is_approved: bool
    notes: str | None = None


class MappingApproveResponse(BaseModel):
    """Response from mapping approval."""
    mapping_id: UUID
    mapping_type: Literal["policy"]
    is_approved: bool
    approved_at: str | None = None


class GapResponse(BaseModel):
    """A gap identified in coverage."""
    gap_type: Literal["unmapped_requirement"]
    requirement_id: UUID
    requirement_code: str
    requirement_name: str | None = None
    requirement_description: str | None = None
    framework_name: str | None = None
    parent_code: str | None = None
    policy_names: list[str] | None = None


class GapListResponse(BaseModel):
    """List of gaps with summary."""
    assessment_id: UUID
    total_requirements: int = 0
    total_gaps: int
    unmapped_requirements: int
    coverage_percentage: float
    gaps: list[GapResponse]


class BulkMappingRequest(BaseModel):
    """Request for bulk mapping operations."""
    mapping_ids: list[UUID]
    mapping_type: Literal["policy"]


class BulkMappingResult(BaseModel):
    """Result of a single mapping operation in bulk."""
    mapping_id: UUID
    success: bool
    error: str | None = None


class BulkMappingResponse(BaseModel):
    """Response from bulk mapping operations."""
    total: int
    successful: int
    failed: int
    results: list[BulkMappingResult]
