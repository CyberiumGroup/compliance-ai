"""Policy ingestion service for document files."""

import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from app.models.policy import Policy
from app.services.audit.audit_service import AuditService
from app.services.ingestion.text_extraction import TextExtractionService
from app.core.ai_client import ai_client


class PolicyIngestionService:
    """Service for ingesting policies from document files."""

    def __init__(self, db: Session):
        self.db = db
        self.audit_service = AuditService(db)
        self.text_extraction = TextExtractionService()

    def ingest_file(
        self,
        file_content: bytes,
        filename: str,
        assessment_id: uuid.UUID,
        user_id: uuid.UUID | None = None,
        name: str | None = None,
        description: str | None = None,
        version: str | None = None,
        owner: str | None = None,
    ) -> dict[str, Any]:
        """
        Ingest a policy from a document file.

        Args:
            file_content: File content as bytes
            filename: Original filename
            assessment_id: Assessment to associate with
            user_id: User performing the upload
            name: Optional policy name (defaults to filename)
            description: Optional policy description
            version: Optional policy version
            owner: Optional policy owner

        Returns:
            Dict with policy details and extraction status
        """
        # Extract text from document
        extracted_text, extraction_error = self.text_extraction.extract_from_bytes(
            file_content, filename
        )

        # Generate name from filename if not provided
        if not name:
            name = Path(filename).stem.replace("_", " ").replace("-", " ").title()

        # Generate AI summary from extracted text (best-effort — failures don't block upload)
        summary = None
        if extracted_text:
            try:
                summary = ai_client.generate_policy_summary(extracted_text, name)
            except Exception:
                pass

        # Create policy
        policy = Policy(
            id=uuid.uuid4(),
            assessment_id=assessment_id,
            name=name,
            description=description,
            version=version,
            owner=owner,
            file_path=filename,
            content_text=extracted_text if extracted_text else None,
            summary=summary,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )

        self.db.add(policy)
        self.db.flush()

        # Audit log
        self.audit_service.log_create(
            entity_type="policy",
            entity_id=policy.id,
            new_values={
                "name": policy.name,
                "filename": filename,
                "assessment_id": str(assessment_id),
                "text_extracted": bool(extracted_text),
            },
            user_id=user_id,
        )

        self.db.commit()

        return {
            "policy": policy,
            "text_extracted": bool(extracted_text),
            "text_length": len(extracted_text) if extracted_text else None,
            "extraction_error": extraction_error,
        }

    def update_policy_text(
        self,
        policy_id: uuid.UUID,
        file_content: bytes,
        filename: str,
        user_id: uuid.UUID | None = None,
    ) -> dict[str, Any]:
        """
        Update a policy's text content from a new file.

        Args:
            policy_id: ID of the policy to update
            file_content: New file content
            filename: New filename
            user_id: User performing the update

        Returns:
            Dict with update status
        """
        policy = self.db.query(Policy).filter(Policy.id == policy_id).first()
        if not policy:
            return {
                "success": False,
                "error": "Policy not found",
            }

        old_values = {
            "file_path": policy.file_path,
            "content_text_length": len(policy.content_text) if policy.content_text else 0,
        }

        # Extract text from new document
        extracted_text, extraction_error = self.text_extraction.extract_from_bytes(
            file_content, filename
        )

        policy.file_path = filename
        policy.content_text = extracted_text if extracted_text else None
        policy.updated_at = datetime.utcnow()

        # Audit log
        self.audit_service.log_update(
            entity_type="policy",
            entity_id=policy.id,
            old_values=old_values,
            new_values={
                "file_path": filename,
                "content_text_length": len(extracted_text) if extracted_text else 0,
            },
            user_id=user_id,
        )

        self.db.commit()

        return {
            "success": True,
            "text_extracted": bool(extracted_text),
            "text_length": len(extracted_text) if extracted_text else None,
            "extraction_error": extraction_error,
        }
