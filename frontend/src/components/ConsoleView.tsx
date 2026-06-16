// ── C4: ConsoleView — Enterprise AI Interface ─────────────────────────────────
import React, { useState, useRef, useEffect, useMemo } from 'react';
import type { Phase, AppLog } from '../types';
import VoiceService from '../services/VoiceService';

const K = {
  bg:        '#0A0B0F',
  surface:   '#111318',
  surfaceHi: '#16181F',
  glass:     'rgba(255,255,255,0.035)',
  glassBorder:'rgba(255,255,255,0.08)',
  pri:  '#F4F6FA',
  sec:  '#8A93A8',
  ter:  '#4A5568',
  mono: "'JetBrains Mono', monospace",
  sans: "'Inter', system-ui, sans-serif",
  accent:    '#6366F1',
  accentLo:  'rgba(99,102,241,0.12)',
  accentMid: 'rgba(99,102,241,0.25)',
  green:  '#22C55E',
  greenLo:'rgba(34,197,94,0.1)',
  amber:  '#F59E0B',
  amberLo:'rgba(245,158,11,0.1)',
  red:    '#EF4444',
  redLo:  'rgba(239,68,68,0.1)',
  r:    '10px',
  rLg:  '16px',
  rFull:'9999px',
};

const CSS = `
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&family=JetBrains+Mono:wght@400;500&display=swap');
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

@keyframes orb-breathe {
  0%,100% { transform: scale(1);    box-shadow: 0 0 40px rgba(99,102,241,0.15), 0 0 80px rgba(99,102,241,0.06); }
  50%     { transform: scale(1.04); box-shadow: 0 0 60px rgba(99,102,241,0.25), 0 0 120px rgba(99,102,241,0.1); }
}
@keyframes orb-listen {
  0%,100% { transform: scale(1);    box-shadow: 0 0 40px rgba(34,197,94,0.2),  0 0 80px rgba(34,197,94,0.08); }
  50%     { transform: scale(1.06); box-shadow: 0 0 70px rgba(34,197,94,0.35), 0 0 130px rgba(34,197,94,0.12); }
}
@keyframes orb-think {
  0%   { box-shadow: 0 0 40px rgba(245,158,11,0.15); }
  33%  { box-shadow: 0 0 55px rgba(245,158,11,0.28); }
  66%  { box-shadow: 0 0 45px rgba(99,102,241,0.2);  }
  100% { box-shadow: 0 0 40px rgba(245,158,11,0.15); }
}
@keyframes orb-speak {
  0%,100% { transform: scale(1);    box-shadow: 0 0 50px rgba(99,102,241,0.3),  0 0 100px rgba(99,102,241,0.12); }
  50%     { transform: scale(1.08); box-shadow: 0 0 80px rgba(99,102,241,0.45), 0 0 150px rgba(99,102,241,0.18); }
}
@keyframes ring-cw  { to { transform: translate(-50%,-50%) rotate(360deg);  } }
@keyframes ring-ccw { to { transform: translate(-50%,-50%) rotate(-360deg); } }
@keyframes fade-up   { from{opacity:0;transform:translateY(8px)} to{opacity:1;transform:translateY(0)} }
@keyframes slide-in  { from{opacity:0;transform:translateX(-8px)} to{opacity:1;transform:translateX(0)} }
@keyframes msg-in    { from{opacity:0;transform:translateY(6px)} to{opacity:1;transform:translateY(0)} }
@keyframes pulse-dot { 0%,100%{opacity:1;transform:scale(1)} 50%{opacity:0.4;transform:scale(0.7)} }
@keyframes think-dot { 0%,80%,100%{transform:translateY(0)} 40%{transform:translateY(-5px)} }
::-webkit-scrollbar { width: 3px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: ${K.ter}; border-radius: 4px; }
:focus-visible { outline: 2px solid ${K.accent}; outline-offset: 2px; border-radius: 6px; }
@media (prefers-reduced-motion: reduce) { *, *::before, *::after { animation: none !important; transition: none !important; } }
`;

