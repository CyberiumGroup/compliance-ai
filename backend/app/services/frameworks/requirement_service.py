"""Service for managing framework requirements."""

import uuid
from typing import Optional

from sqlalchemy.orm import Session, joinedload

from app.models.unified_framework import (
    Framework,
    FrameworkRequirement,
    AssessmentFrameworkScope,
)


class RequirementService:
    """Service for managing framework requirements."""

    def __init__(self, db: Session):
        self.db = db

    def get_requirement(
        self,
        requirement_id: uuid.UUID,
    ) -> Optional[FrameworkRequirement]:
        """Get a requirement by ID.

        Args:
            requirement_id: The requirement's UUID

        Returns:
            FrameworkRequirement or None if not found
        """
        return (
            self.db.query(FrameworkRequirement)
            .filter(FrameworkRequirement.id == requirement_id)
            .first()
        )

    def get_requirement_by_code(
        self,
        framework_id: uuid.UUID,
        code: str,
    ) -> Optional[FrameworkRequirement]:
        """Get a requirement by its code within a framework.

        Args:
            framework_id: The framework's UUID
            code: The requirement code

        Returns:
            FrameworkRequirement or None if not found
        """
        return (
            self.db.query(FrameworkRequirement)
            .filter(
                FrameworkRequirement.framework_id == framework_id,
                FrameworkRequirement.code == code,
            )
            .first()
        )

    def list_requirements(
        self,
        framework_id: uuid.UUID,
        parent_id: Optional[uuid.UUID] = None,
        level: Optional[int] = None,
        is_assessable: Optional[bool] = None,
    ) -> list[FrameworkRequirement]:
        """List requirements with optional filters.

        Args:
            framework_id: The framework's UUID
            parent_id: Filter by parent (None for root level, or specific parent)
            level: Filter by hierarchy level
            is_assessable: Filter by assessable status

        Returns:
            List of FrameworkRequirement objects
        """
        query = self.db.query(FrameworkRequirement).filter(
            FrameworkRequirement.framework_id == framework_id
        )

        if parent_id is not None:
            query = query.filter(FrameworkRequirement.parent_id == parent_id)
        elif level == 0:
            # Root level requirements have no parent
            query = query.filter(FrameworkRequirement.parent_id.is_(None))

        if level is not None:
            query = query.filter(FrameworkRequirement.level == level)

        if is_assessable is not None:
            query = query.filter(FrameworkRequirement.is_assessable == is_assessable)

        return query.order_by(FrameworkRequirement.display_order).all()

    def get_root_requirements(
        self,
        framework_id: uuid.UUID,
    ) -> list[FrameworkRequirement]:
        """Get top-level requirements for a framework.

        Args:
            framework_id: The framework's UUID

        Returns:
            List of root-level FrameworkRequirement objects
        """
        return self.list_requirements(framework_id, level=0)

    def get_assessable_requirements(
        self,
        framework_id: uuid.UUID,
    ) -> list[FrameworkRequirement]:
        """Get all assessable requirements for a framework.

        Args:
            framework_id: The framework's UUID

        Returns:
            List of assessable FrameworkRequirement objects
        """
        return self.list_requirements(framework_id, is_assessable=True)

    def get_children(
        self,
        requirement_id: uuid.UUID,
    ) -> list[FrameworkRequirement]:
        """Get direct children of a requirement.

        Args:
            requirement_id: The parent requirement's UUID

        Returns:
            List of child FrameworkRequirement objects
        """
        return (
            self.db.query(FrameworkRequirement)
            .filter(FrameworkRequirement.parent_id == requirement_id)
            .order_by(FrameworkRequirement.display_order)
            .all()
        )

    def get_ancestors(
        self,
        requirement_id: uuid.UUID,
    ) -> list[FrameworkRequirement]:
        """Get all ancestors of a requirement (parent, grandparent, etc.).

        Args:
            requirement_id: The requirement's UUID

        Returns:
            List of ancestor requirements, from root to immediate parent
        """
        ancestors = []
        current = self.get_requirement(requirement_id)

        while current and current.parent_id:
            parent = self.get_requirement(current.parent_id)
            if parent:
                ancestors.insert(0, parent)
            current = parent

        return ancestors

    def get_requirement_path(
        self,
        requirement_id: uuid.UUID,
    ) -> str:
        """Get the full path of a requirement (e.g., "GV > GV.OC > GV.OC-01").

        Args:
            requirement_id: The requirement's UUID

        Returns:
            String representation of the requirement path
        """
        requirement = self.get_requirement(requirement_id)
        if not requirement:
            return ""

        ancestors = self.get_ancestors(requirement_id)
        path_parts = [a.code for a in ancestors] + [requirement.code]
        return " > ".join(path_parts)

    def get_hierarchy_tree(
        self,
        framework_id: uuid.UUID,
        max_depth: Optional[int] = None,
    ) -> list[dict]:
        """Get the full requirement hierarchy as a nested tree.

        Args:
            framework_id: The framework's UUID
            max_depth: Maximum depth to traverse (None for full tree)

        Returns:
            List of dictionaries with requirement data and nested children
        """

        def build_node(req: FrameworkRequirement, depth: int) -> dict:
            node = {
                "id": str(req.id),
                "code": req.code,
                "name": req.name,
                "description": req.description,
                "level": req.level,
                "is_assessable": req.is_assessable,
                "metadata": req.extra_metadata,
            }

            if max_depth is None or depth < max_depth:
                children = self.get_children(req.id)
                if children:
                    node["children"] = [
                        build_node(child, depth + 1) for child in children
                    ]

            return node

        roots = self.get_root_requirements(framework_id)
        return [build_node(root, 0) for root in roots]

    def get_requirements_in_scope(
        self,
        assessment_id: uuid.UUID,
    ) -> list[FrameworkRequirement]:
        """Get all requirements in scope for an assessment.

        Args:
            assessment_id: The assessment's UUID

        Returns:
            List of FrameworkRequirement objects in scope
        """
        scopes = (
            self.db.query(AssessmentFrameworkScope)
            .filter(AssessmentFrameworkScope.assessment_id == assessment_id)
            .all()
        )

        if not scopes:
            return []

        requirements = []
        for scope in scopes:
            framework_reqs = self.get_assessable_requirements(scope.framework_id)

            if scope.include_all:
                # Include all, minus exclusions
                excluded = set(scope.excluded_requirement_ids or [])
                requirements.extend(
                    req for req in framework_reqs
                    if str(req.id) not in excluded
                )
            else:
                # Include only specified requirements
                included = set(scope.included_requirement_ids or [])
                requirements.extend(
                    req for req in framework_reqs
                    if str(req.id) in included
                )

        return requirements

    def get_requirements_by_framework_in_scope(
        self,
        assessment_id: uuid.UUID,
    ) -> dict[str, list[FrameworkRequirement]]:
        """Get requirements in scope grouped by framework.

        Args:
            assessment_id: The assessment's UUID

        Returns:
            Dictionary mapping framework codes to lists of requirements
        """
        scopes = (
            self.db.query(AssessmentFrameworkScope)
            .options(joinedload(AssessmentFrameworkScope.framework))
            .filter(AssessmentFrameworkScope.assessment_id == assessment_id)
            .all()
        )

        result = {}
        for scope in scopes:
            framework = scope.framework
            framework_reqs = self.get_assessable_requirements(scope.framework_id)

            if scope.include_all:
                excluded = set(scope.excluded_requirement_ids or [])
                reqs = [
                    req for req in framework_reqs
                    if str(req.id) not in excluded
                ]
            else:
                included = set(scope.included_requirement_ids or [])
                reqs = [
                    req for req in framework_reqs
                    if str(req.id) in included
                ]

            result[framework.code] = reqs

        return result

    def create_requirement(
        self,
        framework_id: uuid.UUID,
        code: str,
        name: str,
        parent_id: Optional[uuid.UUID] = None,
        description: Optional[str] = None,
        guidance: Optional[str] = None,
        is_assessable: bool = True,
        display_order: int = 0,
        metadata: Optional[dict] = None,
    ) -> FrameworkRequirement:
        """Create a new requirement.

        Args:
            framework_id: The framework's UUID
            code: Unique code within the framework
            name: Requirement name
            parent_id: Parent requirement's UUID (None for root)
            description: Requirement description
            guidance: Implementation guidance
            is_assessable: Whether this requirement can be assessed
            display_order: Order within siblings
            metadata: Additional metadata

        Returns:
            The created FrameworkRequirement
        """
        # Determine level from parent
        level = 0
        if parent_id:
            parent = self.get_requirement(parent_id)
            if parent:
                level = parent.level + 1

        requirement = FrameworkRequirement(
            id=uuid.uuid4(),
            framework_id=framework_id,
            parent_id=parent_id,
            code=code,
            name=name,
            description=description,
            guidance=guidance,
            level=level,
            is_assessable=is_assessable,
            display_order=display_order,
            metadata=metadata,
        )
        self.db.add(requirement)
        self.db.commit()
        return requirement

    def update_requirement(
        self,
        requirement_id: uuid.UUID,
        name: Optional[str] = None,
        description: Optional[str] = None,
        guidance: Optional[str] = None,
        is_assessable: Optional[bool] = None,
        display_order: Optional[int] = None,
        metadata: Optional[dict] = None,
    ) -> Optional[FrameworkRequirement]:
        """Update a requirement.

        Args:
            requirement_id: The requirement's UUID
            name: New name (optional)
            description: New description (optional)
            guidance: New guidance (optional)
            is_assessable: New assessable status (optional)
            display_order: New display order (optional)
            metadata: New metadata (merged with existing)

        Returns:
            Updated FrameworkRequirement or None if not found
        """
        requirement = self.get_requirement(requirement_id)
        if not requirement:
            return None

        if name is not None:
            requirement.name = name
        if description is not None:
            requirement.description = description
        if guidance is not None:
            requirement.guidance = guidance
        if is_assessable is not None:
            requirement.is_assessable = is_assessable
        if display_order is not None:
            requirement.display_order = display_order
        if metadata is not None:
            requirement.extra_metadata = {**(requirement.extra_metadata or {}), **metadata}

        self.db.commit()
        return requirement

    def delete_requirement(
        self,
        requirement_id: uuid.UUID,
        cascade: bool = True,
    ) -> bool:
        """Delete a requirement.

        Args:
            requirement_id: The requirement's UUID
            cascade: If True, also delete all children

        Returns:
            True if deleted, False if not found
        """
        requirement = self.get_requirement(requirement_id)
        if not requirement:
            return False

        if cascade:
            # Recursively delete children first
            children = self.get_children(requirement_id)
            for child in children:
                self.delete_requirement(child.id, cascade=True)

        self.db.delete(requirement)
        self.db.commit()
        return True

    def search_requirements(
        self,
        query: str,
        framework_id: Optional[uuid.UUID] = None,
        is_assessable: Optional[bool] = None,
        limit: int = 50,
    ) -> list[FrameworkRequirement]:
        """Search requirements by code, name, or description.

        Args:
            query: Search query string
            framework_id: Optionally filter by framework
            is_assessable: Optionally filter by assessable status
            limit: Maximum number of results

        Returns:
            List of matching FrameworkRequirement objects
        """
        search_query = self.db.query(FrameworkRequirement).filter(
            (FrameworkRequirement.code.ilike(f"%{query}%")) |
            (FrameworkRequirement.name.ilike(f"%{query}%")) |
            (FrameworkRequirement.description.ilike(f"%{query}%"))
        )

        if framework_id:
            search_query = search_query.filter(
                FrameworkRequirement.framework_id == framework_id
            )

        if is_assessable is not None:
            search_query = search_query.filter(
                FrameworkRequirement.is_assessable == is_assessable
            )

        return search_query.limit(limit).all()

    def count_requirements(
        self,
        framework_id: uuid.UUID,
        is_assessable: Optional[bool] = None,
    ) -> int:
        """Count requirements in a framework.

        Args:
            framework_id: The framework's UUID
            is_assessable: Optionally filter by assessable status

        Returns:
            Number of requirements
        """
        query = self.db.query(FrameworkRequirement).filter(
            FrameworkRequirement.framework_id == framework_id
        )

        if is_assessable is not None:
            query = query.filter(FrameworkRequirement.is_assessable == is_assessable)

        return query.count()
