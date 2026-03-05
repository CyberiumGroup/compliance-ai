"""Control fact extraction service.

Extracts atomic, independently-verifiable control facts from policy and evidence
documents. Facts are stored as PolicyFact rows and consumed by the scoring engine
instead of raw document text.

Fact types
----------
policy_control
    Extracted from policy/procedure documents (document_type == 'policy').
    Describes what the organisation has *defined, committed to, or designed*.

evidence_observation
    Extracted from evidence artifacts (document_type == 'evidence').
    Describes what the organisation *demonstrably does in practice*.

Extraction rules (applied via prompt)
--------------------------------------
1. Atomic — one fact = one verifiable claim. No compound facts joined with "and".
2. Subject-Verb-Object form — e.g. "The IT team reviews access logs weekly."
3. Separate frequency/trigger/conditions into key_attributes rather than embedding
   them in the statement where possible.
4. No inference — only extract what is explicitly stated or very strongly implied by
   the document's own text. Do not draw conclusions or assume standard practice.

Policy-specific normative criteria
------------------------------------
For policy documents, target explicit normative control statements. Include a sentence if it:
  - Contains "must", "must not", "shall", "is required to", or "are responsible for"
  - Imposes a restriction, obligation, or defined responsibility

Exclusions (policy and evidence)
----------------------------------
Do NOT extract:
  - Purpose or scope statements ("This policy applies to…", "The purpose of this document is…")
  - Definitions or glossary entries
  - Historical notes or version history
  - Approval metadata (approver names, signatures, approval dates)
  - Document history tables
  - Section headers or titles
"""

import json
import logging
import uuid
from datetime import datetime

from openai import AsyncOpenAI, APIError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.policy import Policy
from app.models.policy_fact import PolicyFact

logger = logging.getLogger(__name__)

# gpt-4o-mini for cost efficiency — extraction is document-level (once per doc)
_EXTRACTION_MODEL = "gpt-4o-mini"
_MAX_OUTPUT_TOKENS = 4000

# Truncate very large documents to keep prompt within model limits.
# 40 000 chars ≈ 10 000 tokens — well within gpt-4o-mini's 128k context.
_MAX_CONTENT_CHARS = 40_000

# ─── Shared extraction rules block ────────────────────────────────────────────

_EXTRACTION_RULES = """
Extraction rules — follow strictly:
1. ATOMIC: Each fact must be one verifiable claim. Do not combine multiple actions
   with "and". If a sentence covers two actions, produce two facts.
2. SUBJECT-VERB-OBJECT: Write each statement as "Subject verb object", e.g.
   "The IT Security team reviews privileged access logs every 90 days."
3. SEPARATE ATTRIBUTES: Do not embed frequency, trigger, conditions, or scope into
   the statement. Move them to key_attributes instead.
4. NO INFERENCE: Only extract what is explicitly stated or very strongly implied by
   the document's own text. Do not draw conclusions or assume standard practice.

Do NOT extract any of the following — skip them entirely:
- Purpose or scope statements ("This policy applies to…", "The purpose of this document is…")
- Definitions or glossary entries
- Historical notes or version history
- Approval metadata (approver names, signatures, approval dates)
- Document history tables
- Section headers or titles
"""

_POLICY_NORMATIVE_CRITERIA = """
What to extract from this policy document:
Extract all explicit normative control statements. A control statement qualifies if it:
- Contains the words "must", "must not", "shall", "is required to", or "are responsible for"
- OR imposes a clear restriction, obligation, or defined responsibility

Extract every qualifying sentence. Do not limit or sample — if it is a control statement, include it.
"""

# ─── Prompt builders ──────────────────────────────────────────────────────────

def _policy_text_prompt(document_name: str, content: str) -> list[dict]:
    """Prompt for a text-based policy/procedure document."""
    system = (
        "You are a compliance analyst extracting structured control facts from "
        "an organisation's policy or procedure document.\n\n"
        "A 'policy_control' fact describes what the organisation has defined, "
        "committed to, or designed — not what they actually do in practice.\n\n"
        + _POLICY_NORMATIVE_CRITERIA
        + _EXTRACTION_RULES
        + "\n\nRespond with a JSON object matching this schema exactly:\n"
        '{\n'
        '  "facts": [\n'
        '    {\n'
        '      "statement": "string — atomic S-V-O claim",\n'
        '      "key_attributes": {\n'
        '        "what": "what control or action is described",\n'
        '        "scope": "which systems, people, or assets are covered (null if not stated)",\n'
        '        "responsible_party": "who is accountable (null if not stated)",\n'
        '        "frequency": "how often (null if not stated)",\n'
        '        "trigger": "what event triggers this control (null if not stated)",\n'
        '        "conditions": "any conditions or prerequisites (null if not stated)",\n'
        '        "exceptions": "any stated exceptions or exclusions (null if not stated)",\n'
        '        "tools": "tools or systems mentioned (null if not stated)"\n'
        '      },\n'
        '      "confidence": "explicit OR implied",\n'
        '      "document_reference": {\n'
        '        "document_name": "string",\n'
        '        "section": "section heading or page reference (null if unknown)"\n'
        '      }\n'
        '    }\n'
        '  ]\n'
        '}'
    )
    user = (
        f"Document: {document_name}\n\n"
        "Extract policy_control facts from the following document text.\n\n"
        f"{content}"
    )
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


