// ── C4: Shared Domain Contracts ───────────────────────────────────────────────
// All domain-level types live here. No component imports types from each other.

export type Phase = 'idle' | 'waiting' | 'recording' | 'processing' | 'speaking';
export type LogSource = 'USER' | 'AI' | 'SYSTEM';

export interface AppLog {
  id: string;
  source: LogSource;
  message: string;
  ts: string;
}
