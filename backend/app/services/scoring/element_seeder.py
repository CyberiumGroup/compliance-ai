"""Loads pre-generated Phase 1 requirement elements from a JSON file into the database.

Elements are seeded once when a framework is loaded (not generated on-demand via LLM).
Each framework that supports scoring must have a corresponding elements JSON file.
"""

import json
import logging
import uuid
from pathlib import Path

from sqlalchemy.orm import Session

from app.models.scoring_job import RequirementElement
from app.models.unified_framework import Framework, FrameworkRequirement

logger = logging.getLogger(__name__)

# Maps framework_type string (used by the loader) to its elements JSON file name.
# Add new entries here as more frameworks get pre-generated element data.
FRAMEWORK_ELEMENT_FILES: dict[str, str] = {
    "nist_csf": "csf_2_0_elements.json",
}


def seed_requirement_elements(db: Session, framework: Framework, json_path: Path) -> int:
    """Load Phase 1 requirement elements from a JSON file into the database.

    Matches JSON entries to DB requirements by code. Requirements that already
    have elements are skipped (idempotent). JSON entries with no matching DB
    requirement are skipped with a debug log.

    JSON structure expected:
        [
          {
            "requirement_id": "GV.OC-01",   <- matches FrameworkRequirement.code
            "elements": [
              { "element_id": "GV.OC-01-E1", "element_text": "..." },
              ...
            ]
          },
          ...
        ]

    Returns:
        Number of requirements for which elements were seeded.
    """
    with open(json_path, encoding="utf-8") as f:
        data: list[dict] = json.load(f)

    # Build code -> requirement_id map for all assessable requirements in this framework
    reqs = (
        db.query(FrameworkRequirement)
        .filter(
            FrameworkRequirement.framework_id == framework.id,
            FrameworkRequirement.is_assessable == True,  # noqa: E712
        )
        .all()
    )
    code_to_req_id: dict[str, uuid.UUID] = {r.code: r.id for r in reqs}

    # Find requirements that already have elements (skip to stay idempotent)
    existing_req_ids: set[uuid.UUID] = set(
        row.requirement_id
        for row in db.query(RequirementElement.requirement_id)
        .filter(RequirementElement.requirement_id.in_(list(code_to_req_id.values())))
        .all()
    )

    seeded = 0
    skipped_no_match = 0
    skipped_existing = 0

    for entry in data:
        code = entry.get("requirement_id")
        req_id = code_to_req_id.get(code)

        if req_id is None:
            skipped_no_match += 1
            logger.debug("No DB requirement found for code %s — skipping", code)
            continue

        if req_id in existing_req_ids:
            skipped_existing += 1
            continue

        for elem in entry.get("elements", []):
            db.add(RequirementElement(
                id=uuid.uuid4(),
                requirement_id=req_id,
                element_id=elem["element_id"],
                description=elem["element_text"],
            ))

        seeded += 1

    db.commit()

    logger.info(
        "Seeded elements for %d/%d requirements in framework '%s' "
        "(skipped: %d no DB match, %d already had elements)",
        seeded, len(reqs), framework.code, skipped_no_match, skipped_existing,
    )
    return seeded


def get_elements_json_path(framework_type: str) -> Path | None:
    """Return the Path to the elements JSON file for a given framework type, or None."""
    filename = FRAMEWORK_ELEMENT_FILES.get(framework_type)
    if not filename:
        return None
    data_dir = Path(__file__).parent.parent.parent / "data"
    path = data_dir / filename
    return path if path.exists() else None
