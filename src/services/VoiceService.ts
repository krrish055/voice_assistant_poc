// Allowlist: only allow requests to the configured backend origin
const _RAW_API = process.env.REACT_APP_API_URL || 'http://localhost:8000';
const API = (() => {
  try {
    const url = new URL(_RAW_API);
    // Only allow http/https and known safe origins
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
}

// ── FAQ Knowledge Base (POC: hardcoded — production mein Redis cache se serve hoga) ──
// NOTE: Ye answers abhi client-side map mein hain for POC demo.
// Production architecture mein ye Redis hash (faq:<normalized_key> -> answer)
// mein store honge aur backend /api/faq/lookup endpoint ke through serve honge.
export const FAQ_MAP: Record<string, string> = {
  'what services does intimetec offer':
    'InTimeTec offers end-to-end software engineering, AI & cognitive automation pipelines, security compliance consulting, cloud infrastructure, and product development — serving clients across the US, India, UAE, Saudi Arabia, Netherlands, Australia, South Korea, and Colombia.',

  'how can ai help my compliance process':
    'Our AI compliance engine automates audit trail generation, flags policy deviations in real time, transcribes and classifies voice inputs into structured reports, and reduces manual review effort by up to 80% — all hands-free via our voice pipeline.',

  'can i generate a report from this session':
    'Yes! Once your voice session completes, the system automatically generates a structured PDF compliance report. You will see a "Download Compliance Report" button appear on the console as soon as it is ready.',

  'what industries does intimetec serve':
    'InTimeTec serves Healthcare, Government & Public Sector, Agriculture Technology, Logistics & Dispatch, Finance, and Enterprise IT. Products like NextGen Ag Tech, Court Access Tracking System, and ClearSpend are purpose-built for these verticals.',

  'how do i get started with intimetec':
    'You can start right here — this voice session connects you directly to our AI compliance node. For enterprise onboarding, visit intimetec.com or speak your requirements now and our system will generate a structured intake report automatically.',
};

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
