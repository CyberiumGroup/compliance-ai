"""Legacy framework endpoints for NIST CSF 2.0 data (see frameworks.py for unified API)."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload

from app.db.session import get_db
from app.models.framework import CSFFunction, CSFCategory, CSFSubcategory
from app.schemas.framework import CSFFunctionResponse, FrameworkSummary
from app.services.seed_service import seed_all

router = APIRouter()


@router.get("/functions", response_model=list[CSFFunctionResponse])
async def get_functions(
    include_categories: bool = False,
    db: Session = Depends(get_db),
):
    """Get all CSF functions."""
    query = db.query(CSFFunction)

    if include_categories:
        query = query.options(
            joinedload(CSFFunction.categories).joinedload(CSFCategory.subcategories)
        )

    functions = query.all()
    return functions


@router.get("/functions/{function_code}")
async def get_function(
    function_code: str,
    include_categories: bool = True,
    db: Session = Depends(get_db),
):
    """Get a CSF function by code."""
    query = db.query(CSFFunction).filter(CSFFunction.code == function_code.upper())

    if include_categories:
        query = query.options(
            joinedload(CSFFunction.categories).joinedload(CSFCategory.subcategories)
        )

    function = query.first()

    if not function:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Function {function_code} not found",
        )

    return {
        "id": function.id,
        "code": function.code,
        "name": function.name,
        "description": function.description,
        "categories": [
            {
                "id": cat.id,
                "code": cat.code,
                "name": cat.name,
                "description": cat.description,
                "subcategories": [
                    {
                        "id": sub.id,
                        "code": sub.code,
                        "description": sub.description,
                    }
                    for sub in cat.subcategories
                ] if include_categories else None,
            }
            for cat in function.categories
        ] if include_categories else None,
    }


@router.get("/categories")
async def get_categories(
    function_code: str | None = None,
    db: Session = Depends(get_db),
):
    """Get all CSF categories, optionally filtered by function."""
    query = db.query(CSFCategory).options(joinedload(CSFCategory.function))

    if function_code:
        query = query.join(CSFFunction).filter(CSFFunction.code == function_code.upper())

    categories = query.all()

    return [
        {
            "id": cat.id,
            "code": cat.code,
            "name": cat.name,
            "description": cat.description,
            "function_code": cat.function.code,
        }
        for cat in categories
    ]


@router.get("/subcategories")
async def get_subcategories(
    category_code: str | None = None,
    function_code: str | None = None,
    db: Session = Depends(get_db),
):
    """Get all CSF subcategories, optionally filtered."""
    query = (
        db.query(CSFSubcategory)
        .options(
            joinedload(CSFSubcategory.category).joinedload(CSFCategory.function)
        )
    )

    if category_code:
        query = query.join(CSFCategory).filter(CSFCategory.code == category_code.upper())
    elif function_code:
        query = query.join(CSFCategory).join(CSFFunction).filter(
            CSFFunction.code == function_code.upper()
        )

    subcategories = query.all()

    return [
        {
            "id": sub.id,
            "code": sub.code,
            "description": sub.description,
            "category_code": sub.category.code,
            "function_code": sub.category.function.code,
        }
        for sub in subcategories
    ]


@router.get("/summary", response_model=FrameworkSummary)
async def get_framework_summary(
    db: Session = Depends(get_db),
):
    """Get a summary of the CSF framework."""
    functions_count = db.query(CSFFunction).count()
    categories_count = db.query(CSFCategory).count()
    subcategories_count = db.query(CSFSubcategory).count()

    return FrameworkSummary(
        functions_count=functions_count,
        categories_count=categories_count,
        subcategories_count=subcategories_count,
    )


@router.post("/seed")
async def seed_framework(
    db: Session = Depends(get_db),
):
    """Seed the framework with NIST CSF 2.0 data and interview questions."""
    result = seed_all(db)
    return {
        "message": "Framework data seeded successfully",
        "seeded": result,
    }
