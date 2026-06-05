const API = process.env.REACT_APP_API_URL || 'http://localhost:8000';

export interface StreamResponse {
  status: 'success' | 'silence' | 'error';
  audio_url?: string | null;
  voice_response_url?: string | null;
  ai_response_text?: string;
  user_said?: string;
  download_url?: string | null;
}

const VoiceService = {
  fullUrl: (path: string) => `${API}${path}`,

  async fetchWelcome(): Promise<StreamResponse> {
    const res = await fetch(`${API}/api/voice/welcome`);
    return res.json();
  },

  async sendChunk(blob: Blob, sessionId: string): Promise<StreamResponse> {
    const form = new FormData();
    form.append('userId', 'user_open_mic');
    form.append('sessionId', sessionId);
    form.append('audio_blob', blob, 'chunk.webm');
    try {
      const res = await fetch(`${API}/api/voice/process-stream`, { method: 'POST', body: form });
      if (!res.ok) return { status: 'silence' };
      return res.json();
    } catch {
      return { status: 'silence' };
    }
  },

  async sendText(text: string, sessionId: string): Promise<StreamResponse> {
    const form = new FormData();
    form.append('userId', 'user_open_mic');
    form.append('sessionId', sessionId);
    form.append('text_fallback', text);
    try {
      const res = await fetch(`${API}/api/voice/process-stream`, { method: 'POST', body: form });
      if (!res.ok) return { status: 'error' };
      return res.json();
    } catch {
      return { status: 'error' };
    }
  },
};

export default VoiceService;
