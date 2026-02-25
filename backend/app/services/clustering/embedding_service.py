"""Service for generating and managing embeddings for requirements."""

import uuid
from typing import Optional

from sqlalchemy.orm import Session
from tenacity import retry, stop_after_attempt, wait_exponential

from app.core.config import settings
from app.models.unified_framework import FrameworkRequirement


class EmbeddingService:
    """Service for generating text embeddings.

    Uses OpenAI's text-embedding-3-small model (or configured alternative)
    to generate vector embeddings for requirements and other text content.
    """

    def __init__(self, db: Optional[Session] = None):
        self.db = db
        self._client = None

    @property
    def client(self):
        """Lazy initialization of OpenAI client."""
        if self._client is None:
            if not settings.openai_api_key:
                raise ValueError("OPENAI_API_KEY not configured")
            from openai import OpenAI
            self._client = OpenAI(api_key=settings.openai_api_key)
        return self._client

    def prepare_requirement_text(self, requirement: FrameworkRequirement) -> str:
        """Prepare text for embedding from a requirement.

        Combines parent category context, code, name, description, and guidance
        into a single text optimized for semantic similarity matching.

        The immediate parent's code, name, and description are prepended to
        anchor the requirement within its broader topic domain. Only the immediate
        parent is included (not grandparent) to avoid over-generalisation.

        Args:
            requirement: The FrameworkRequirement to prepare text for

        Returns:
            Combined text string for embedding
        """
        parts = []

        # Prepend immediate parent context (e.g. category level for NIST CSF subcategories)
        if requirement.parent:
            parent = requirement.parent
            parent_label = f"{parent.code}: {parent.name}"
            if parent.description:
                parent_label += f" — {parent.description}"
            parts.append(parent_label)

        parts.append(requirement.code)

        if requirement.name and requirement.name != requirement.code:
            parts.append(requirement.name)

        if requirement.description:
            parts.append(requirement.description)

        if requirement.guidance:
            parts.append(f"Implementation guidance: {requirement.guidance}")

        return " | ".join(parts)

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
    )
    def generate_embedding(self, text: str) -> list[float]:
        """Generate an embedding vector for the given text.

        Args:
            text: The text to generate an embedding for

        Returns:
            List of floats representing the embedding vector
        """
        # Truncate text if too long (OpenAI has 8191 token limit)
        # Rough estimate: 4 chars per token
        max_chars = 8000 * 4
        if len(text) > max_chars:
            text = text[:max_chars]

        response = self.client.embeddings.create(
            model=settings.embedding_model,
            input=text,
            dimensions=settings.embedding_dimensions,
        )

        return response.data[0].embedding

    def generate_embeddings_batch(
        self,
        texts: list[str],
        batch_size: int = 100,
    ) -> list[list[float]]:
        """Generate embeddings for multiple texts in batches.

        Args:
            texts: List of texts to generate embeddings for
            batch_size: Number of texts to process per API call

        Returns:
            List of embedding vectors
        """
        all_embeddings = []

        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]

            # Truncate each text if needed
            max_chars = 8000 * 4
            batch = [t[:max_chars] if len(t) > max_chars else t for t in batch]

            response = self.client.embeddings.create(
                model=settings.embedding_model,
                input=batch,
                dimensions=settings.embedding_dimensions,
            )

            # Sort by index to maintain order
            sorted_data = sorted(response.data, key=lambda x: x.index)
            all_embeddings.extend([d.embedding for d in sorted_data])

        return all_embeddings

    def embed_requirement(
        self,
        requirement_id: uuid.UUID,
        force: bool = False,
    ) -> Optional[list[float]]:
        """Generate and store embedding for a single requirement.

        Args:
            requirement_id: The requirement's UUID
            force: If True, regenerate even if embedding exists

        Returns:
            The embedding vector, or None if requirement not found
        """
        if not self.db:
            raise ValueError("Database session required")

        requirement = (
            self.db.query(FrameworkRequirement)
            .filter(FrameworkRequirement.id == requirement_id)
            .first()
        )

        if not requirement:
            return None

        # Skip if embedding exists and not forcing
        if requirement.embedding and not force:
            return requirement.embedding

        # Generate embedding
        text = self.prepare_requirement_text(requirement)
        embedding = self.generate_embedding(text)

        # Store embedding
        requirement.embedding = embedding
        self.db.commit()

        return embedding

    def embed_all_requirements(
        self,
        framework_id: Optional[uuid.UUID] = None,
        force: bool = False,
        batch_size: int = 100,
    ) -> dict[str, int]:
        """Generate embeddings for all requirements (optionally filtered by framework).

        Args:
            framework_id: Optional framework filter
            force: If True, regenerate all embeddings
            batch_size: Number of requirements to process per batch

        Returns:
            Dictionary with counts of processed, skipped, and failed
        """
        if not self.db:
            raise ValueError("Database session required")

        query = self.db.query(FrameworkRequirement)

        if framework_id:
            query = query.filter(FrameworkRequirement.framework_id == framework_id)

        if not force:
            query = query.filter(FrameworkRequirement.embedding.is_(None))

        requirements = query.all()

        stats = {"processed": 0, "skipped": 0, "failed": 0}

        # Process in batches
        for i in range(0, len(requirements), batch_size):
            batch = requirements[i:i + batch_size]

            # Prepare texts
            texts = [self.prepare_requirement_text(req) for req in batch]

            try:
                # Generate embeddings in batch
                embeddings = self.generate_embeddings_batch(texts, batch_size=batch_size)

                # Store embeddings
                for req, embedding in zip(batch, embeddings):
                    req.embedding = embedding
                    stats["processed"] += 1

                self.db.commit()

            except Exception as e:
                # Log error and continue with next batch
                print(f"Error processing batch: {e}")
                stats["failed"] += len(batch)
                self.db.rollback()

        return stats

    def get_embedding(
        self,
        requirement_id: uuid.UUID,
    ) -> Optional[list[float]]:
        """Get the embedding for a requirement.

        Args:
            requirement_id: The requirement's UUID

        Returns:
            The embedding vector, or None if not found
        """
        if not self.db:
            raise ValueError("Database session required")

        requirement = (
            self.db.query(FrameworkRequirement)
            .filter(FrameworkRequirement.id == requirement_id)
            .first()
        )

        return requirement.embedding if requirement else None

    def get_requirements_with_embeddings(
        self,
        framework_id: Optional[uuid.UUID] = None,
        is_assessable: Optional[bool] = None,
    ) -> list[tuple[FrameworkRequirement, list[float]]]:
        """Get all requirements that have embeddings.

        Args:
            framework_id: Optional framework filter
            is_assessable: Optional filter for assessable requirements

        Returns:
            List of (requirement, embedding) tuples
        """
        if not self.db:
            raise ValueError("Database session required")

        query = self.db.query(FrameworkRequirement).filter(
            FrameworkRequirement.embedding.isnot(None)
        )

        if framework_id:
            query = query.filter(FrameworkRequirement.framework_id == framework_id)

        if is_assessable is not None:
            query = query.filter(FrameworkRequirement.is_assessable == is_assessable)

        requirements = query.all()
        return [(req, req.embedding) for req in requirements]
