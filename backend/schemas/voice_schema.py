from pydantic import BaseModel


# ── Inbound request payloads ──────────────────────────────────────────────────

class VoiceStreamPayload(BaseModel):
    """Payload for the /process-transcript endpoint."""
    userId: str
    sessionId: str
    textChunk: str


# ── Outbound response envelopes ───────────────────────────────────────────────

class WelcomeResponse(BaseModel):
    status: str
    audio_url: str


class TTSResponse(BaseModel):
    status: str
    audio_url: str


class TokenResponse(BaseModel):
    status: str
    token: str
    server_url: str


class VoiceEnvelopeResponse(BaseModel):
    """Generic voice pipeline response envelope (chat + document routes)."""
    status: str
    user_said: str
    ai_response_text: str
    download_url: str | None = None
    voice_response_url: str | None = None
    pptx_url: str | None = None
