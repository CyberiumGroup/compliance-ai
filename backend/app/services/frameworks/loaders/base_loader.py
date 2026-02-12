"""Base class for framework loaders."""

from abc import ABC, abstractmethod
from typing import Optional
import uuid

from sqlalchemy.orm import Session

from app.models.unified_framework import (
    Framework,
    FrameworkRequirement,
    FrameworkType,
    RequirementCrosswalk,
    RequirementClusterMember,
)
from app.models.control import ControlMapping
from app.models.policy import PolicyMapping
from app.models.interview import InterviewQuestion
from app.models.score import SubcategoryScore
from app.models.deviation import Deviation


class RequirementData:
    """Data structure for a requirement to be loaded."""

    def __init__(
        self,
        code: str,
        name: str,
        description: Optional[str] = None,
        guidance: Optional[str] = None,
        level: int = 0,
        is_assessable: bool = True,
        display_order: int = 0,
        metadata: Optional[dict] = None,
        children: Optional[list["RequirementData"]] = None,
    ):
        self.code = code
        self.name = name
        self.description = description
        self.guidance = guidance
        self.level = level
        self.is_assessable = is_assessable
        self.display_order = display_order
        self.metadata = metadata or {}
        self.children = children or []


class FrameworkData:
    """Data structure for a framework to be loaded."""

    def __init__(
        self,
        code: str,
        name: str,
        version: str,
        description: Optional[str] = None,
        framework_type: FrameworkType = FrameworkType.CUSTOM,
        hierarchy_levels: int = 1,
        hierarchy_labels: Optional[list[str]] = None,
        metadata: Optional[dict] = None,
        requirements: Optional[list[RequirementData]] = None,
    ):
        self.code = code
        self.name = name
        self.version = version
        self.description = description
        self.framework_type = framework_type
        self.hierarchy_levels = hierarchy_levels
        self.hierarchy_labels = hierarchy_labels or []
        self.metadata = metadata or {}
        self.requirements = requirements or []


