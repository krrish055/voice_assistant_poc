import json
import logging
from datetime import datetime, timezone
from pathlib import Path

from exceptions import StorageError

_log     = logging.getLogger(__name__)
_DB_BASE = Path(__file__).parent.parent.resolve()
_DB_FILE = (_DB_BASE / 'db.json').resolve()

assert str(_DB_FILE).startswith(str(_DB_BASE)), 'DB file path escapes project root.'


def _read() -> list:
    if not _DB_FILE.exists():
        return []
    try:
        data = json.loads(_DB_FILE.read_text(encoding='utf-8'))
    except (json.JSONDecodeError, OSError) as e:
        raise StorageError(f'Failed to read DB: {e}') from e
    if isinstance(data, dict):
        data = data.get('conversations', [])
    return [r for r in data if isinstance(r, dict)] if isinstance(data, list) else []


def _write(data: list) -> None:
    try:
        _DB_FILE.write_text(json.dumps(data, indent=2), encoding='utf-8')
    except OSError as e:
        raise StorageError(f'Failed to write DB: {e}') from e


def save_turn(entry: dict) -> None:
    data = _read()
    entry['timestamp'] = datetime.now(timezone.utc).isoformat()
    data.append(entry)
    _write(data)


def get_session_history(session_id: str) -> list:
    return [r for r in _read() if r.get('session_id') == session_id]


def get_conversations_by_user(user_id: str) -> list:
    return [r for r in _read() if r.get('user_id') == user_id]
