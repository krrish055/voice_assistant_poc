export interface VoicePayload {
  userId: string;
  sessionId: string;
  textChunk: string;
}

export interface VoiceResponse {
  status: 'success' | 'ignored' | 'error';
  ai_response_text?: string;
  next_step?: string;
  confidence_score?: number;
  message?: string;
  download_url?: string | null;
}

class VoiceService {
  private static instance: VoiceService;
  private apiUrl: string;
  private readonly REQUEST_TIMEOUT = 30000;

  private constructor() {
    this.apiUrl = process.env.REACT_APP_API_URL || 'http://localhost:8000';
  }

  static getInstance(): VoiceService {
    if (!VoiceService.instance) {
      VoiceService.instance = new VoiceService();
    }
    return VoiceService.instance;
  }

  async sendTranscriptChunk(payload: VoicePayload): Promise<VoiceResponse> {
    const abortController = new AbortController();
    const timeoutId = setTimeout(() => abortController.abort(), this.REQUEST_TIMEOUT);

    try {
      const response = await fetch(`${this.apiUrl}/api/voice/process-transcript`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(payload),
        signal: abortController.signal,
      });

      if (!response.ok) {
        return {
          status: 'error',
          message: `Server error: ${response.statusText}`,
        };
      }

      const data = await response.json();
      return data as VoiceResponse;
    } catch (error) {
      if (error instanceof TypeError && error.message === 'Failed to fetch') {
        return {
          status: 'error',
          message: 'Network connection failed',
        };
      }

      if (error instanceof Error && error.name === 'AbortError') {
        return {
          status: 'error',
          message: 'Request timeout',
        };
      }

      return {
        status: 'error',
        message: error instanceof Error ? error.message : 'Unknown error occurred',
      };
    } finally {
      clearTimeout(timeoutId);
    }
  }
}

export default VoiceService.getInstance();
