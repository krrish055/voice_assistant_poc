// Allowlist: only allow requests to the configured backend origin
const _RAW_API = process.env.REACT_APP_API_URL || 'http://localhost:8000';
const API = (() => {
  try {
    const url = new URL(_RAW_API);
    if (!['http:', 'https:'].includes(url.protocol)) throw new Error();
    return url.origin;
  } catch {
    return 'http://localhost:8000';
  }
})();

export interface StreamResponse {
  status: 'success' | 'silence' | 'error';
  audio_url?: string | null;
  voice_response_url?: string | null;
  ai_response_text?: string;
  user_said?: string;
  download_url?: string | null;
  pptx_url?: string | null;
}

const VoiceService = {
  fullUrl: (path: string) => `${API}${path}`,

  async fetchFaq(): Promise<Record<string, string>> {
    try {
      const res = await fetch(`${API}/api/faq`);
      if (!res.ok) return {};
      return res.json();
    } catch {
      return {};
    }
  },

  async fetchWelcome(): Promise<StreamResponse> {
    const res = await fetch(`${API}/api/voice/welcome`);
    return res.json();
  },

  async sendChunk(blob: Blob, userId: string, sessionId: string): Promise<StreamResponse> {
    const form = new FormData();
    form.append('userId', userId);
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

  async speakFaq(text: string, sessionId: string): Promise<string | null> {
    const form = new FormData();
    form.append('text', text);
    form.append('sessionId', sessionId);
    try {
      const res = await fetch(`${API}/api/voice/tts`, { method: 'POST', body: form });
      if (!res.ok) return null;
      const data = await res.json();
      return data.audio_url ?? null;
    } catch {
      return null;
    }
  },

  async sendText(text: string, userId: string, sessionId: string): Promise<StreamResponse> {
    const form = new FormData();
    form.append('userId', userId);
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
