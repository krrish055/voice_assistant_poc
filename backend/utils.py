import json
import re
import time
from pathlib import Path

from config import PDF_MAX_AGE_SECONDS

REPORTS_DIR = str((Path(__file__).parent / 'reports').resolve())

_SESSION_RE        = re.compile(r'^[a-zA-Z0-9_\-]{1,64}$')
ALLOWED_AUDIO_MIME = {'audio/webm', 'audio/wav', 'audio/mpeg', 'audio/ogg', 'audio/flac', 'application/octet-stream'}
ALLOWED_AUDIO_EXT  = {'.webm', '.wav', '.mp3', '.m4a', '.ogg', '.flac'}


def extract_spoken_text(raw: dict, fallback: str = "") -> str:
    """Single canonical implementation for extracting the spoken reply from an LLM output dict.

    Handles:
    - Normal dict with ai_response_text
    - Dict with only ai_summary
    - Dict with sections array
    - ai_response_text field that itself contains a JSON blob
    """
    text = raw.get("ai_response_text", "")
    if not isinstance(text, str) or not text.strip():
        text = raw.get("ai_summary", "")
    if not isinstance(text, str) or not text.strip():
        sections = raw.get("sections") or []
        text = sections[0].get("body", "") if sections else ""
    text = (text or "").strip()
    if text.startswith("{"):
        try:
            inner = json.loads(text)
            text = (inner.get("ai_response_text") or "").strip()
        except Exception:
            text = ""
    brace_idx = text.find("{")
    if brace_idx > 0:
        text = text[:brace_idx].strip()
    return text or fallback


def validate_session(session_id: str) -> str:
    if not _SESSION_RE.fullmatch(session_id):
        raise ValueError(f'Invalid session ID: {session_id}')
    return session_id


def safe_path(directory: str, filename: str) -> Path:
    base   = Path(directory).resolve()
    target = (base / filename).resolve()
    if not str(target).startswith(str(base)):
        raise ValueError(f'Path traversal detected for: {filename}')
    return target


def cleanup_old_audio(directory: str, max_age_seconds: int = 3600) -> None:
    now = time.time()
    try:
        for f in Path(directory).glob('audio_*.mp3'):
            if now - f.stat().st_mtime > max_age_seconds:
                f.unlink(missing_ok=True)
        for f in Path(directory).glob('Report_*.pdf'):
            if now - f.stat().st_mtime > PDF_MAX_AGE_SECONDS:
                f.unlink(missing_ok=True)
    except Exception:
        pass
