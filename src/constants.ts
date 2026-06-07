// ── C4: Application Constants ─────────────────────────────────────────────────
import { ITT_THEME as T } from './theme';
import type { Phase } from './types';

export const MIME          = MediaRecorder.isTypeSupported('audio/webm;codecs=opus') ? 'audio/webm;codecs=opus' : 'audio/webm';
export const SESSION_ID    = 'ITT_' + Date.now();

export const VAD_CONFIG = {
  SPEECH_START_MS : 200,
  SPEECH_STOP_MS  : 2200,
  MAX_RECORD_MS   : 25000,
  CALIB_FRAMES    : 90,
  NOISE_MULT      : 1.6,
  FFT_SIZE        : 256,
} as const;

export const PHASE_COLOR: Record<Phase, string> = {
  idle:       T.colors.textMuted,
  waiting:    T.colors.accentBlue,
  recording:  T.colors.accentTeal,
  processing: '#F59E0B',
  speaking:   '#10B981',
};

export const PHASE_GLOW: Record<Phase, string> = {
  idle:       'rgba(148,163,184,0.1)',
  waiting:    'rgba(0,119,182,0.25)',
  recording:  'rgba(72,202,228,0.4)',
  processing: 'rgba(245,158,11,0.35)',
  speaking:   'rgba(16,185,129,0.4)',
};

export const PHASE_LABEL: Record<Phase, string> = {
  idle:       'OFFLINE',
  waiting:    'LISTENING',
  recording:  'CAPTURING',
  processing: 'PROCESSING',
  speaking:   'AI SPEAKING',
};

export const PHASE_STATUS_TEXT: Record<Phase, string> = {
  idle:       'Compliance Node Offline',
  waiting:    'System Ready — Speak Now',
  recording:  'Capturing Audio Buffer…',
  processing: 'Executing Cognitive Pipeline…',
  speaking:   'AI Broadcast Active',
};

export const FAQ_QUESTIONS = [
  'What services does InTimeTec offer?',
  'How can AI help my compliance process?',
  'Can I generate a report from this session?',
  'What industries does InTimeTec serve?',
  'How do I get started with InTimeTec?',
] as const;

export const MISSION_CARDS = [
  { title: 'Software Engineering',  desc: 'Zero-friction VAD loop manages complete audio context changes. No push-to-talk required.' },
  { title: 'Security Compliance',   desc: 'Semantic guardrails filter restricted queries and flag compliance deviations in real time.' },
  { title: 'Cognitive Pipelines',   desc: 'Generate validated enterprise PDF reports from voice input using automated processing arrays.' },
] as const;

export const CLIENT_LOGOS = ['BerryIntl', 'MIMO Monitors', 'Credit Interlink', 'rf IDEAS', 'PlexTrac', 'NetAcent', 'RedBuilt'] as const;

export const HERO_IMAGES = [
  'https://images.unsplash.com/photo-1531482615713-2afd69097998?w=600&q=80',
  'https://images.unsplash.com/photo-1559839734-2b71ea197ec2?w=600&q=80',
  'https://images.unsplash.com/photo-1522071820081-009f0129c71c?w=600&q=80',
] as const;