def _evidence_text_prompt(document_name: str, content: str) -> list[dict]:
    """Prompt for a text-based evidence artifact."""
    system = (
        "You are a compliance analyst extracting structured control facts from "
        "an organisation's evidence artifact (e.g. audit log, report, screenshot "
        "description, meeting minutes, or test result).\n\n"
        "An 'evidence_observation' fact describes what the organisation "
        "demonstrably *does in practice* — not what a policy says they should do.\n\n"
        + _EXTRACTION_RULES
        + "\n\nRespond with a JSON object matching this schema exactly:\n"
        '{\n'
        '  "facts": [\n'
        '    {\n'
        '      "statement": "string — atomic S-V-O claim",\n'
        '      "key_attributes": {\n'
        '        "what": "what activity or outcome is evidenced",\n'
        '        "scope": "which systems, people, or assets are covered (null if not stated)",\n'
        '        "time_period": "when or over what period (null if not stated)",\n'
        '        "actor": "who performed the activity (null if not stated)",\n'
        '        "result": "outcome or finding (null if not stated)",\n'
        '        "anomalies": "any exceptions or issues noted (null if not stated)"\n'
        '      },\n'
        '      "document_reference": {\n'
        '        "document_name": "string",\n'
        '        "section": "section heading or page reference (null if unknown)"\n'
        '      }\n'
        '    }\n'
        '  ]\n'
        '}'
    )
    user = (
        f"Document: {document_name}\n\n"
        "Extract evidence_observation facts from the following evidence text.\n\n"
        f"{content}"
    )
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


def _evidence_spreadsheet_prompt(document_name: str, json_content: str) -> list[dict]:
    """Prompt for a spreadsheet evidence artifact (JSON representation)."""
    system = (
        "You are a compliance analyst extracting structured control facts from "
        "an organisation's evidence spreadsheet. The spreadsheet has been parsed "
        "into JSON format with sheets, columns, and rows.\n\n"
        "An 'evidence_observation' fact describes what the organisation "
        "demonstrably *does in practice*.\n\n"
        "Spreadsheet guidance:\n"
        "- Each row often represents one observation (e.g. a log entry, a review record).\n"
        "- Column names describe what each value means.\n"
        "- Synthesise row-level data into atomic factual statements about "
        "the organisation's actual practices.\n"
        "- Do not produce one fact per row — identify the patterns and "
        "recurring activities the data demonstrates.\n\n"
        + _EXTRACTION_RULES
        + "\n\nRespond with a JSON object matching this schema exactly:\n"
        '{\n'
        '  "facts": [\n'
        '    {\n'
        '      "statement": "string — atomic S-V-O claim",\n'
        '      "key_attributes": {\n'
        '        "what": "what activity or outcome is evidenced",\n'
        '        "scope": "which systems, people, or assets are covered (null if not stated)",\n'
        '        "time_period": "when or over what period (null if not stated)",\n'
        '        "actor": "who performed the activity (null if not stated)",\n'
        '        "result": "outcome or finding (null if not stated)",\n'
        '        "anomalies": "any exceptions or issues noted (null if not stated)"\n'
        '      },\n'
        '      "document_reference": {\n'
        '        "document_name": "string",\n'
        '        "section": "sheet name or column reference (null if unknown)"\n'
        '      }\n'
        '    }\n'
        '  ]\n'
        '}'
    )
    user = (
        f"Document: {document_name} (spreadsheet, converted to JSON)\n\n"
        "Extract evidence_observation facts from the following spreadsheet data.\n\n"
        f"{json_content}"
    )
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


# ─── Service ──────────────────────────────────────────────────────────────────

