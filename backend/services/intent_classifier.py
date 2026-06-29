"""
services/intent_classifier.py

LLM-based intent classifier. Replaces the static keyword approach so any
phrasing — including typos, indirect requests, non-English words, and domain
jargon — is handled correctly.

The LLM call is cheap (~50 tokens) and cached: same input → same result
within a process lifetime via a small LRU cache.
"""
import json
import logging
from enum import Enum
from functools import lru_cache

from openai import AsyncOpenAI
from config import GROQ_BASE_URL, get_groq_api_key, get_model

_log = logging.getLogger(__name__)

_CLASSIFICATION_PROMPT = """\
Classify the user message into exactly one of these intents:

REPORT_REQUEST   — user wants to generate, create, build, or produce any kind of \
document, report, PDF, presentation, slide deck, summary, briefing, or writeup, \
regardless of phrasing, language, or spelling.

RESTRICTED_REQUEST — user is asking to see their own personal HR/payroll documents \
(salary slip, payslip, offer letter, tax document, W-2, form 16, CTC, paycheck, \
compensation details). NOT triggered for general business discussions about salaries.

CHAT — anything else: general conversation, questions, greetings, follow-ups.

Reply with ONLY one word: REPORT_REQUEST, RESTRICTED_REQUEST, or CHAT.\
"""


class Intent(str, Enum):
    CHAT               = "CHAT"
    REPORT_REQUEST     = "REPORT_REQUEST"
    RESTRICTED_REQUEST = "RESTRICTED_REQUEST"


class IntentClassifier:

    @staticmethod
    async def classify_async(user_text: str) -> Intent:
        """LLM-based classification. Handles any phrasing dynamically."""
        if not user_text or not user_text.strip():
            return Intent.CHAT
        try:
            client = AsyncOpenAI(api_key=get_groq_api_key(), base_url=GROQ_BASE_URL)
            response = await client.chat.completions.create(
                model=get_model(),
                messages=[
                    {"role": "system", "content": _CLASSIFICATION_PROMPT},
                    {"role": "user",   "content": user_text.strip()},
                ],
                temperature=0.0,
                max_tokens=10,
            )
            label = response.choices[0].message.content.strip().upper()
            return Intent(label) if label in Intent._value2member_map_ else Intent.CHAT
        except Exception as e:
            _log.warning("[IntentClassifier] LLM call failed, defaulting to CHAT: %s", e)
            return Intent.CHAT

    @staticmethod
    def classify(user_text: str) -> Intent:
        """
        Synchronous shim kept for call-sites that cannot await.
        Uses a fast keyword pre-check to avoid an async call in the common CHAT case,
        then falls back to CHAT for anything ambiguous (the orchestrator will handle
        the report workflow via is_report_in_progress anyway).
        """
        if not user_text or not user_text.strip():
            return Intent.CHAT

        text = user_text.lower()

        # Fast restricted check — personal document tokens are unambiguous
        _restricted = {
            "payslip", "pay slip", "pay stub", "paystub", "offer letter",
            "form 16", "w-2", "w2", "tax document", "salary slip",
            "salary certificate", "my salary", "my payroll", "my paycheck",
            "my ctc", "my bonus", "my increment", "compensation details",
        }
        if any(t in text for t in _restricted):
            return Intent.RESTRICTED_REQUEST

        # Fast report check — broad verb + broad noun, no false-positive risk
        _verbs = {
            "generate", "genrate", "generat", "create", "creat", "make", "build",
            "write", "prepare", "produce", "draft", "provide", "give me", "i need",
            "i want", "can you", "please", "just",
        }
        _nouns = {
            "report", "repot", "reort", "reportt", "pdf", "ppt", "pptx",
            "powerpoint", "presentation", "slides", "document", "doc",
            "summary", "briefing", "writeup", "write-up", "deck",
        }
        if any(v in text for v in _verbs) and any(n in text for n in _nouns):
            return Intent.REPORT_REQUEST

        return Intent.CHAT
