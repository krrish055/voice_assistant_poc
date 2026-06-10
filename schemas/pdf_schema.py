from pydantic import BaseModel


class PdfDownloadResponse(BaseModel):
    """Response envelope returned after a PDF report is ready for download."""
    status: str
    user_said: str
    ai_response_text: str
    download_url: str | None = None
    pptx_url: str | None = None
    voice_response_url: str | None = None
