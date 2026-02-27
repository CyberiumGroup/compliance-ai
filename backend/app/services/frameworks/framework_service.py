"""Service for managing compliance frameworks."""

import uuid
from typing import Optional

from sqlalchemy.orm import Session

from app.models.unified_framework import (
    Framework,
    FrameworkType,
    FrameworkRequirement,
    CompanyFramework,
    AssessmentFrameworkScope,
)
from app.services.frameworks.loaders.base_loader import BaseFrameworkLoader


class FrameworkService:
    """Service for managing compliance frameworks."""

    def __init__(self, db: Session):
        self.db = db

    def list_frameworks(
        self,
        is_active: Optional[bool] = True,
        framework_type: Optional[str] = None,
    ) -> list[Framework]:
        """List all frameworks with optional filters.

        Args:
            is_active: Filter by active status (None for all)
            framework_type: Filter by framework type

        Returns:
            List of Framework objects
        """
        query = self.db.query(Framework)

        if is_active is not None:
            query = query.filter(Framework.is_active == is_active)

        if framework_type:
            query = query.filter(Framework.framework_type == framework_type)

        return query.order_by(Framework.name).all()

    def get_framework(self, framework_id: uuid.UUID) -> Optional[Framework]:
        """Get a framework by ID.

        Args:
            framework_id: The framework's UUID

        Returns:
            Framework object or None if not found
        """
        return self.db.query(Framework).filter(Framework.id == framework_id).first()

    def get_framework_by_code(self, code: str) -> Optional[Framework]:
        """Get a framework by its code.

        Args:
            code: The framework code (e.g., "NIST-CSF-2.0")

        Returns:
            Framework object or None if not found
        """
        return self.db.query(Framework).filter(Framework.code == code).first()

    def create_custom_framework(
        self,
        code: str,
        name: str,
        version: str,
        description: Optional[str] = None,
        hierarchy_levels: int = 1,
        hierarchy_labels: Optional[list[str]] = None,
        metadata: Optional[dict] = None,
    ) -> Framework:
        """Create a new custom framework.

        Args:
            code: Unique framework code
            name: Framework name
            version: Framework version
            description: Optional description
            hierarchy_levels: Number of hierarchy levels
            hierarchy_labels: Labels for each level
            metadata: Additional metadata

        Returns:
            The created Framework object
        """
        framework = Framework(
            id=uuid.uuid4(),
            code=code,
            name=name,
            version=version,
            description=description,
            framework_type=FrameworkType.CUSTOM.value,
            hierarchy_levels=hierarchy_levels,
            hierarchy_labels=hierarchy_labels,
            metadata=metadata,
            is_active=True,
            is_builtin=False,
        )
        self.db.add(framework)
        self.db.commit()
        return framework

    def update_framework(
        self,
        framework_id: uuid.UUID,
        name: Optional[str] = None,
        description: Optional[str] = None,
        is_active: Optional[bool] = None,
        metadata: Optional[dict] = None,
    ) -> Optional[Framework]:
        """Update a framework.

        Args:
            framework_id: The framework's UUID
            name: New name (optional)
            description: New description (optional)
            is_active: New active status (optional)
            metadata: New metadata (merged with existing)

        Returns:
            Updated Framework or None if not found
        """
        framework = self.get_framework(framework_id)
        if not framework:
            return None

        if name is not None:
            framework.name = name
        if description is not None:
            framework.description = description
        if is_active is not None:
            framework.is_active = is_active
        if metadata is not None:
            framework.extra_metadata = {**(framework.extra_metadata or {}), **metadata}

        self.db.commit()
        return framework

    def delete_framework(self, framework_id: uuid.UUID) -> bool:
        """Delete a custom framework.

        Built-in frameworks cannot be deleted (use deactivate instead).

        Args:
            framework_id: The framework's UUID

        Returns:
            True if deleted, False if not found or not deletable
        """
        framework = self.get_framework(framework_id)
        if not framework or framework.is_builtin:
            return False

        # Delete associated requirements first
        self.db.query(FrameworkRequirement).filter(
            FrameworkRequirement.framework_id == framework_id
        ).delete()

        self.db.delete(framework)
        self.db.commit()
        return True

    def load_builtin_framework(
        self,
        framework_type: str,
        force_reload: bool = False,
    ) -> Framework:
        """Load a built-in framework using its loader and seed Phase 1 elements if available.

        Args:
            framework_type: Type of framework (nist_csf, iso_27001, soc2_tsc)
            force_reload: If True, delete and reload existing framework

        Returns:
            The loaded Framework object
        """
        loader = BaseFrameworkLoader.get_loader(framework_type)
        framework = loader.load(self.db, force_reload=force_reload)

        # Seed pre-generated Phase 1 requirement elements if a data file exists.
        # On force_reload the old requirements are CASCADE-deleted so elements are
        # automatically wiped; the seeder will re-insert them fresh.
        from app.services.scoring.element_seeder import get_elements_json_path, seed_requirement_elements
        json_path = get_elements_json_path(framework_type)
        if json_path:
            seed_requirement_elements(self.db, framework, json_path)

        return framework

    def load_all_builtin_frameworks(
        self,
        force_reload: bool = False,
    ) -> list[Framework]:
        """Load all built-in frameworks.

        Args:
            force_reload: If True, delete and reload existing frameworks

        Returns:
            List of loaded Framework objects
        """
        frameworks = []
        for framework_type in ["nist_csf", "iso_27001", "soc2_tsc"]:
            framework = self.load_builtin_framework(framework_type, force_reload)
            frameworks.append(framework)
        return frameworks

    def get_company_frameworks(
        self,
        organization_name: str,
        is_active: Optional[bool] = True,
    ) -> list[CompanyFramework]:
        """Get frameworks selected by a company.

        Args:
            organization_name: The company's name
            is_active: Filter by active status

        Returns:
            List of CompanyFramework objects
        """
        query = self.db.query(CompanyFramework).filter(
            CompanyFramework.organization_name == organization_name
        )

        if is_active is not None:
            query = query.filter(CompanyFramework.is_active == is_active)

        return query.order_by(CompanyFramework.priority).all()

    def add_company_framework(
        self,
        organization_name: str,
        framework_id: uuid.UUID,
        priority: int = 0,
        notes: Optional[str] = None,
    ) -> CompanyFramework:
        """Add a framework to a company's selection.

        Args:
            organization_name: The company's name
            framework_id: The framework to add
            priority: Priority order (lower = higher priority)
            notes: Optional notes

        Returns:
            The created CompanyFramework object
        """
        # Check if already exists
        existing = self.db.query(CompanyFramework).filter(
            CompanyFramework.organization_name == organization_name,
            CompanyFramework.framework_id == framework_id,
        ).first()

        if existing:
            existing.is_active = True
            existing.priority = priority
            if notes:
                existing.notes = notes
            self.db.commit()
            return existing

        company_framework = CompanyFramework(
            id=uuid.uuid4(),
            organization_name=organization_name,
            framework_id=framework_id,
            is_active=True,
            priority=priority,
            notes=notes,
        )
        self.db.add(company_framework)
        self.db.commit()
        return company_framework

    def remove_company_framework(
        self,
        organization_name: str,
        framework_id: uuid.UUID,
    ) -> bool:
        """Remove a framework from a company's selection.

        Args:
            organization_name: The company's name
            framework_id: The framework to remove

        Returns:
            True if removed, False if not found
        """
        result = self.db.query(CompanyFramework).filter(
            CompanyFramework.organization_name == organization_name,
            CompanyFramework.framework_id == framework_id,
        ).delete()

        self.db.commit()
        return result > 0

    def get_assessment_scope(
        self,
        assessment_id: uuid.UUID,
    ) -> list[AssessmentFrameworkScope]:
        """Get the framework scope for an assessment.

        Args:
            assessment_id: The assessment's UUID

        Returns:
            List of AssessmentFrameworkScope objects
        """
        return self.db.query(AssessmentFrameworkScope).filter(
            AssessmentFrameworkScope.assessment_id == assessment_id
        ).all()

    def set_assessment_scope(
        self,
        assessment_id: uuid.UUID,
        framework_id: uuid.UUID,
        include_all: bool = True,
        excluded_requirement_ids: Optional[list[str]] = None,
        included_requirement_ids: Optional[list[str]] = None,
    ) -> AssessmentFrameworkScope:
        """Set the scope for a framework in an assessment.

        Args:
            assessment_id: The assessment's UUID
            framework_id: The framework's UUID
            include_all: Whether to include all requirements
            excluded_requirement_ids: List of requirement IDs to exclude
            included_requirement_ids: List of requirement IDs to include

        Returns:
            The created/updated AssessmentFrameworkScope object
        """
        existing = self.db.query(AssessmentFrameworkScope).filter(
            AssessmentFrameworkScope.assessment_id == assessment_id,
            AssessmentFrameworkScope.framework_id == framework_id,
        ).first()

        if existing:
            existing.include_all = include_all
            existing.excluded_requirement_ids = excluded_requirement_ids
            existing.included_requirement_ids = included_requirement_ids
            self.db.commit()
            return existing

        scope = AssessmentFrameworkScope(
            id=uuid.uuid4(),
            assessment_id=assessment_id,
            framework_id=framework_id,
            include_all=include_all,
            excluded_requirement_ids=excluded_requirement_ids,
            included_requirement_ids=included_requirement_ids,
        )
        self.db.add(scope)
        self.db.commit()
        return scope

    def remove_assessment_scope(
        self,
        assessment_id: uuid.UUID,
        framework_id: uuid.UUID,
    ) -> bool:
        """Remove a framework from an assessment's scope.

        Args:
            assessment_id: The assessment's UUID
            framework_id: The framework's UUID

        Returns:
            True if removed, False if not found
        """
        result = self.db.query(AssessmentFrameworkScope).filter(
            AssessmentFrameworkScope.assessment_id == assessment_id,
            AssessmentFrameworkScope.framework_id == framework_id,
        ).delete()

        self.db.commit()
        return result > 0

    def get_framework_stats(self, framework_id: uuid.UUID) -> dict:
        """Get statistics about a framework.

        Args:
            framework_id: The framework's UUID

        Returns:
            Dictionary with framework statistics
        """
        framework = self.get_framework(framework_id)
        if not framework:
            return {}

        total = self.db.query(FrameworkRequirement).filter(
            FrameworkRequirement.framework_id == framework_id
        ).count()

        assessable = self.db.query(FrameworkRequirement).filter(
            FrameworkRequirement.framework_id == framework_id,
            FrameworkRequirement.is_assessable == True,
        ).count()

        by_level = {}
        for level in range(framework.hierarchy_levels):
            count = self.db.query(FrameworkRequirement).filter(
                FrameworkRequirement.framework_id == framework_id,
                FrameworkRequirement.level == level,
            ).count()
            label = (
                framework.hierarchy_labels[level]
                if framework.hierarchy_labels and level < len(framework.hierarchy_labels)
                else f"Level {level}"
            )
            by_level[label] = count

        return {
            "framework_id": str(framework_id),
            "framework_code": framework.code,
            "framework_name": framework.name,
            "total_requirements": total,
            "assessable_requirements": assessable,
            "requirements_by_level": by_level,
        }