type UIState = 'idle' | 'listening' | 'thinking' | 'speaking';
function toUIState(p: Phase): UIState {
  if (p === 'speaking')                     return 'speaking';
  if (p === 'processing')                   return 'thinking';
  if (p === 'waiting' || p === 'recording') return 'listening';
  return 'idle';
}

function fakeTranslate(text: string): string | null {
  if (/[\u0900-\u097F]/.test(text)) return `[EN] ${text.replace(/[\u0900-\u097F]/g, '').trim() || 'Translation available'}`;
  if (text.length > 4 && /^[a-zA-Z\s.,?!'"]+$/.test(text)) return `[HI] अनुवाद उपलब्ध है`;
  return null;
}

/* ── Animated Orb ───────────────────────────────────────────────────────────── */
const Orb: React.FC<{ state: UIState }> = ({ state }) => {
  const anim = {
    idle:      'orb-breathe 4s ease-in-out infinite',
    listening: 'orb-listen 2s ease-in-out infinite',
    thinking:  'orb-think 2s ease-in-out infinite',
    speaking:  'orb-speak 1.5s ease-in-out infinite',
  }[state];
  const color = {
    idle:      K.accent,
    listening: K.green,
    thinking:  K.amber,
    speaking:  K.accent,
  }[state];
  return (
    <div style={{ position: 'relative', width: 120, height: 120, flexShrink: 0, overflow: 'visible' }}>
      {/* Orbit ring 1 */}
      <div style={{
        position: 'absolute', top: '50%', left: '50%',
        width: 160, height: 160,
        border: `1px solid ${color}22`,
        borderRadius: '50%',
        transform: 'translate(-50%,-50%)',
        animation: 'ring-cw 8s linear infinite',
      }} />
      {/* Orbit ring 2 */}
      <div style={{
        position: 'absolute', top: '50%', left: '50%',
        width: 190, height: 190,
        border: `1px solid ${color}14`,
        borderRadius: '50%',
        transform: 'translate(-50%,-50%)',
        animation: 'ring-ccw 12s linear infinite',
      }} />
      {/* Core orb */}
      <div style={{
        position: 'absolute', top: '50%', left: '50%',
        transform: 'translate(-50%,-50%)',
        width: 100, height: 100, borderRadius: '50%',
        background: `radial-gradient(circle at 35% 35%, ${color}55, ${color}18 60%, transparent)`,
        border: `1.5px solid ${color}40`,
        animation: anim,
        display: 'flex', alignItems: 'center', justifyContent: 'center',
      }}>
        <div style={{
          width: 36, height: 36, borderRadius: '50%',
          background: `radial-gradient(circle at 40% 40%, #fff4, ${color}88)`,
        }} />
      </div>
    </div>
  );
};

/* ── Conversation Turn ──────────────────────────────────────────────────────── */
const ConversationTurn: React.FC<{ log: AppLog; translation: string | null }> = ({ log, translation }) => {
  if (log.source === 'SYSTEM') return null;
  const isAI = log.source === 'AI';
  const labelColor = isAI ? K.accent : K.green;
  return (
    <div style={{ borderBottom: `1px solid ${K.glassBorder}`, padding: '20px 0', animation: 'msg-in 0.3s ease-out' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
        <div style={{ width: 6, height: 6, borderRadius: '50%', background: labelColor, boxShadow: `0 0 6px ${labelColor}` }} />
        <span style={{ fontFamily: K.sans, fontSize: 11, fontWeight: 600, color: labelColor, letterSpacing: '0.04em', textTransform: 'uppercase' }}>
          {isAI ? 'AI Response' : 'You said'}
        </span>
        <span style={{ fontFamily: K.mono, fontSize: 10, color: K.ter, marginLeft: 'auto' }}>{log.ts}</span>
      </div>
      <p style={{ fontFamily: K.sans, fontSize: 15, color: K.pri, lineHeight: 1.65, marginBottom: translation ? 12 : 0 }}>{log.message}</p>
      {translation && (
        <div style={{ display: 'flex', alignItems: 'flex-start', gap: 10, padding: '10px 14px', borderRadius: K.r, background: K.glass, border: `1px solid ${K.glassBorder}` }}>
          <span style={{ fontFamily: K.mono, fontSize: 9, color: K.sec, letterSpacing: 1, textTransform: 'uppercase', paddingTop: 2 }}>
            {isAI ? 'HI' : 'EN'}
          </span>
          <p style={{ fontFamily: K.sans, fontSize: 13, color: K.sec, lineHeight: 1.6, margin: 0, fontStyle: 'italic' }}>{translation}</p>
        </div>
      )}
    </div>
  );
};

/* ── Timeline ───────────────────────────────────────────────────────────────── */
interface TimelineEvent { id: string; ts: string; label: string; type: 'connect' | 'user' | 'ai' | 'system'; }
const TIMELINE_COLORS = { connect: K.green, user: K.green, ai: K.accent, system: K.ter };
const Timeline: React.FC<{ events: TimelineEvent[] }> = ({ events }) => (
  <div style={{ display: 'flex', flexDirection: 'column', gap: 0 }}>
    {events.map((ev, i) => (
      <div key={ev.id} style={{ display: 'flex', gap: 12, paddingBottom: 16, animation: 'slide-in 0.3s ease-out' }}>
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', flexShrink: 0 }}>
          <div style={{ width: 8, height: 8, borderRadius: '50%', background: TIMELINE_COLORS[ev.type], boxShadow: i === 0 ? `0 0 8px ${TIMELINE_COLORS[ev.type]}` : 'none', marginTop: 2 }} />
          {i < events.length - 1 && <div style={{ width: 1, flex: 1, background: K.glassBorder, marginTop: 4, minHeight: 12 }} />}
        </div>
        <div>
          <p style={{ fontFamily: K.mono, fontSize: 9, color: K.ter, marginBottom: 2 }}>{ev.ts}</p>
          <p style={{ fontFamily: K.sans, fontSize: 12, color: ev.type === 'connect' ? K.pri : K.sec, lineHeight: 1.4 }}>{ev.label}</p>
        </div>
      </div>
    ))}
  </div>
);

/* ── Quick Actions ──────────────────────────────────────────────────────────── */
const ACTIONS = [
  { id: 'audit',     icon: '📋', label: 'Audit Report',     desc: 'Generate full compliance audit',  query: 'Generate an audit report for this session' },
  { id: 'risk',      icon: '⚠️',  label: 'Risk Analysis',    desc: 'Identify compliance risks',       query: 'Analyze compliance risks in this session' },
  { id: 'checklist', icon: '✅', label: 'Compliance Check', desc: 'Review against standards',        query: 'Run a compliance checklist review' },
  { id: 'policy',    icon: '📌', label: 'Policy Review',    desc: 'Check policy alignment',          query: 'Review policies discussed in this session' },
] as const;

const QuickActions: React.FC<{ onAction: (q: string) => void; dlUrl: string | null; pptxUrl: string | null }> = ({ onAction, dlUrl, pptxUrl }) => (
  <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
    {ACTIONS.map(a => (
      <button key={a.id} onClick={() => onAction(a.query)} style={{
        display: 'flex', alignItems: 'center', gap: 12,
        padding: '12px 14px', borderRadius: K.r,
        background: K.glass, border: `1px solid ${K.glassBorder}`,
        cursor: 'pointer', textAlign: 'left', width: '100%',
        transition: 'background 0.15s, border-color 0.15s',
      }}
        onMouseEnter={e => { e.currentTarget.style.background = K.accentLo; e.currentTarget.style.borderColor = K.accentMid; }}
        onMouseLeave={e => { e.currentTarget.style.background = K.glass;    e.currentTarget.style.borderColor = K.glassBorder; }}
      >
        <span style={{ fontSize: 18, flexShrink: 0 }}>{a.icon}</span>
        <div>
          <p style={{ fontFamily: K.sans, fontSize: 12, fontWeight: 500, color: K.pri, margin: '0 0 2px' }}>{a.label}</p>
          <p style={{ fontFamily: K.sans, fontSize: 11, color: K.ter, margin: 0 }}>{a.desc}</p>
        </div>
      </button>
    ))}
    {(dlUrl || pptxUrl) && (
      <div style={{ marginTop: 4, padding: '10px 14px', borderRadius: K.r, background: K.accentLo, border: `1px solid ${K.accentMid}`, display: 'flex', flexDirection: 'column', gap: 6 }}>
        <p style={{ fontFamily: K.mono, fontSize: 9, color: K.accent, letterSpacing: 1.5, textTransform: 'uppercase', marginBottom: 4 }}>Reports Ready</p>
        {dlUrl   && <a href={VoiceService.fullUrl(dlUrl)}   target="_blank" rel="noreferrer" style={{ fontFamily: K.sans, fontSize: 12, color: K.accent, textDecoration: 'none', fontWeight: 500 }}>↓ Compliance PDF</a>}
        {pptxUrl && <a href={VoiceService.fullUrl(pptxUrl)} target="_blank" rel="noreferrer" style={{ fontFamily: K.sans, fontSize: 12, color: K.accent, textDecoration: 'none', fontWeight: 500 }}>↓ Presentation</a>}
      </div>
    )}
  </div>
);

/* ── Command Dock ───────────────────────────────────────────────────────────── */
interface DockProps {
  isMicMuted: boolean; isSpeakerMuted: boolean; translationOn: boolean; transcriptOpen: boolean;
  onToggleMic: () => void; onToggleSpeaker: () => void; onToggleTranslation: () => void;
  onToggleTranscript: () => void; onDisconnect: () => void;
}
const DockBtn: React.FC<{ label: string; active?: boolean; danger?: boolean; onClick: () => void; children: React.ReactNode }> = ({ label, active, danger, onClick, children }) => (
  <button onClick={onClick} aria-label={label} title={label} style={{
    width: 44, height: 44, borderRadius: '50%',
    border: `1px solid ${danger ? K.red + '40' : active ? K.accentMid : K.glassBorder}`,
    cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center',
    background: danger ? K.redLo : active ? K.accentLo : K.glass,
    transition: 'all 0.15s', color: danger ? K.red : active ? K.accent : K.sec, fontSize: 18,
  }}
    onMouseEnter={e => { e.currentTarget.style.transform = 'scale(1.08)'; }}
    onMouseLeave={e => { e.currentTarget.style.transform = 'scale(1)'; }}
  >{children}</button>
);
const CommandDock: React.FC<DockProps> = ({ isMicMuted, isSpeakerMuted, translationOn, transcriptOpen, onToggleMic, onToggleSpeaker, onToggleTranslation, onToggleTranscript, onDisconnect }) => (
  <div style={{ display: 'inline-flex', alignItems: 'center', gap: 8, padding: '10px 16px', borderRadius: K.rFull, background: 'rgba(17,19,24,0.85)', backdropFilter: 'blur(20px)', border: `1px solid ${K.glassBorder}`, boxShadow: '0 8px 32px rgba(0,0,0,0.4)' }}>
    <DockBtn label={isMicMuted ? 'Unmute mic' : 'Mute mic'} danger={isMicMuted} onClick={onToggleMic}>
      {isMicMuted
        ? <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><line x1="2" y1="2" x2="22" y2="22"/><path d="M18.9 13.2A6 6 0 0 0 12 7v-.2M6 6a6 6 0 0 0-.1 1v5a6 6 0 0 0 9.7 4.7M12 19v3m-4 0h8"/></svg>
        : <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><path d="M12 1a4 4 0 0 1 4 4v6a4 4 0 0 1-8 0V5a4 4 0 0 1 4-4z"/><path d="M19 10a7 7 0 0 1-14 0M12 19v4M8 23h8"/></svg>}
    </DockBtn>
    <DockBtn label={isSpeakerMuted ? 'Unmute speaker' : 'Mute speaker'} danger={isSpeakerMuted} onClick={onToggleSpeaker}>
      {isSpeakerMuted
        ? <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"/><line x1="23" y1="9" x2="17" y2="15"/><line x1="17" y1="9" x2="23" y2="15"/></svg>
        : <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"/><path d="M19.07 4.93a10 10 0 0 1 0 14.14M15.54 8.46a5 5 0 0 1 0 7.07"/></svg>}
    </DockBtn>
    <DockBtn label="Toggle translation" active={translationOn} onClick={onToggleTranslation}>
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><circle cx="12" cy="12" r="10"/><path d="M2 12h20M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"/></svg>
    </DockBtn>
    <DockBtn label="Toggle transcript" active={transcriptOpen} onClick={onToggleTranscript}>
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>
    </DockBtn>
    <div style={{ width: 1, height: 24, background: K.glassBorder, margin: '0 4px' }} />
    <DockBtn label="End session" danger onClick={onDisconnect}>
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round"><rect x="3" y="3" width="18" height="18" rx="2"/></svg>
    </DockBtn>
  </div>
);

/* ── Text Input ─────────────────────────────────────────────────────────────── */
const TextInput: React.FC<{ onSend: (t: string) => void }> = ({ onSend }) => {
  const [val, setVal] = useState('');
  const submit = () => { const t = val.trim(); if (!t) return; setVal(''); onSend(t); };
  return (
    <div style={{ display: 'flex', gap: 10, padding: '12px 16px', background: K.glass, border: `1px solid ${K.glassBorder}`, borderRadius: K.rLg, backdropFilter: 'blur(12px)', transition: 'border-color 0.15s' }}
      onFocusCapture={e => (e.currentTarget.style.borderColor = K.accentMid)}
      onBlurCapture={e  => (e.currentTarget.style.borderColor = K.glassBorder)}
    >
      <input value={val} onChange={e => setVal(e.target.value)} onKeyDown={e => e.key === 'Enter' && !e.shiftKey && (e.preventDefault(), submit())}
        placeholder="Type a message or ask the AI…" aria-label="Message input"
        style={{ flex: 1, background: 'transparent', border: 'none', outline: 'none', fontFamily: K.sans, fontSize: 14, color: K.pri }}
      />
      <button onClick={submit} disabled={!val.trim()} aria-label="Send"
        style={{ padding: '8px 18px', borderRadius: K.r, border: 'none', background: val.trim() ? K.accent : K.ter, color: '#fff', fontFamily: K.sans, fontSize: 13, fontWeight: 500, cursor: val.trim() ? 'pointer' : 'default', transition: 'background 0.15s' }}>
        Send
      </button>
    </div>
  );
};

/* ── Props ──────────────────────────────────────────────────────────────────── */
interface Props {
  phase: Phase; amplitude: number; logs: AppLog[];
  dlUrl: string | null; pptxUrl: string | null; sessionId: string;
  isMicMuted: boolean; isSpeakerMuted: boolean;
  onDisconnect: () => void; onToggleMic: () => void;
  onToggleSpeaker: () => void; onDispatch: (t: string) => void;
  audioElement: HTMLAudioElement | null;
}

/* ── Root ───────────────────────────────────────────────────────────────────── */
export const ConsoleView: React.FC<Props> = ({
  phase, logs, dlUrl, pptxUrl, sessionId,
  isMicMuted, isSpeakerMuted,
  onDisconnect, onToggleMic, onToggleSpeaker, onDispatch,
}) => {
  const [translationOn,  setTranslationOn]  = useState(true);
  const [transcriptOpen, setTranscriptOpen] = useState(true);
  const feedRef = useRef<HTMLDivElement>(null);
  const uiState = toUIState(phase);

  const timeline: TimelineEvent[] = useMemo(() => {
    const events: TimelineEvent[] = [{ id: 'connect', ts: logs[logs.length - 1]?.ts ?? '--:--:--', label: 'Session connected', type: 'connect' }];
    logs.slice().reverse().forEach(l => {
      if (l.source === 'USER') events.push({ id: l.id, ts: l.ts, label: 'User spoke',    type: 'user' });
      if (l.source === 'AI')   events.push({ id: l.id, ts: l.ts, label: 'AI responded',  type: 'ai' });
      if (l.source === 'SYSTEM' && l.message.includes('report')) events.push({ id: l.id + 's', ts: l.ts, label: 'Report generated', type: 'system' });
    });
    return events.slice(0, 12);
  }, [logs]);

  const chatLogs = useMemo(() => logs.filter(l => l.source !== 'SYSTEM').slice().reverse(), [logs]);
  useEffect(() => { if (feedRef.current) feedRef.current.scrollTop = feedRef.current.scrollHeight; }, [chatLogs.length]);

  const stateColor = uiState === 'listening' ? K.green : uiState === 'thinking' ? K.amber : uiState === 'speaking' ? K.accent : K.ter;

  return (
    <>
      <style>{CSS}</style>
      <div style={{ height: '100%', display: 'flex', flexDirection: 'column', background: K.bg, color: K.pri, fontFamily: K.sans, overflow: 'hidden' }}>

        {/* NAV */}
        <nav style={{ height: 52, display: 'flex', alignItems: 'center', padding: '0 24px', borderBottom: `1px solid ${K.glassBorder}`, background: K.surface, flexShrink: 0, gap: 16 }}>
          <span style={{ fontFamily: K.sans, fontSize: 14, fontWeight: 600, color: K.pri }}>Compliance Advisor</span>
          <div style={{ display: 'flex', alignItems: 'center', gap: 5, padding: '3px 10px', borderRadius: K.rFull, background: K.greenLo, border: `1px solid ${K.green}25` }}>
            <div style={{ width: 5, height: 5, borderRadius: '50%', background: K.green, animation: 'pulse-dot 2s infinite' }} />
            <span style={{ fontFamily: K.mono, fontSize: 9, color: K.green, letterSpacing: 1, fontWeight: 500 }}>CONNECTED</span>
          </div>
          <div style={{ flex: 1 }} />
          <span style={{ fontFamily: K.mono, fontSize: 10, color: K.ter }}>{sessionId.slice(-10)}</span>
          {(dlUrl || pptxUrl) && (
            <div style={{ display: 'flex', gap: 8 }}>
              {dlUrl   && <a href={VoiceService.fullUrl(dlUrl)}   target="_blank" rel="noreferrer" style={{ fontFamily: K.sans, fontSize: 12, fontWeight: 500, color: K.accent, background: K.accentLo, border: `1px solid ${K.accentMid}`, borderRadius: K.r, padding: '4px 12px', textDecoration: 'none' }}>↓ PDF</a>}
              {pptxUrl && <a href={VoiceService.fullUrl(pptxUrl)} target="_blank" rel="noreferrer" style={{ fontFamily: K.sans, fontSize: 12, fontWeight: 500, color: K.accent, background: K.accentLo, border: `1px solid ${K.accentMid}`, borderRadius: K.r, padding: '4px 12px', textDecoration: 'none' }}>↓ PPTX</a>}
            </div>
          )}
          <button
            onClick={() => {
              const lines = (document.querySelector('[role="log"]') as HTMLElement)?.innerText ?? 'No transcript';
              const blob = new Blob([lines], { type: 'text/plain' });
              const a = document.createElement('a'); a.href = URL.createObjectURL(blob); a.download = `transcript-${sessionId.slice(-6)}.txt`; a.click();
            }}
            style={{ fontFamily: K.sans, fontSize: 12, fontWeight: 500, color: K.sec, background: K.glass, border: `1px solid ${K.glassBorder}`, borderRadius: K.r, padding: '4px 12px', cursor: 'pointer' }}
          >↓ Transcript</button>
        </nav>

        {/* BODY GRID */}
        <div style={{ flex: 1, display: 'grid', minHeight: 0, overflow: 'hidden', gridTemplateColumns: '260px 1fr 260px' }}>

          {/* LEFT — Timeline */}
          <div style={{ borderRight: `1px solid ${K.glassBorder}`, display: 'flex', flexDirection: 'column', overflow: 'hidden', background: K.surface }}>
            <div style={{ padding: '16px 16px 12px', borderBottom: `1px solid ${K.glassBorder}`, flexShrink: 0 }}>
              <p style={{ fontFamily: K.mono, fontSize: 9, color: K.ter, letterSpacing: 2, textTransform: 'uppercase' }}>Session Timeline</p>
            </div>
            <div style={{ flex: 1, overflowY: 'auto', padding: '16px' }}><Timeline events={timeline} /></div>
          </div>

          {/* CENTER — Orb + Conversation */}
          <div style={{ display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
            {/* Orb */}
            <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', padding: '28px 32px 20px', flexShrink: 0, gap: 14 }}>
              <Orb state={uiState} />
              <div style={{ display: 'inline-flex', alignItems: 'center', gap: 8, padding: '5px 14px', borderRadius: K.rFull, background: `${stateColor}12`, border: `1px solid ${stateColor}25` }}>
                <div style={{ width: 6, height: 6, borderRadius: '50%', background: stateColor, animation: uiState !== 'idle' ? 'pulse-dot 1.5s infinite' : 'none' }} />
                <span style={{ fontFamily: K.sans, fontSize: 12, fontWeight: 500, color: stateColor }}>
                  {uiState === 'listening' ? 'Listening — speak now' : uiState === 'thinking' ? 'Processing your request' : uiState === 'speaking' ? 'AI is responding' : 'Ready'}
                </span>
                {uiState === 'thinking' && (
                  <span style={{ display: 'inline-flex', gap: 3 }}>
                    {[0,1,2].map(i => <span key={i} style={{ width: 4, height: 4, borderRadius: '50%', background: K.amber, animation: `think-dot 1.2s ease-in-out ${i*0.15}s infinite`, display: 'inline-block' }} />)}
                  </span>
                )}
              </div>
            </div>

            {/* Conversation feed */}
            {transcriptOpen && (
              <div ref={feedRef} style={{ flex: 1, overflowY: 'auto', padding: '0 32px 16px', borderTop: `1px solid ${K.glassBorder}` }} role="log" aria-live="polite">
                {chatLogs.length === 0
                  ? <div style={{ padding: '40px 0', textAlign: 'center' }}><p style={{ fontFamily: K.sans, fontSize: 13, color: K.ter, lineHeight: 1.7 }}>Your conversation will appear here.<br/>Speak or type a message to begin.</p></div>
                  : chatLogs.map(log => <ConversationTurn key={log.id} log={log} translation={translationOn ? fakeTranslate(log.message) : null} />)
                }
              </div>
            )}
          </div>

          {/* RIGHT — Quick Actions */}
          <div style={{ borderLeft: `1px solid ${K.glassBorder}`, display: 'flex', flexDirection: 'column', overflow: 'hidden', background: K.surface }}>
            <div style={{ padding: '16px 16px 12px', borderBottom: `1px solid ${K.glassBorder}`, flexShrink: 0 }}>
              <p style={{ fontFamily: K.mono, fontSize: 9, color: K.ter, letterSpacing: 2, textTransform: 'uppercase' }}>Quick Actions</p>
            </div>
            <div style={{ flex: 1, overflowY: 'auto', padding: '12px' }}>
              <QuickActions onAction={onDispatch} dlUrl={dlUrl} pptxUrl={pptxUrl} />
            </div>
          </div>
        </div>

        {/* BOTTOM BAR */}
        <div style={{ borderTop: `1px solid ${K.glassBorder}`, background: K.surface, flexShrink: 0, padding: '14px 24px', display: 'flex', alignItems: 'center', gap: 16 }}>
          <CommandDock
            isMicMuted={isMicMuted} isSpeakerMuted={isSpeakerMuted}
            translationOn={translationOn} transcriptOpen={transcriptOpen}
            onToggleMic={onToggleMic} onToggleSpeaker={onToggleSpeaker}
            onToggleTranslation={() => setTranslationOn(v => !v)}
            onToggleTranscript={() => setTranscriptOpen(v => !v)}
            onDisconnect={onDisconnect}
          />
          <div style={{ flex: 1 }}><TextInput onSend={onDispatch} /></div>
        </div>
      </div>
    </>
  );
};
