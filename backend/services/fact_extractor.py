"""
services/fact_extractor.py

Single responsibility: extract structured facts from a conversation turn.

Implementation: focused LLM call with a small, strict prompt.
Handles all phrasings, typos, speech-to-text artifacts, and languages.
Regex cannot do this reliably — the LLM can.

Cost: ~50-80 tokens per turn (extraction prompt is intentionally minimal).
Latency: runs concurrently after the main response is already returned to the user.

The caller (OrchestratorAgent) writes returned facts into SessionMemoryService.
This class has no knowledge of sessions, agents, or pipelines.
"""
import json
import logging
from typing import Dict

from openai import AsyncOpenAI
from config import GROQ_BASE_URL, get_groq_api_key, get_model

_log = logging.getLogger(__name__)

_EXTRACTION_PROMPT = """\
You are a fact extractor. Given a conversation snippet, extract ALL explicitly stated facts.

Return ONLY a valid JSON object with string values. Use null for unknown fields.
Only include fields where the user explicitly stated information — do not infer or guess.

Fixed fields to extract (use exactly these keys):
{
  "user_name":     "person's name if stated, else null",
  "business_type": "what kind of business/product/service if stated, else null",
  "company_name":  "company name if stated, else null",
  "location":      "city or region if stated, else null",
  "revenue":       "revenue/sales figure if stated, else null",
  "employees":     "employee count if stated, else null",
  "goal":          "stated goal or objective if stated, else null",
  "problem":       "stated problem or challenge if stated, else null",
  "other_facts":   {"descriptive_key": "value"} for ANY other explicit facts not covered above (purchases, preferences, numbers, dates, relationships, etc.), else null
}

Rules:
- Only extract what is explicitly said.
- Ignore filler words, typos, and grammar errors — extract the meaning.
- For other_facts, use short snake_case keys that describe the fact (e.g. "bike_purchase": "bought a bike for 10k").
- Return {} if nothing is extractable.
- Never fabricate values.
- Output only the JSON object, nothing else.\
"""


class FactExtractorService:

    @staticmethod
    async def extract_async(user_text: str, ai_response: str = "") -> Dict[str, str]:
        """
        Extract facts from a conversation turn using the LLM.
        Includes both user utterance and AI response for full context.
        Returns {key: value} with null values removed.
        Returns {} on any failure — never raises.
        """
        snippet = f"User: {user_text}"
        if ai_response:
            snippet += f"\nAssistant: {ai_response}"

        try:
            client = AsyncOpenAI(api_key=get_groq_api_key(), base_url=GROQ_BASE_URL)
            response = await client.chat.completions.create(
                model=get_model(),
                messages=[
                    {"role": "system", "content": _EXTRACTION_PROMPT},
                    {"role": "user",   "content": snippet},
                ],
                temperature=0.0,
                max_tokens=300,
            )
            raw = response.choices[0].message.content.strip()
            # Strip markdown fences if present
            if raw.startswith("```"):
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]
            parsed = json.loads(raw)
            # Flatten other_facts into top-level keys
            other = parsed.pop("other_facts", None)
            if isinstance(other, dict):
                parsed.update(other)
            # Remove null/empty values
            return {k: v for k, v in parsed.items() if v and str(v).lower() not in ("null", "none", "")}
        except Exception as e:
            _log.warning("[FactExtractor] extraction failed: %s", e)
            return {}
