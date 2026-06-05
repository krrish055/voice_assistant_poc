# Standard library
import json
import os
from datetime import datetime, timezone

# Local
from exceptions import StorageError


# DB file path resolved relative to this file so it works from any working directory
_DB_FILE = os.path.join(os.path.dirname(__file__), "db.json")


# ── Internal I/O ──────────────────────────────────────────────────────────────

def _read() -> list:
    if not os.path.exists(_DB_FILE):
        return []
    try:
        with open(_DB_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        raise StorageError(f"Failed to read DB: {e}") from e
    if isinstance(data, dict):
        data = data.get("conversations", [])
    if not isinstance(data, list):
        return []
    return [record for record in data if isinstance(record, dict)]


def _write(data: list) -> None:
    try:
        with open(_DB_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    except OSError as e:
        raise StorageError(f"Failed to write DB: {e}") from e


# ── Query Functions ───────────────────────────────────────────────────────────

def save_turn(entry: dict) -> None:
    """Persist a single conversation turn with a UTC timestamp."""
    data = _read()
    entry["timestamp"] = datetime.now(timezone.utc).isoformat()
    data.append(entry)
    _write(data)


def get_session_history(session_id: str) -> list:
    """Return all turns for a given session, ordered by insertion order."""
    return [r for r in _read() if r.get("session_id") == session_id]


def get_conversations_by_user(user_id: str) -> list:
    """Return all conversation records for a given user."""
    return [r for r in _read() if r.get("user_id") == user_id]
