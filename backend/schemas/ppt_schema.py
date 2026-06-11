from pydantic import BaseModel


class PptxDownloadResponse(BaseModel):
    """Response envelope returned after a PPTX document is ready for download."""
    status: str
    user_said: str
    ai_response_text: str
    pptx_url: str | None = None
    download_url: str | None = None
    voice_response_url: str | None = None