class FactExtractionService:
    """Extracts control facts from a policy or evidence document.

    Usage (background task):
        service = FactExtractionService(db)
        await service.extract_and_store(policy_id)
    """

    def __init__(self, db: Session):
        self.db = db
        self._openai: AsyncOpenAI | None = None

    def _get_client(self) -> AsyncOpenAI:
        if self._openai is None:
            if not settings.openai_api_key:
                raise ValueError("OPENAI_API_KEY not configured")
            # max_retries=3: SDK will automatically retry 5xx errors with
            # exponential backoff, handling transient OpenAI server errors.
            self._openai = AsyncOpenAI(api_key=settings.openai_api_key, max_retries=3)
        return self._openai

    async def extract_and_store(self, policy_id: uuid.UUID) -> dict:
        """Extract facts from a document and persist them.

        Deletes any existing facts for the policy before storing new ones,
        so this method is safe to call for regeneration.

        Returns a summary dict:
            {"fact_count": int, "warning": str | None}
        """
        policy = self.db.query(Policy).filter(Policy.id == policy_id).first()
        if not policy:
            logger.error("FactExtractionService: policy %s not found", policy_id)
            return {"fact_count": 0, "warning": "Policy not found"}

        if not policy.content_text:
            logger.warning(
                "FactExtractionService: policy %s has no content_text — skipping extraction",
                policy_id,
            )
            policy.facts_extracted_at = datetime.utcnow()
            self.db.commit()
            return {"fact_count": 0, "warning": "Document has no extractable text"}

        # ── Build the appropriate prompt ───────────────────────────────────────
        document_name = policy.name or policy.file_path or str(policy_id)
        content = policy.content_text[:_MAX_CONTENT_CHARS]
        is_spreadsheet = (policy.chunk_strategy == "tabular")

        if policy.document_type == "policy":
            messages = _policy_text_prompt(document_name, content)
            fact_type = "policy_control"
        elif is_spreadsheet:
            messages = _evidence_spreadsheet_prompt(document_name, content)
            fact_type = "evidence_observation"
        else:
            messages = _evidence_text_prompt(document_name, content)
            fact_type = "evidence_observation"

        # ── Call LLM ──────────────────────────────────────────────────────────
        total_chars = sum(len(m["content"]) for m in messages)
        logger.debug(
            "FactExtractionService: sending %d chars to %s for policy %s",
            total_chars, _EXTRACTION_MODEL, policy_id,
        )
        raw_facts: list[dict] = []
        llm_error: str | None = None
        try:
            client = self._get_client()
            response = await client.chat.completions.create(
                model=_EXTRACTION_MODEL,
                messages=messages,
                max_tokens=_MAX_OUTPUT_TOKENS,
                temperature=0.0,
                response_format={"type": "json_object"},
            )
            raw_text = response.choices[0].message.content or ""
            parsed = json.loads(raw_text)
            raw_facts = parsed.get("facts", [])
        except APIError as exc:
            # Expected transient failures (5xx, rate limits, timeouts) — no traceback needed.
            llm_error = str(exc)
            logger.warning(
                "FactExtractionService: OpenAI API error for policy %s: %s",
                policy_id, exc,
            )
        except Exception as exc:
            # Unexpected error (JSON parse failure, SDK bug, etc.) — log with traceback.
            llm_error = str(exc)
            logger.exception(
                "FactExtractionService: unexpected error for policy %s",
                policy_id,
            )

        # ── Delete existing facts ──────────────────────────────────────────────
        self.db.query(PolicyFact).filter(PolicyFact.policy_id == policy_id).delete()

        # ── Persist new facts ──────────────────────────────────────────────────
        for i, raw in enumerate(raw_facts):
            if not isinstance(raw, dict):
                continue
            statement = raw.get("statement", "").strip()
            if not statement:
                continue

            fact = PolicyFact(
                id=uuid.uuid4(),
                policy_id=policy_id,
                fact_index=i,
                fact_type=fact_type,
                statement=statement,
                key_attributes=raw.get("key_attributes") or None,
                confidence=raw.get("confidence") or None,
                document_reference=raw.get("document_reference") or None,
                extraction_model=_EXTRACTION_MODEL,
                created_at=datetime.utcnow(),
                embedding_vector=None,  # FUTURE: fact-level filtering (not yet implemented)
            )
            self.db.add(fact)

        # ── Mark extraction complete ───────────────────────────────────────────
        policy.facts_extracted_at = datetime.utcnow()
        self.db.commit()

        fact_count = len([r for r in raw_facts if isinstance(r, dict) and r.get("statement", "").strip()])

        warning: str | None = None
        if llm_error:
            warning = f"Extraction failed: {llm_error}"
        elif fact_count == 0:
            warning = "No facts were extracted — the document may lack control-relevant content."

        logger.info(
            "FactExtractionService: extracted %d facts for policy %s (type=%s)",
            fact_count, policy_id, fact_type,
        )
        return {"fact_count": fact_count, "warning": warning}