class BaseFrameworkLoader(ABC):
    """Abstract base class for framework loaders.

    Framework loaders are responsible for loading compliance frameworks
    into the database. Each loader implements the logic for parsing
    and transforming framework data from various sources (static data,
    files, APIs, etc.) into the unified framework structure.
    """

    @abstractmethod
    def get_framework_data(self) -> FrameworkData:
        """Get the framework data to be loaded.

        Returns:
            FrameworkData object containing the framework and its requirements.
        """
        pass

    def load(self, db: Session, force_reload: bool = False) -> Framework:
        """Load the framework into the database.

        Args:
            db: Database session
            force_reload: If True, delete existing requirements and reload from file.
                          The framework record itself is preserved to maintain FK references.

        Returns:
            The loaded Framework object
        """
        framework_data = self.get_framework_data()

        # Check if framework already exists
        existing = (
            db.query(Framework)
            .filter(Framework.code == framework_data.code)
            .first()
        )

        if existing and not force_reload:
            return existing

        if existing and force_reload:
            self._delete_framework_requirements(db, existing.id)

            # Update framework metadata from file
            existing.name = framework_data.name
            existing.version = framework_data.version
            existing.description = framework_data.description
            existing.framework_type = framework_data.framework_type.value
            existing.hierarchy_levels = framework_data.hierarchy_levels
            existing.hierarchy_labels = framework_data.hierarchy_labels
            existing.extra_metadata = framework_data.metadata
            db.flush()

            framework = existing
        else:
            # Create new framework
            framework = Framework(
                id=uuid.uuid4(),
                code=framework_data.code,
                name=framework_data.name,
                version=framework_data.version,
                description=framework_data.description,
                framework_type=framework_data.framework_type.value,
                hierarchy_levels=framework_data.hierarchy_levels,
                hierarchy_labels=framework_data.hierarchy_labels,
                extra_metadata=framework_data.metadata,
                is_active=True,
                is_builtin=True,
            )
            db.add(framework)
            db.flush()

        # Load requirements recursively
        self._load_requirements(
            db=db,
            framework_id=framework.id,
            requirements=framework_data.requirements,
            parent_id=None,
            level=0,
        )

        db.commit()
        return framework

    def _delete_framework_requirements(
        self, db: Session, framework_id: uuid.UUID
    ) -> None:
        """Delete all requirements for a framework and clean up FK references.

        Handles cascading by:
        - Deleting rows from tables with non-nullable FKs (crosswalks, cluster members)
        - Nulling out nullable FK columns (mappings, scores, interviews, deviations)
        - Clearing self-referencing parent_id before deleting requirements
        """
        req_ids = [
            r.id for r in
            db.query(FrameworkRequirement.id)
            .filter(FrameworkRequirement.framework_id == framework_id)
            .all()
        ]

        if not req_ids:
            return

        # Delete from tables with non-nullable FK to framework_requirements
        db.query(RequirementCrosswalk).filter(
            (RequirementCrosswalk.source_requirement_id.in_(req_ids))
            | (RequirementCrosswalk.target_requirement_id.in_(req_ids))
        ).delete(synchronize_session=False)

        db.query(RequirementClusterMember).filter(
            RequirementClusterMember.requirement_id.in_(req_ids)
        ).delete(synchronize_session=False)

        # Null out nullable FK columns in dependent tables
        db.query(ControlMapping).filter(
            ControlMapping.requirement_id.in_(req_ids)
        ).update({ControlMapping.requirement_id: None}, synchronize_session=False)

        db.query(PolicyMapping).filter(
            PolicyMapping.requirement_id.in_(req_ids)
        ).update({PolicyMapping.requirement_id: None}, synchronize_session=False)

        db.query(InterviewQuestion).filter(
            InterviewQuestion.requirement_id.in_(req_ids)
        ).update({InterviewQuestion.requirement_id: None}, synchronize_session=False)

        db.query(SubcategoryScore).filter(
            SubcategoryScore.requirement_id.in_(req_ids)
        ).update({SubcategoryScore.requirement_id: None}, synchronize_session=False)

        db.query(Deviation).filter(
            Deviation.requirement_id.in_(req_ids)
        ).update({Deviation.requirement_id: None}, synchronize_session=False)

        # Clear self-referencing parent_id, then delete all requirements
        db.query(FrameworkRequirement).filter(
            FrameworkRequirement.framework_id == framework_id
        ).update({FrameworkRequirement.parent_id: None}, synchronize_session=False)

        db.query(FrameworkRequirement).filter(
            FrameworkRequirement.framework_id == framework_id
        ).delete(synchronize_session=False)

        db.flush()

    def _load_requirements(
        self,
        db: Session,
        framework_id: uuid.UUID,
        requirements: list[RequirementData],
        parent_id: Optional[uuid.UUID],
        level: int,
    ) -> None:
        """Recursively load requirements into the database.

        Args:
            db: Database session
            framework_id: ID of the parent framework
            requirements: List of requirements to load
            parent_id: ID of the parent requirement (None for root)
            level: Current hierarchy level
        """
        for order, req_data in enumerate(requirements):
            requirement = FrameworkRequirement(
                id=uuid.uuid4(),
                framework_id=framework_id,
                parent_id=parent_id,
                code=req_data.code,
                name=req_data.name,
                description=req_data.description,
                guidance=req_data.guidance,
                level=level,
                is_assessable=req_data.is_assessable,
                display_order=req_data.display_order or order,
                extra_metadata=req_data.metadata,
            )
            db.add(requirement)
            db.flush()

            # Recursively load children
            if req_data.children:
                self._load_requirements(
                    db=db,
                    framework_id=framework_id,
                    requirements=req_data.children,
                    parent_id=requirement.id,
                    level=level + 1,
                )

    @staticmethod
    def get_loader(framework_type: str) -> "BaseFrameworkLoader":
        """Factory method to get the appropriate loader for a framework type.

        Args:
            framework_type: The type of framework (nist_csf, iso_27001, soc2_tsc, custom)

        Returns:
            The appropriate loader instance

        Raises:
            ValueError: If framework type is not supported
        """
        from app.services.frameworks.loaders.nist_csf_loader import NistCsfLoader
        from app.services.frameworks.loaders.iso27001_loader import Iso27001Loader
        from app.services.frameworks.loaders.soc2_loader import Soc2Loader

        loaders = {
            "nist_csf": NistCsfLoader,
            "iso_27001": Iso27001Loader,
            "soc2_tsc": Soc2Loader,
        }

        if framework_type not in loaders:
            raise ValueError(f"Unsupported framework type: {framework_type}")

        return loaders[framework_type]()
