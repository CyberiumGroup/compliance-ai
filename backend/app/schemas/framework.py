"""Legacy schemas for NIST CSF 2.0 framework entities (see unified_framework.py for unified schemas)."""

from uuid import UUID

from pydantic import BaseModel, Field


class CSFSubcategoryBase(BaseModel):
    """Base schema for CSF Subcategory."""
    code: str = Field(..., max_length=20, examples=["GV.OC-01"])
    description: str


class CSFSubcategoryCreate(CSFSubcategoryBase):
    """Schema for creating a CSF Subcategory."""
    category_id: UUID


class CSFSubcategoryResponse(CSFSubcategoryBase):
    """Schema for CSF Subcategory response."""
    id: UUID
    category_id: UUID

    model_config = {"from_attributes": True}


class CSFCategoryBase(BaseModel):
    """Base schema for CSF Category."""
    code: str = Field(..., max_length=20, examples=["GV.OC"])
    name: str = Field(..., max_length=100)
    description: str | None = None


class CSFCategoryCreate(CSFCategoryBase):
    """Schema for creating a CSF Category."""
    function_id: UUID


class CSFCategoryResponse(CSFCategoryBase):
    """Schema for CSF Category response."""
    id: UUID
    function_id: UUID
    subcategories: list[CSFSubcategoryResponse] | None = None

    model_config = {"from_attributes": True}


class CSFFunctionBase(BaseModel):
    """Base schema for CSF Function."""
    code: str = Field(..., max_length=10, examples=["GV"])
    name: str = Field(..., max_length=100, examples=["GOVERN"])
    description: str | None = None


class CSFFunctionCreate(CSFFunctionBase):
    """Schema for creating a CSF Function."""
    pass


class CSFFunctionResponse(CSFFunctionBase):
    """Schema for CSF Function response."""
    id: UUID
    categories: list[CSFCategoryResponse] | None = None

    model_config = {"from_attributes": True}


class FrameworkSummary(BaseModel):
    """Summary of the CSF framework."""
    functions_count: int
    categories_count: int
    subcategories_count: int
