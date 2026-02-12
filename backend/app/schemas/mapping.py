"""Schemas for mapping operations."""

from uuid import UUID
from typing import Literal

from pydantic import BaseModel, Field


class MappingGenerateRequest(BaseModel):
    """Request to generate AI mappings."""
    include_policies: bool = True
    include_controls: bool = True
    confidence_threshold: float = Field(default=0.5, ge=0.0, le=1.0)


class MappingSuggestion(BaseModel):
    """A single mapping suggestion from AI."""
    entity_type: Literal["policy", "control"]
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
    control_mappings: int
    suggestions: list[MappingSuggestion]


class MappingApproveRequest(BaseModel):
    """Request to approve or reject a mapping."""
    is_approved: bool
    notes: str | None = None


class MappingApproveResponse(BaseModel):
    """Response from mapping approval."""
    mapping_id: UUID
    mapping_type: Literal["policy", "control"]
    is_approved: bool
    approved_at: str | None = None


class GapResponse(BaseModel):
    """A gap identified in coverage."""
    gap_type: Literal["unmapped_subcategory", "policy_only", "control_only"]
    subcategory_id: UUID
    subcategory_code: str
    subcategory_description: str
    function_code: str
    category_code: str
    has_policy: bool
    has_control: bool
    policy_names: list[str] | None = None
    control_names: list[str] | None = None


class GapListResponse(BaseModel):
    """List of gaps with summary."""
    assessment_id: UUID
    total_gaps: int
    unmapped_subcategories: int
    policy_only_count: int
    control_only_count: int
    coverage_percentage: float
    gaps: list[GapResponse]


class BulkMappingRequest(BaseModel):
    """Request for bulk mapping operations."""
    mapping_ids: list[UUID]
    mapping_type: Literal["policy", "control"]


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
