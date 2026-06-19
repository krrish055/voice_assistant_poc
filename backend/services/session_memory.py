"""
services/session_memory.py

Single responsibility: persist and serve all session-scoped memory.

Stores per session:
  - facts: extracted key-value facts from conversation (name, business, numbers, etc.)
  - summary: rolling summary of conversation so far
  - recent_turns: last N raw turns for context
  - report_slots: topic, page_count, output_format

Design: interface + in-process dict implementation.
Swap to Redis: implement ISessionMemory backed by redis-py without changing any agent.

Token efficiency:
  Agents receive a compact context_block string, not raw history.
  Full history is never resent after the first MEMORY_SUMMARY_TURNS turns.
"""
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from config import MEMORY_MAX_FACTS, MEMORY_SUMMARY_TURNS, MEMORY_HISTORY_WINDOW

_REQUIRED_SLOTS = ("topic", "page_count", "output_format")


class ISessionMemory(ABC):

    # ── Fact store ────────────────────────────────────────────────────────────

    @abstractmethod
    def set_fact(self, session_id: str, key: str, value: Any) -> None: ...

    @abstractmethod
    def get_facts(self, session_id: str) -> Dict[str, Any]: ...

    # ── Summary ───────────────────────────────────────────────────────────────

    @abstractmethod
    def set_summary(self, session_id: str, summary: str) -> None: ...

    @abstractmethod
    def get_summary(self, session_id: str) -> str: ...

    # ── Turn history ──────────────────────────────────────────────────────────

    @abstractmethod
    def add_turn(self, session_id: str, user: str, assistant: str) -> None: ...

    @abstractmethod
    def get_recent_turns(self, session_id: str) -> List[Dict]: ...

    # ── Report slots ──────────────────────────────────────────────────────────

    @abstractmethod
    def update_slot(self, session_id: str, key: str, value: Any) -> None: ...

    @abstractmethod
    def get_slots(self, session_id: str) -> Dict: ...

    @abstractmethod
    def is_slots_complete(self, session_id: str) -> bool: ...

    @abstractmethod
    def missing_slots(self, session_id: str) -> List[str]: ...

    @abstractmethod
    def clear_slots(self, session_id: str) -> None: ...

    @abstractmethod
    def is_report_in_progress(self, session_id: str) -> bool: ...

    # ── Context assembly ──────────────────────────────────────────────────────

    @abstractmethod
    def get_context_block(self, session_id: str) -> str: ...

    # ── Full session clear ────────────────────────────────────────────────────

    @abstractmethod
    def clear_session(self, session_id: str) -> None: ...


class SessionMemoryService(ISessionMemory):
    """
    In-process implementation. All data keyed by session_id.
    No global state — each instance has its own _store.
    """

    def __init__(self) -> None:
        # { session_id: { "facts": {}, "summary": "", "turns": [], "slots": {} } }
        self._store: Dict[str, Dict] = {}

    def _session(self, session_id: str) -> Dict:
        if session_id not in self._store:
            self._store[session_id] = {
                "facts":   {},
                "summary": "",
                "turns":   [],
                "slots":   {},
            }
        return self._store[session_id]

    # ── Fact store ────────────────────────────────────────────────────────────

    def set_fact(self, session_id: str, key: str, value: Any) -> None:
        sess = self._session(session_id)
        sess["facts"][key] = value
        # Cap total facts
        if len(sess["facts"]) > MEMORY_MAX_FACTS:
            oldest = next(iter(sess["facts"]))
            del sess["facts"][oldest]

    def get_facts(self, session_id: str) -> Dict[str, Any]:
        return dict(self._session(session_id)["facts"])

    # ── Summary ───────────────────────────────────────────────────────────────

    def set_summary(self, session_id: str, summary: str) -> None:
        self._session(session_id)["summary"] = summary.strip()

    def get_summary(self, session_id: str) -> str:
        return self._session(session_id)["summary"]

    # ── Turn history ──────────────────────────────────────────────────────────

    def add_turn(self, session_id: str, user: str, assistant: str) -> None:
        turns = self._session(session_id)["turns"]
        turns.append({"user_input": user, "ai_response_text": assistant})
        # Keep only the most recent window
        if len(turns) > MEMORY_HISTORY_WINDOW:
            self._store[session_id]["turns"] = turns[-MEMORY_HISTORY_WINDOW:]

    def get_recent_turns(self, session_id: str) -> List[Dict]:
        return list(self._session(session_id)["turns"][-MEMORY_SUMMARY_TURNS:])

    # ── Report slots ──────────────────────────────────────────────────────────

    def update_slot(self, session_id: str, key: str, value: Any) -> None:
        self._session(session_id)["slots"][key] = value

    def get_slots(self, session_id: str) -> Dict:
        return dict(self._session(session_id)["slots"])

    def is_slots_complete(self, session_id: str) -> bool:
        slots = self._session(session_id)["slots"]
        return all(slots.get(s) for s in _REQUIRED_SLOTS)

    def missing_slots(self, session_id: str) -> List[str]:
        slots = self._session(session_id)["slots"]
        return [s for s in _REQUIRED_SLOTS if not slots.get(s)]

    def is_report_in_progress(self, session_id: str) -> bool:
        """True if slot collection has started but is not yet complete."""
        slots = self._session(session_id)["slots"]
        has_any = any(slots.get(s) for s in _REQUIRED_SLOTS)
        return has_any and not self.is_slots_complete(session_id)

    def clear_slots(self, session_id: str) -> None:
        self._session(session_id)["slots"] = {}

    # ── Context assembly ──────────────────────────────────────────────────────

    def get_context_block(self, session_id: str) -> str:
        """
        Returns a compact string injected into every agent prompt.
        Two sections:
          [USER PROFILE]  — all persisted facts, used for summarization and recall.
          [CONFIRMED REPORT SLOTS] — filled slots, LLM must not re-ask.
        """
        sess  = self._session(session_id)
        parts = []

        summary = sess["summary"].strip()
        if summary:
            parts.append(f"[CONVERSATION SUMMARY]\n{summary}")

        facts = sess["facts"]
        if facts:
            fact_lines = "\n".join(f"  {k}: {v}" for k, v in facts.items())
            parts.append(
                f"[USER PROFILE — everything known about the user]\n"
                f"{fact_lines}\n"
                f"Use this to answer recall questions. Do NOT ask for any of this again."
            )

        slots = sess["slots"]
        filled = {k: v for k, v in slots.items() if v}
        if filled:
            slot_lines = "\n".join(f"  {k}: {v}" for k, v in filled.items())
            parts.append(f"[CONFIRMED REPORT SLOTS — do NOT ask for these again]\n{slot_lines}")

        return "\n\n".join(parts)

    # ── Full session clear ────────────────────────────────────────────────────

    def clear_session(self, session_id: str) -> None:
        self._store.pop(session_id, None)
