"""AI client for interacting with OpenAI API."""

import json
from typing import Any

from tenacity import retry, stop_after_attempt, wait_exponential

from app.core.config import settings


class AIClient:
    """Client for OpenAI API."""

    def __init__(self):
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

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
    )
    def generate_mapping_suggestions(
        self,
        policy_text: str,
        subcategories: list[dict[str, str]],
    ) -> list[dict[str, Any]]:
        """
        Generate mapping suggestions for a policy document.

        Args:
            policy_text: The text content of the policy
            subcategories: List of requirements with code and description

        Returns:
            List of suggested mappings with confidence scores
        """
        subcategories_text = "\n".join(
            f"- {sc['code']}: {sc['description']}"
            for sc in subcategories
        )

        prompt = f"""Analyze the following policy document and determine which framework requirements it maps to.

POLICY TEXT:
{policy_text[:4000]}

AVAILABLE REQUIREMENTS:
{subcategories_text}

Respond with a JSON array of mappings. Each mapping should have:
- "subcategory_code": The requirement code (e.g., "GV.OC-01")
- "confidence_score": A number between 0.0 and 1.0 indicating confidence
- "reasoning": A brief explanation of why this mapping applies
- "source_excerpt": A short quote (1-2 sentences) from the policy text that supports this mapping

Only include mappings with confidence >= 0.3. Return an empty array if no mappings apply.

Respond ONLY with the JSON array, no other text."""

        response = self.client.chat.completions.create(
            model=settings.ai_model,
            max_tokens=settings.ai_max_tokens,
            temperature=settings.ai_temperature,
            messages=[{"role": "user", "content": prompt}],
        )

        try:
            content = response.choices[0].message.content.strip()
            # Handle potential markdown code blocks
            if content.startswith("```"):
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]
            return json.loads(content)
        except (json.JSONDecodeError, IndexError):
            return []

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
    )
    def analyze_interview_response(
        self,
        question: str,
        response: str,
        subcategory_code: str,
        subcategory_description: str,
    ) -> dict[str, Any]:
        """
        Analyze an interview response for scoring insights.

        Args:
            question: The interview question
            response: The interviewee's response
            subcategory_code: The related CSF subcategory code
            subcategory_description: The subcategory description

        Returns:
            Analysis including maturity indicators and evidence
        """
        prompt = f"""Analyze this interview response for a compliance assessment.

REQUIREMENT: {subcategory_code}
DESCRIPTION: {subcategory_description}

QUESTION: {question}

RESPONSE: {response}

Analyze and respond with JSON containing:
- "maturity_indicators": List of positive maturity indicators found
- "gaps_identified": List of gaps or concerns identified
- "evidence_quotes": Key quotes that serve as evidence
- "suggested_score_contribution": A number 0-4 based on maturity tiers (0=no evidence, 4=adaptive/optimized)
- "confidence": How confident you are in this analysis (0.0-1.0)

Respond ONLY with the JSON object, no other text."""

        ai_response = self.client.chat.completions.create(
            model=settings.ai_model,
            max_tokens=settings.ai_max_tokens,
            temperature=settings.ai_temperature,
            messages=[{"role": "user", "content": prompt}],
        )

        try:
            content = ai_response.choices[0].message.content.strip()
            if content.startswith("```"):
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]
            return json.loads(content)
        except (json.JSONDecodeError, IndexError):
            return {
                "maturity_indicators": [],
                "gaps_identified": [],
                "evidence_quotes": [],
                "suggested_score_contribution": 0,
                "confidence": 0.0,
            }


    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
    )
    def generate_policy_summary(self, policy_text: str, policy_name: str) -> str:
        """Generate a concise high-level summary of a policy document.

        Args:
            policy_text: Extracted text content of the policy document
            policy_name: Name of the policy (used for context)

        Returns:
            2-3 sentence summary describing the document's purpose, scope, and key topics
        """
        # Use first 4000 chars — enough to capture title, purpose, and scope sections
        excerpt = policy_text[:4000]

        prompt = f"""Write a 2-3 sentence summary of the following policy document called "{policy_name}".
Describe its purpose, the topics it covers, and who or what it applies to.
Be concise and factual. Do not use phrases like "This document" or "This policy" — start directly with what the policy does.

DOCUMENT:
{excerpt}

Summary:"""

        response = self.client.chat.completions.create(
            model=settings.ai_model,
            max_tokens=200,
            temperature=0.0,
            messages=[{"role": "user", "content": prompt}],
        )

        return response.choices[0].message.content.strip()

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
    )
    def generate_spreadsheet_summary(self, json_content: str, filename: str) -> str:
        """Generate a concise summary of spreadsheet evidence data."""
        try:
            data = json.loads(json_content)
            sheets = data.get("sheets", [])
            sheet_desc = "; ".join(
                f'"{s["name"]}" ({len(s["rows"])} rows, columns: {", ".join(s["columns"][:6])}'
                f'{"…" if len(s["columns"]) > 6 else ""})'
                for s in sheets
            )
        except Exception:
            sheet_desc = "unknown structure"

        excerpt = json_content[:4000]

        prompt = f"""Summarize the following spreadsheet evidence file called "{filename}".
Structure: {sheet_desc}

Describe what type of implementation evidence this spreadsheet represents, what data it contains,
and what compliance or security controls it might demonstrate.
Be concise (2-3 sentences). Start directly with what the data shows.

DATA (JSON, truncated):
{excerpt}

Summary:"""

        response = self.client.chat.completions.create(
            model=settings.ai_model,
            max_tokens=200,
            temperature=0.0,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.choices[0].message.content.strip()


# Global AI client instance
ai_client = AIClient()
