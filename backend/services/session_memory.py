"""
services/session_memory.py

Stores per-session memory in JSON files under backend/memory_store/.

Each session gets one file: memory_store/<session_id>.json
Structure:
  {
    "facts":       { key: value },
    "summary":     "",
    "turns":       [ { "user_input": "", "ai_response_text": "" } ],
    "slots":       { "_workflow_active": false, ... },
    "last_report": { "download_url": null, "pptx_url": null }
  }

Why JSON files:
  - Survives server restarts (in-process dict did not)
  - No extra infrastructure (no Redis, no extra DB)
  - Neo4j remains for long-term conversation history across sessions
  - This handles within-session working memory and report state
"""
import json
import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, List, Optional

from config import MEMORY_MAX_FACTS, MEMORY_SUMMARY_TURNS, MEMORY_HISTORY_WINDOW

_log = logging.getLogger(__name__)

_TOPIC_ONLY_REQUIRED = ("topic",)

# Directory next to this file's package root
_MEMORY_DIR = Path(__file__).resolve().parent.parent / "memory_store"
_MEMORY_DIR.mkdir(exist_ok=True)


def _path(session_id: str) -> Path:
    return _MEMORY_DIR / f"{session_id}.json"


def _load(session_id: str) -> Dict:
    p = _path(session_id)
    if p.exists():
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except Exception as e:
            _log.warning("[Memory] corrupt file for session=%s, resetting: %s", session_id, e)
    return {"facts": {}, "summary": "", "turns": [], "slots": {}, "last_report": {}}


def _save(session_id: str, data: Dict) -> None:
    try:
        _path(session_id).write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    except Exception as e:
        _log.error("[Memory] failed to save session=%s: %s", session_id, e)


class ISessionMemory(ABC):

    @abstractmethod
    def set_fact(self, session_id: str, key: str, value: Any) -> None: ...

    @abstractmethod
    def get_facts(self, session_id: str) -> Dict[str, Any]: ...

    @abstractmethod
    def set_summary(self, session_id: str, summary: str) -> None: ...

    @abstractmethod
    def get_summary(self, session_id: str) -> str: ...

    @abstractmethod
    def add_turn(self, session_id: str, user: str, assistant: str) -> None: ...

    @abstractmethod
    def get_recent_turns(self, session_id: str) -> List[Dict]: ...

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

    @abstractmethod
    def mark_report_started(self, session_id: str) -> None: ...

    @abstractmethod
    def set_last_report_urls(self, session_id: str, download_url: Optional[str], pptx_url: Optional[str]) -> None: ...

    @abstractmethod
    def get_last_report_urls(self, session_id: str) -> Dict: ...

    @abstractmethod
    def get_context_block(self, session_id: str) -> str: ...

    @abstractmethod
    def clear_session(self, session_id: str) -> None: ...


