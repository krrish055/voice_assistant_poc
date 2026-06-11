import re
import time
from pathlib import Path

REPORTS_DIR = str((Path(__file__).parent / 'reports').resolve())

_SESSION_RE        = re.compile(r'^[a-zA-Z0-9_\-]{1,64}$')
ALLOWED_AUDIO_MIME = {'audio/webm', 'audio/wav', 'audio/mpeg', 'audio/ogg', 'audio/flac', 'application/octet-stream'}
ALLOWED_AUDIO_EXT  = {'.webm', '.wav', '.mp3', '.m4a', '.ogg', '.flac'}


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
            if now - f.stat().st_mtime > 86400:
                f.unlink(missing_ok=True)
    except Exception:
        pass
