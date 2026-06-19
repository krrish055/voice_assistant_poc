"""
services/intent_classifier.py

Single responsibility: classify raw user text into an Intent.

Design constraints:
  - No knowledge of agents, registry, pipeline, or routing.
  - Keyword-based for Sprint 2 (fast, zero-cost, no LLM call).
  - Sprint 3 can swap classify() for an LLM pre-classification call
    without changing any other file.

Routing precedence (highest → lowest):
  RESTRICTED_REQUEST > REPORT_REQUEST > CHAT

Security wins: if restricted AND report signals both appear in the same
utterance, RESTRICTED_REQUEST is returned.
"""
from enum import Enum


class Intent(str, Enum):
    CHAT                = "CHAT"
    REPORT_REQUEST      = "REPORT_REQUEST"
    RESTRICTED_REQUEST  = "RESTRICTED_REQUEST"


# ---------------------------------------------------------------------------
# Keyword sets
# Each set contains lowercase tokens. Classification requires the user text
# (lowercased) to contain at least one token from the relevant set.
#
# RESTRICTED tokens carry higher signal than REPORT tokens and are checked
# first. An action verb is NOT required for restricted requests because
# "show me my salary" and "payslip" are unambiguous on their own.
#
# REPORT tokens require an action verb co-occurring with a document noun to
# avoid false positives from casual usage ("let me report back", "report
# on the situation").
# ---------------------------------------------------------------------------

_RESTRICTED_TOKENS: frozenset[str] = frozenset({
    "payslip", "pay slip", "pay stub", "paystub",
    "offer letter", "form 16", "w-2", "w2",
    "tax document",
})

# Phrases that are only restricted when the user is requesting their OWN documents.
# A business owner discussing salary delays or payroll strategy is NOT restricted.
# Restriction triggers only when BOTH a possessive/request signal AND a sensitive noun appear.
_RESTRICTED_PHRASE_PAIRS: tuple = (
    ("my salary",    None),
    ("my payroll",   None),
    ("my paycheck",  None),
    ("my ctc",       None),
    ("my bonus",     None),
    ("my increment", None),
    ("show salary",  None),
    ("see salary",   None),
    ("get salary",   None),
    ("salary slip",  None),
    ("salary certificate", None),
    ("compensation details", None),
    ("cost to company", None),
)

_REPORT_ACTION_VERBS: frozenset[str] = frozenset({
    "generate", "create", "make", "build", "write",
    "prepare", "produce", "draft", "give me a", "i need a",
    "can you make", "can you create", "can you generate",
})

_REPORT_DOCUMENT_NOUNS: frozenset[str] = frozenset({
    "report", "pdf", "ppt", "pptx", "powerpoint",
    "presentation", "slides", "document", "summary",
    "briefing", "writeup", "write-up",
})


class IntentClassifier:
    """
    Stateless keyword-based intent classifier.

    Sprint 3 extension: replace or wrap classify() with an LLM pre-call.
    The return type (Intent) and method signature stay identical.
    """

    @staticmethod
    def classify(user_text: str) -> Intent:
        """Return the Intent for the given user utterance.

        Precedence: RESTRICTED_REQUEST > REPORT_REQUEST > CHAT

        RESTRICTED only triggers for explicit personal document/data requests
        (e.g. "show me my salary slip"), NOT for business context discussions
        (e.g. "salaries are delayed", "payroll strategy", "employee bonus plan").
        """
        if not user_text or not user_text.strip():
            return Intent.CHAT

        text = user_text.lower()

        # --- RESTRICTED: exact document tokens (payslip, form 16, etc.) ----
        if any(token in text for token in _RESTRICTED_TOKENS):
            return Intent.RESTRICTED_REQUEST

        # --- RESTRICTED: possessive/request phrases -------------------------
        if any(phrase in text for phrase, _ in _RESTRICTED_PHRASE_PAIRS):
            return Intent.RESTRICTED_REQUEST

        # --- REPORT (requires action verb + document noun) ------------------
        has_action = any(verb in text for verb in _REPORT_ACTION_VERBS)
        has_noun   = any(noun in text for noun in _REPORT_DOCUMENT_NOUNS)
        if has_action and has_noun:
            return Intent.REPORT_REQUEST

        # --- Default --------------------------------------------------------
        return Intent.CHAT
