const API = process.env.REACT_APP_API_URL || 'http://localhost:8000';
const TIMEOUT = 30_000;

export interface AudioStreamResponse {
  status: 'success' | 'error';
  user_said?: string;
  ai_response_text?: string;
  voice_response_url?: string | null;
  download_url?: string | null;
  message?: string;
}

export interface LiveKitToken {
  status: string;
  token: string;
  server_url: string;
}

class VoiceService {
  private static instance: VoiceService;
  private constructor() {}

  static getInstance(): VoiceService {
    if (!VoiceService.instance) VoiceService.instance = new VoiceService();
    return VoiceService.instance;
  }

  async getLiveKitToken(roomName: string, identity: string): Promise<LiveKitToken> {
    try {
      const res = await fetch(
        `${API}/api/voice/get-token?roomName=${encodeURIComponent(roomName)}&identity=${encodeURIComponent(identity)}`
      );
      if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
      return await res.json();
    } catch (e) {
      throw new Error(e instanceof Error ? e.message : 'Token fetch failed');
    }
  }

  // Shared dispatcher — audio blob path and text fallback path both resolve here
  private async postAudioStream(form: FormData): Promise<AudioStreamResponse> {
    try {
      const controller = new AbortController();
      const timer = setTimeout(() => controller.abort(), TIMEOUT);
      const res = await fetch(`${API}/api/voice/process-audio-stream`, {
        method: 'POST',
        body: form,
        signal: controller.signal,
      });
      clearTimeout(timer);
      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: res.statusText }));
        return { status: 'error', message: err.detail ?? res.statusText };
      }
      return await res.json();
    } catch (e) {
      return { status: 'error', message: e instanceof Error ? e.message : 'Request failed' };
    }
  }

  async sendAudioBlob(userId: string, sessionId: string, blob: Blob): Promise<AudioStreamResponse> {
    const form = new FormData();
    form.append('userId', userId);
    form.append('sessionId', sessionId);
    form.append('audio_blob', blob, 'recording.webm');
    return this.postAudioStream(form);
  }

  async sendTextFallback(userId: string, sessionId: string, text: string): Promise<AudioStreamResponse> {
    const form = new FormData();
    form.append('userId', userId);
    form.append('sessionId', sessionId);
    form.append('text_fallback', text);
    return this.postAudioStream(form);
  }

  audioUrl(path: string): string {
    return `${API}${path}`;
  }
}

export default VoiceService.getInstance();