class SessionMemoryService(ISessionMemory):
    """JSON file-backed session memory. Survives server restarts."""

    # ── Fact store ────────────────────────────────────────────────────────────

    def set_fact(self, session_id: str, key: str, value: Any) -> None:
        d = _load(session_id)
        d["facts"][key] = value
        if len(d["facts"]) > MEMORY_MAX_FACTS:
            oldest = next(iter(d["facts"]))
            del d["facts"][oldest]
        _save(session_id, d)

    def get_facts(self, session_id: str) -> Dict[str, Any]:
        return dict(_load(session_id)["facts"])

    # ── Summary ───────────────────────────────────────────────────────────────

    def set_summary(self, session_id: str, summary: str) -> None:
        d = _load(session_id)
        d["summary"] = summary.strip()
        _save(session_id, d)

    def get_summary(self, session_id: str) -> str:
        return _load(session_id)["summary"]

    # ── Turn history ──────────────────────────────────────────────────────────

    def add_turn(self, session_id: str, user: str, assistant: str) -> None:
        d = _load(session_id)
        d["turns"].append({"user_input": user, "ai_response_text": assistant})
        if len(d["turns"]) > MEMORY_HISTORY_WINDOW:
            d["turns"] = d["turns"][-MEMORY_HISTORY_WINDOW:]
        _save(session_id, d)

    def get_recent_turns(self, session_id: str) -> List[Dict]:
        return list(_load(session_id)["turns"][-MEMORY_SUMMARY_TURNS:])

    # ── Report slots ──────────────────────────────────────────────────────────

    def update_slot(self, session_id: str, key: str, value: Any) -> None:
        d = _load(session_id)
        d["slots"][key] = value
        _save(session_id, d)

    def get_slots(self, session_id: str) -> Dict:
        return dict(_load(session_id)["slots"])

    def is_slots_complete(self, session_id: str) -> bool:
        """True when topic is set AND at least 2 key_facts have been collected."""
        slots = _load(session_id)["slots"]
        has_topic = bool(slots.get("topic"))
        key_facts = slots.get("key_facts") or []
        has_facts = isinstance(key_facts, list) and len(key_facts) >= 2
        return has_topic and has_facts

    def missing_slots(self, session_id: str) -> List[str]:
        slots = _load(session_id)["slots"]
        missing = []
        if not slots.get("topic"):
            missing.append("topic")
        key_facts = slots.get("key_facts") or []
        if not (isinstance(key_facts, list) and len(key_facts) >= 2):
            missing.append("key_facts")
        return missing

    def is_report_in_progress(self, session_id: str) -> bool:
        return bool(_load(session_id)["slots"].get("_workflow_active"))

    def mark_report_started(self, session_id: str) -> None:
        d = _load(session_id)
        d["slots"]["_workflow_active"] = True
        _save(session_id, d)

    def clear_slots(self, session_id: str) -> None:
        d = _load(session_id)
        d["slots"] = {"_workflow_active": False, "_report_done": True}
        _save(session_id, d)

    def set_last_report_urls(self, session_id: str, download_url: Optional[str], pptx_url: Optional[str]) -> None:
        d = _load(session_id)
        d["last_report"] = {"download_url": download_url, "pptx_url": pptx_url}
        _save(session_id, d)

    def get_last_report_urls(self, session_id: str) -> Dict:
        return dict(_load(session_id).get("last_report") or {})

    # ── Context assembly ──────────────────────────────────────────────────────

    def get_context_block(self, session_id: str) -> str:
        d = _load(session_id)
        parts = []

        summary = d["summary"].strip()
        if summary:
            parts.append(f"[CONVERSATION SUMMARY]\n{summary}")

        facts = d["facts"]
        if facts:
            lines = "\n".join(f"  {k}: {v}" for k, v in facts.items())
            parts.append(
                f"[USER PROFILE — everything known about the user]\n{lines}\n"
                f"Use this to answer recall questions. Do NOT ask for any of this again."
            )

        turns = d["turns"]
        if turns:
            recent = turns[-MEMORY_SUMMARY_TURNS:]
            turn_lines = "\n".join(
                f"User: {t['user_input']}\nAssistant: {t['ai_response_text']}"
                for t in recent if t.get("user_input")
            )
            if turn_lines:
                parts.append(
                    f"[RECENT CONVERSATION — topic already discussed, do NOT ask again]\n{turn_lines}"
                )

        slots = d["slots"]
        filled = {k: v for k, v in slots.items() if v and not str(k).startswith("_")}
        if filled:
            slot_lines = "\n".join(f"  {k}: {v}" for k, v in filled.items())
            parts.append(f"[CONFIRMED REPORT SLOTS — do NOT ask for these again]\n{slot_lines}")

        return "\n\n".join(parts)

    # ── Full session clear ────────────────────────────────────────────────────

    def clear_session(self, session_id: str) -> None:
        try:
            _path(session_id).unlink(missing_ok=True)
        except Exception as e:
            _log.warning("[Memory] failed to delete session=%s: %s", session_id, e)
