// ── C4: ConsoleView — Enterprise AI Interface ─────────────────────────────────
import React, { useState, useRef, useEffect, useMemo } from 'react';
import type { Phase, AppLog } from '../types';
import VoiceService from '../services/VoiceService';

/* ══════════════════════════════════════════════════════════════════════════════
   TOKENS
══════════════════════════════════════════════════════════════════════════════ */
const K = {
  // Surfaces — dark premium, not hacker
  bg:        '#0A0B0F',
  surface:   '#111318',
  surfaceHi: '#16181F',
  glass:     'rgba(255,255,255,0.035)',
  glassBorder:'rgba(255,255,255,0.08)',

  // Typography
  pri:  '#F4F6FA',
  sec:  '#8A93A8',
  ter:  '#4A5568',
  mono: "'JetBrains Mono', monospace",
  sans: "'Inter', system-ui, sans-serif",

  // Single accent — indigo-blue. Used for ONE thing: active state.
  accent:    '#6366F1',
  accentLo:  'rgba(99,102,241,0.12)',
  accentMid: 'rgba(99,102,241,0.25)',

  // Semantic
  green:  '#22C55E',
  greenLo:'rgba(34,197,94,0.1)',
  amber:  '#F59E0B',
  amberLo:'rgba(245,158,11,0.1)',
  red:    '#EF4444',
  redLo:  'rgba(239,68,68,0.1)',

  // Geometry
  r:    '10px',
  rLg:  '16px',
  rFull:'9999px',
};

/* ══════════════════════════════════════════════════════════════════════════════
   STATE MODEL
══════════════════════════════════════════════════════════════════════════════ */
type UIState = 'idle' | 'listening' | 'thinking' | 'speaking';

function toUIState(p: Phase): UIState {
  if (p === 'speaking')                        return 'speaking';
  if (p === 'processing')                      return 'thinking';
  if (p === 'waiting' || p === 'recording')    return 'listening';
  return 'idle';
}

// Naive translation stub — in production replace with real i18n/translation API
function fakeTranslate(text: string): string | null {
  // If text contains Hindi characters, return an English stub
  if (/[\u0900-\u097F]/.test(text)) return `[EN] ${text.replace(/[\u0900-\u097F]/g, '').trim() || 'Translation available'}`;
  // If English, return Hindi stub
  if (text.length > 4 && /^[a-zA-Z\s.,?!'"]+$/.test(text))
    return `[HI] अनुवाद उपलब्ध है`;
  return null;
}

/* ══════════════════════════════════════════════════════════════════════════════
   CSS
══════════════════════════════════════════════════════════════════════════════ */
const CSS = `
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&family=JetBrains+Mono:wght@400;500&display=swap');

*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

/* ── Orb animations ───────────────────────────────────────────── */
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

/* Ring orbit */
@keyframes ring-cw  { to { transform: translate(-50%,-50%) rotate(360deg);  } }
@keyframes ring-ccw { to { transform: translate(-50%,-50%) rotate(-360deg); } }

/* Particles drift */
@keyframes drift-1 { 0%,100%{transform:translate(0,0) scale(1)} 33%{transform:translate(8px,-12px) scale(1.3)} 66%{transform:translate(-6px,8px) scale(0.8)} }
@keyframes drift-2 { 0%,100%{transform:translate(0,0) scale(1)} 33%{transform:translate(-10px,6px) scale(0.7)} 66%{transform:translate(7px,-9px) scale(1.2)} }
@keyframes drift-3 { 0%,100%{transform:translate(0,0) scale(1)} 50%{transform:translate(12px,10px) scale(1.4)} }

/* UI motion */
@keyframes fade-up   { from{opacity:0;transform:translateY(8px)} to{opacity:1;transform:translateY(0)} }
@keyframes slide-in  { from{opacity:0;transform:translateX(-8px)} to{opacity:1;transform:translateX(0)} }
@keyframes msg-in    { from{opacity:0;transform:translateY(6px)} to{opacity:1;transform:translateY(0)} }
@keyframes pulse-dot { 0%,100%{opacity:1;transform:scale(1)} 50%{opacity:0.4;transform:scale(0.7)} }
@keyframes think-dot { 0%,80%,100%{transform:translateY(0)} 40%{transform:translateY(-5px)} }
@keyframes bar-wave  { 0%,100%{transform:scaleY(0.3)} 50%{transform:scaleY(1)} }
@keyframes shimmer   { from{background-position:200% center} to{background-position:-200% center} }

/* Scrollbars */
::-webkit-scrollbar { width: 3px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: ${K.ter}; border-radius: 4px; }

/* Focus */
:focus-visible { outline: 2px solid ${K.accent}; outline-offset: 2px; border-radius: 6px; }

/* Reduced motion */
@media (prefers-reduced-motion: reduce) { *, *::before, *::after { animation: none !important; transition: none !important; } }
`;

/* ══════════════════════════════════════════════════════════════════════════════
   ORB — The signature element
   CSS-only state machine. No canvas, no JS animation.
══════════════════════════════════════════════════════════════════════════════ */
const ORB_CONFIG = {
  idle:      { anim: 'orb-breathe 4s ease-in-out infinite', core: K.accent,  ring1: K.accentMid, ring2: K.accentLo,  label: 'Standby'   },
  listening: { anim: 'orb-listen 2s ease-in-out infinite',  core: K.green,   ring1: K.greenLo,   ring2: K.greenLo,   label: 'Listening' },
  thinking:  { anim: 'orb-think 2.5s ease-in-out infinite', core: K.amber,   ring1: K.amberLo,   ring2: K.accentLo,  label: 'Thinking'  },
  speaking:  { anim: 'orb-speak 1.8s ease-in-out infinite', core: K.accent,  ring1: K.accentMid, ring2: K.accentLo,  label: 'Speaking'  },
};

const Orb: React.FC<{ state: UIState }> = ({ state }) => {
  const cfg = ORB_CONFIG[state];
  return (
    <div style={{ position: 'relative', width: 200, height: 200, flexShrink: 0 }}>
      {/* Outer ambient glow */}
      <div style={{
        position: 'absolute', inset: -32, borderRadius: '50%',
        background: `radial-gradient(circle, ${cfg.ring2} 0%, transparent 70%)`,
        pointerEvents: 'none', transition: 'background 0.8s ease',
      }} />

      {/* Ring 1 — slow clockwise */}
      <div style={{
        position: 'absolute', top: '50%', left: '50%',
        width: '100%', height: '100%',
        border: `1px solid ${cfg.ring1}`,
        borderRadius: '50%',
        animation: 'ring-cw 20s linear infinite',
        transform: 'translate(-50%,-50%)',
      }}>
        <div style={{
          position: 'absolute', top: -4, left: '50%', marginLeft: -4,
          width: 8, height: 8, borderRadius: '50%',
          background: cfg.core, opacity: 0.8,
          boxShadow: `0 0 10px ${cfg.core}`,
        }} />
      </div>

      {/* Ring 2 — faster counter-clockwise */}
      {(state === 'speaking' || state === 'thinking') && (
        <div style={{
          position: 'absolute', top: '50%', left: '50%',
          width: '80%', height: '80%',
          border: `1px dashed ${cfg.ring1}`,
          borderRadius: '50%',
          animation: 'ring-ccw 12s linear infinite',
          transform: 'translate(-50%,-50%)',
        }}>
          <div style={{
            position: 'absolute', bottom: -3, right: '20%',
            width: 6, height: 6, borderRadius: '50%',
            background: cfg.core, opacity: 0.6,
          }} />
        </div>
      )}

      {/* Particles — only during thinking */}
      {state === 'thinking' && ['drift-1', 'drift-2', 'drift-3'].map((anim, i) => (
        <div key={i} style={{
          position: 'absolute',
          top: `${[30, 55, 45][i]}%`, left: `${[60, 30, 65][i]}%`,
          width: [5, 4, 6][i], height: [5, 4, 6][i],
          borderRadius: '50%', background: K.amber,
          opacity: 0.5, animation: `${anim} ${[3, 4, 3.5][i]}s ease-in-out infinite`,
        }} />
      ))}

      {/* Core orb */}
      <div style={{
        position: 'absolute', inset: 24, borderRadius: '50%',
        background: `radial-gradient(circle at 38% 36%, ${K.surfaceHi}, ${K.bg})`,
        border: `1px solid ${cfg.ring1}`,
        animation: cfg.anim,
        transition: 'border-color 0.6s ease',
        display: 'flex', flexDirection: 'column',
        alignItems: 'center', justifyContent: 'center', gap: 6,
      }}>
        {/* SimLi stub — replace with <SimliClient agentId={...} /> */}
        <div
          data-simli-ready="true"
          style={{
            width: 44, height: 44, borderRadius: '50%',
            background: `radial-gradient(circle at 35% 35%, ${K.surfaceHi}, ${K.bg})`,
            border: `1px solid ${cfg.ring1}`,
            display: 'flex', alignItems: 'center', justifyContent: 'center',
          }}
        >
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
            <circle cx="12" cy="8" r="3.5" stroke={cfg.core} strokeWidth="1.5" fill={`${cfg.core}18`}/>
            <path d="M4 20c0-3.87 3.58-7 8-7s8 3.13 8 7" stroke={cfg.core} strokeWidth="1.5" strokeLinecap="round"/>
          </svg>
        </div>

        {/* State label */}
        <span style={{
          fontFamily: K.mono, fontSize: 9, letterSpacing: 2,
          fontWeight: 500, color: cfg.core, opacity: 0.9,
        }}>
          {cfg.label.toUpperCase()}
        </span>
      </div>

      {/* Waveform bars — visible when speaking or listening */}
      {(state === 'speaking' || state === 'listening') && (
        <div style={{
          position: 'absolute', bottom: 0, left: '50%', transform: 'translateX(-50%)',
          display: 'flex', gap: 3, alignItems: 'center', height: 18,
        }} aria-hidden="true">
          {[0.6, 0.9, 1, 0.9, 0.6].map((h, i) => (
            <div key={i} style={{
              width: 3, height: `${h * 100}%`, minHeight: 3,
              borderRadius: 2, background: cfg.core, opacity: 0.7,
              transformOrigin: 'center',
              animation: `bar-wave ${0.7 + i * 0.1}s ease-in-out ${i * 0.08}s infinite`,
            }} />
          ))}
        </div>
      )}
    </div>
  );
};

/* ══════════════════════════════════════════════════════════════════════════════
   TRANSLATION CARD — hero feature
══════════════════════════════════════════════════════════════════════════════ */
interface TurnProps {
  log: AppLog;
  translation: string | null;
}
const ConversationTurn: React.FC<TurnProps> = ({ log, translation }) => {
  if (log.source === 'SYSTEM') return null;
  const isAI = log.source === 'AI';
  const labelColor = isAI ? K.accent : K.green;
  const label      = isAI ? 'AI Response' : 'You said';
  const transLabel = isAI ? 'Hindi' : 'English';

  return (
    <div
      style={{
        borderBottom: `1px solid ${K.glassBorder}`,
        padding: '20px 0',
        animation: 'msg-in 0.3s ease-out',
      }}
    >
      {/* Speaker label */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
        <div style={{
          width: 6, height: 6, borderRadius: '50%',
          background: labelColor, flexShrink: 0,
          boxShadow: `0 0 6px ${labelColor}`,
        }} />
        <span style={{ fontFamily: K.sans, fontSize: 11, fontWeight: 600, color: labelColor, letterSpacing: '0.04em', textTransform: 'uppercase' }}>
          {label}
        </span>
        <span style={{ fontFamily: K.mono, fontSize: 10, color: K.ter, marginLeft: 'auto' }}>{log.ts}</span>
      </div>

      {/* Original text */}
      <p style={{
        fontFamily: K.sans, fontSize: 15, color: K.pri, lineHeight: 1.65,
        marginBottom: translation ? 12 : 0, fontWeight: 400,
      }}>
        {log.message}
      </p>

      {/* Translation */}
      {translation && (
        <div style={{
          display: 'flex', alignItems: 'flex-start', gap: 10,
          padding: '10px 14px', borderRadius: K.r,
          background: K.glass, border: `1px solid ${K.glassBorder}`,
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 5, flexShrink: 0, paddingTop: 2 }}>
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke={K.sec} strokeWidth="2" strokeLinecap="round">
              <circle cx="12" cy="12" r="10"/><path d="M2 12h20M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"/>
            </svg>
            <span style={{ fontFamily: K.mono, fontSize: 9, color: K.sec, letterSpacing: 1, textTransform: 'uppercase', fontWeight: 500 }}>{transLabel}</span>
          </div>
          <p style={{ fontFamily: K.sans, fontSize: 13, color: K.sec, lineHeight: 1.6, margin: 0, fontStyle: 'italic' }}>
            {translation}
          </p>
        </div>
      )}
    </div>
  );
};

/* ══════════════════════════════════════════════════════════════════════════════
   SESSION TIMELINE — left panel
══════════════════════════════════════════════════════════════════════════════ */
interface TimelineEvent { id: string; ts: string; label: string; type: 'connect' | 'user' | 'ai' | 'system'; }

const TIMELINE_COLORS = { connect: K.green, user: K.green, ai: K.accent, system: K.ter };

const Timeline: React.FC<{ events: TimelineEvent[] }> = ({ events }) => (
  <div style={{ display: 'flex', flexDirection: 'column', gap: 0 }}>
    {events.map((ev, i) => (
      <div key={ev.id} style={{ display: 'flex', gap: 12, paddingBottom: 16, animation: 'slide-in 0.3s ease-out' }}>
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', flexShrink: 0 }}>
          <div style={{
            width: 8, height: 8, borderRadius: '50%',
            background: TIMELINE_COLORS[ev.type],
            boxShadow: i === 0 ? `0 0 8px ${TIMELINE_COLORS[ev.type]}` : 'none',
            marginTop: 2, flexShrink: 0,
          }} />
          {i < events.length - 1 && (
            <div style={{ width: 1, flex: 1, background: K.glassBorder, marginTop: 4, minHeight: 12 }} />
          )}
        </div>
        <div>
          <p style={{ fontFamily: K.mono, fontSize: 9, color: K.ter, marginBottom: 2 }}>{ev.ts}</p>
          <p style={{ fontFamily: K.sans, fontSize: 12, color: ev.type === 'connect' ? K.pri : K.sec, lineHeight: 1.4 }}>
            {ev.label}
          </p>
        </div>
      </div>
    ))}
  </div>
);

/* ══════════════════════════════════════════════════════════════════════════════
   QUICK ACTIONS — right panel
══════════════════════════════════════════════════════════════════════════════ */
const ACTIONS = [
  { id: 'audit',    icon: '📋', label: 'Audit Report',     desc: 'Generate full compliance audit', query: 'Generate an audit report for this session' },
  { id: 'risk',     icon: '⚠️',  label: 'Risk Analysis',    desc: 'Identify compliance risks',      query: 'Analyze compliance risks in this session' },
  { id: 'checklist',icon: '✅', label: 'Compliance Check', desc: 'Review against standards',       query: 'Run a compliance checklist review' },
  { id: 'policy',   icon: '📌', label: 'Policy Review',    desc: 'Check policy alignment',         query: 'Review policies discussed in this session' },
] as const;

const QuickActions: React.FC<{ onAction: (query: string) => void; onExport: () => void; dlUrl: string | null; pptxUrl: string | null }> = ({ onAction, onExport, dlUrl, pptxUrl }) => {
  const [exporting, setExporting] = React.useState(false);
  const handleExport = async () => {
    setExporting(true);
    await onExport();
    setExporting(false);
  };
  return (
  <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
    {ACTIONS.map(a => (
      <button
        key={a.id}
        onClick={() => onAction(a.query)}
        style={{
          display: 'flex', alignItems: 'center', gap: 12,
          padding: '12px 14px', borderRadius: K.r,
          background: K.glass, border: `1px solid ${K.glassBorder}`,
          cursor: 'pointer', textAlign: 'left', width: '100%',
          transition: 'background 0.15s, border-color 0.15s',
        }}
        onMouseEnter={e => { e.currentTarget.style.background = K.accentLo; e.currentTarget.style.borderColor = K.accentMid; }}
        onMouseLeave={e => { e.currentTarget.style.background = K.glass;    e.currentTarget.style.borderColor = K.glassBorder; }}
      >
        <span style={{ fontSize: 18, flexShrink: 0, lineHeight: 1 }}>{a.icon}</span>
        <div>
          <p style={{ fontFamily: K.sans, fontSize: 12, fontWeight: 500, color: K.pri, margin: '0 0 2px' }}>{a.label}</p>
          <p style={{ fontFamily: K.sans, fontSize: 11, color: K.ter, margin: 0 }}>{a.desc}</p>
        </div>
      </button>
    ))}

    {/* Export Session — runs silently in background */}
    <button
      onClick={handleExport}
      disabled={exporting}
      style={{
        display: 'flex', alignItems: 'center', gap: 12,
        padding: '12px 14px', borderRadius: K.r,
        background: exporting ? K.accentLo : K.glass,
        border: `1px solid ${exporting ? K.accentMid : K.glassBorder}`,
        cursor: exporting ? 'default' : 'pointer', textAlign: 'left', width: '100%',
        transition: 'background 0.15s, border-color 0.15s', opacity: exporting ? 0.7 : 1,
      }}
      onMouseEnter={e => { if (!exporting) { e.currentTarget.style.background = K.accentLo; e.currentTarget.style.borderColor = K.accentMid; } }}
      onMouseLeave={e => { if (!exporting) { e.currentTarget.style.background = K.glass;    e.currentTarget.style.borderColor = K.glassBorder; } }}
    >
      <span style={{ fontSize: 18, flexShrink: 0, lineHeight: 1 }}>{exporting ? '⏳' : '↗'}</span>
      <div>
        <p style={{ fontFamily: K.sans, fontSize: 12, fontWeight: 500, color: K.pri, margin: '0 0 2px' }}>
          {exporting ? 'Generating report…' : 'Export Session'}
        </p>
        <p style={{ fontFamily: K.sans, fontSize: 11, color: K.ter, margin: 0 }}>Generate PDF report with full transcript</p>
      </div>
    </button>

    {/* Download links when available */}
    {(dlUrl || pptxUrl) && (
      <div style={{
        marginTop: 4, padding: '10px 14px', borderRadius: K.r,
        background: K.accentLo, border: `1px solid ${K.accentMid}`,
        display: 'flex', flexDirection: 'column', gap: 6,
      }}>
        <p style={{ fontFamily: K.mono, fontSize: 9, color: K.accent, letterSpacing: 1.5, textTransform: 'uppercase', marginBottom: 4 }}>Reports Ready</p>
        {dlUrl && (
          <a href={VoiceService.fullUrl(dlUrl)} target="_blank" rel="noreferrer" style={{
            fontFamily: K.sans, fontSize: 12, color: K.accent, textDecoration: 'none', fontWeight: 500,
            display: 'flex', alignItems: 'center', gap: 6,
          }}>↓ Compliance PDF</a>
        )}
        {pptxUrl && (
          <a href={VoiceService.fullUrl(pptxUrl)} target="_blank" rel="noreferrer" style={{
            fontFamily: K.sans, fontSize: 12, color: K.accent, textDecoration: 'none', fontWeight: 500,
            display: 'flex', alignItems: 'center', gap: 6,
          }}>↓ Presentation</a>
        )}
      </div>
    )}
  </div>
  );
};

/* ══════════════════════════════════════════════════════════════════════════════
   TRANSCRIPT EXPORT MODAL
══════════════════════════════════════════════════════════════════════════════ */
const ExportModal: React.FC<{ logs: AppLog[]; sessionId: string; onClose: () => void }> = ({ logs, sessionId, onClose }) => {
  const transcript = logs.slice().reverse().filter(l => l.source !== 'SYSTEM');
  const printRef = useRef<HTMLDivElement>(null);

  const handlePrint = () => {
    const w = window.open('', '_blank')!;
    w.document.write(`
      <html><head><title>Session Transcript – ${sessionId}</title>
      <style>
        body { font-family: 'Inter', sans-serif; padding: 40px; color: #111; max-width: 800px; margin: 0 auto; }
        h1 { font-size: 20px; margin-bottom: 4px; }
        .meta { font-size: 12px; color: #666; margin-bottom: 32px; }
        .turn { margin-bottom: 20px; page-break-inside: avoid; }
        .speaker { font-size: 10px; font-weight: 600; letter-spacing: 1px; text-transform: uppercase; margin-bottom: 4px; }
        .speaker.ai { color: #6366F1; } .speaker.user { color: #16A34A; }
        .msg { font-size: 14px; line-height: 1.65; padding: 10px 14px; border-radius: 8px; }
        .msg.ai { background: #F5F3FF; } .msg.user { background: #F0FDF4; }
        .ts { font-size: 10px; color: #999; margin-top: 4px; font-family: monospace; }
      </style></head><body>
      <h1>InTimeTec Compliance Session Transcript</h1>
      <div class="meta">Session: ${sessionId} &nbsp;·&nbsp; Exported: ${new Date().toLocaleString()} &nbsp;·&nbsp; ${transcript.length} messages</div>
      ${transcript.map(l => `
        <div class="turn">
          <div class="speaker ${l.source.toLowerCase()}">${l.source === 'AI' ? '◈ AI Compliance Advisor' : '◆ User'}</div>
          <div class="msg ${l.source.toLowerCase()}">${l.message.replace(/</g, '&lt;').replace(/>/g, '&gt;')}</div>
          <div class="ts">${l.ts}</div>
        </div>`).join('')}
      </body></html>`);
    w.document.close();
    w.focus();
    w.print();
  };

  return (
    <div style={{
      position: 'fixed', inset: 0, zIndex: 100,
      background: 'rgba(0,0,0,0.75)', backdropFilter: 'blur(8px)',
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      padding: 24,
    }} onClick={e => e.target === e.currentTarget && onClose()}>
      <div style={{
        background: K.surface, border: `1px solid ${K.glassBorder}`,
        borderRadius: K.rLg, width: '100%', maxWidth: 640,
        maxHeight: '80vh', display: 'flex', flexDirection: 'column',
        boxShadow: '0 24px 80px rgba(0,0,0,0.6)',
      }}>
        {/* Header */}
        <div style={{ padding: '16px 20px', borderBottom: `1px solid ${K.glassBorder}`, display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexShrink: 0 }}>
          <div>
            <p style={{ fontFamily: K.sans, fontSize: 14, fontWeight: 600, color: K.pri, margin: '0 0 2px' }}>Session Transcript</p>
            <p style={{ fontFamily: K.mono, fontSize: 10, color: K.ter, margin: 0 }}>{sessionId} · {transcript.length} messages</p>
          </div>
          <div style={{ display: 'flex', gap: 8 }}>
            <button onClick={handlePrint} style={{
              padding: '8px 16px', borderRadius: K.r, border: 'none',
              background: K.accent, color: '#fff',
              fontFamily: K.sans, fontSize: 12, fontWeight: 500, cursor: 'pointer',
            }}>↓ Download PDF</button>
            <button onClick={onClose} style={{
              width: 32, height: 32, borderRadius: K.r, border: `1px solid ${K.glassBorder}`,
              background: 'transparent', color: K.sec, cursor: 'pointer', fontSize: 16,
              display: 'flex', alignItems: 'center', justifyContent: 'center',
            }}>×</button>
          </div>
        </div>
        {/* Body */}
        <div ref={printRef} style={{ flex: 1, overflowY: 'auto', padding: '16px 20px' }}>
          {transcript.length === 0
            ? <p style={{ fontFamily: K.sans, fontSize: 13, color: K.ter, textAlign: 'center', padding: '40px 0' }}>No conversation yet.</p>
            : transcript.map(l => (
              <div key={l.id} style={{ marginBottom: 16 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 5 }}>
                  <div style={{ width: 6, height: 6, borderRadius: '50%', background: l.source === 'AI' ? K.accent : K.green, flexShrink: 0 }} />
                  <span style={{ fontFamily: K.mono, fontSize: 9, fontWeight: 600, color: l.source === 'AI' ? K.accent : K.green, letterSpacing: 1, textTransform: 'uppercase' }}>
                    {l.source === 'AI' ? 'AI Compliance Advisor' : 'You'}
                  </span>
                  <span style={{ fontFamily: K.mono, fontSize: 9, color: K.ter, marginLeft: 'auto' }}>{l.ts}</span>
                </div>
                <div style={{
                  padding: '10px 14px', borderRadius: K.r,
                  background: l.source === 'AI' ? K.accentLo : K.greenLo,
                  border: `1px solid ${l.source === 'AI' ? K.accentMid : K.green + '25'}`,
                  fontSize: 13, color: K.pri, lineHeight: 1.65,
                }}>
                  {l.message}
                </div>
              </div>
            ))
          }
        </div>
      </div>
    </div>
  );
};


interface DockProps {
  isMicMuted:     boolean;
  isSpeakerMuted: boolean;
  translationOn:  boolean;
  transcriptOpen: boolean;
  onToggleMic:    () => void;
  onToggleSpeaker:() => void;
  onToggleTranslation: () => void;
  onToggleTranscript:  () => void;
  onDisconnect:   () => void;
}

const DockButton: React.FC<{
  label: string; active?: boolean; danger?: boolean;
  onClick: () => void; children: React.ReactNode;
}> = ({ label, active, danger, onClick, children }) => (
  <button
    onClick={onClick}
    aria-label={label}
    title={label}
    style={{
      width: 44, height: 44, borderRadius: '50%', border: `1px solid ${danger ? K.red + '40' : active ? K.accentMid : K.glassBorder}`,
      cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center',
      background: danger ? K.redLo : active ? K.accentLo : K.glass,
      transition: 'all 0.15s',
      color: danger ? K.red : active ? K.accent : K.sec,
      fontSize: 18, flexShrink: 0,
    }}
    onMouseEnter={e => { e.currentTarget.style.transform = 'scale(1.08)'; }}
    onMouseLeave={e => { e.currentTarget.style.transform = 'scale(1)'; }}
  >
    {children}
  </button>
);

const CommandDock: React.FC<DockProps> = ({
  isMicMuted, isSpeakerMuted, translationOn, transcriptOpen,
  onToggleMic, onToggleSpeaker, onToggleTranslation, onToggleTranscript, onDisconnect,
}) => (
  <div style={{
    display: 'inline-flex', alignItems: 'center', gap: 8,
    padding: '10px 16px', borderRadius: K.rFull,
    background: 'rgba(17,19,24,0.85)',
    backdropFilter: 'blur(20px)',
    border: `1px solid ${K.glassBorder}`,
    boxShadow: '0 8px 32px rgba(0,0,0,0.4), 0 1px 0 rgba(255,255,255,0.05) inset',
  }}>
    <DockButton label={isMicMuted ? 'Unmute microphone' : 'Mute microphone'} danger={isMicMuted} onClick={onToggleMic}>
      {isMicMuted
        ? <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><line x1="2" y1="2" x2="22" y2="22"/><path d="M18.9 13.2A6 6 0 0 0 12 7v-.2M6 6a6 6 0 0 0-.1 1v5a6 6 0 0 0 9.7 4.7M12 19v3m-4 0h8"/></svg>
        : <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><path d="M12 1a4 4 0 0 1 4 4v6a4 4 0 0 1-8 0V5a4 4 0 0 1 4-4z"/><path d="M19 10a7 7 0 0 1-14 0M12 19v4M8 23h8"/></svg>
      }
    </DockButton>

    <DockButton label={isSpeakerMuted ? 'Unmute speaker' : 'Mute speaker'} danger={isSpeakerMuted} onClick={onToggleSpeaker}>
      {isSpeakerMuted
        ? <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"/><line x1="23" y1="9" x2="17" y2="15"/><line x1="17" y1="9" x2="23" y2="15"/></svg>
        : <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"/><path d="M19.07 4.93a10 10 0 0 1 0 14.14M15.54 8.46a5 5 0 0 1 0 7.07"/></svg>
      }
    </DockButton>

    <DockButton label="Toggle translation" active={translationOn} onClick={onToggleTranslation}>
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><circle cx="12" cy="12" r="10"/><path d="M2 12h20M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"/></svg>
    </DockButton>

    <DockButton label="Toggle transcript" active={transcriptOpen} onClick={onToggleTranscript}>
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>
    </DockButton>

    {/* Divider */}
    <div style={{ width: 1, height: 24, background: K.glassBorder, margin: '0 4px' }} />

    <DockButton label="End session" danger onClick={onDisconnect}>
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round"><rect x="3" y="3" width="18" height="18" rx="2"/></svg>
    </DockButton>
  </div>
);

/* ══════════════════════════════════════════════════════════════════════════════
   TEXT INPUT
══════════════════════════════════════════════════════════════════════════════ */
const TextInput: React.FC<{ onSend: (t: string) => void }> = ({ onSend }) => {
  const [val, setVal] = useState('');
  const ref = useRef<HTMLInputElement>(null);
  const submit = () => { const t = val.trim(); if (!t) return; setVal(''); onSend(t); };
  return (
    <div style={{
      display: 'flex', gap: 10, padding: '12px 16px',
      background: K.glass, border: `1px solid ${K.glassBorder}`,
      borderRadius: K.rLg, backdropFilter: 'blur(12px)',
      transition: 'border-color 0.15s',
    }}
      onFocusCapture={e => (e.currentTarget.style.borderColor = K.accentMid)}
      onBlurCapture={e  => (e.currentTarget.style.borderColor = K.glassBorder)}
    >
      <input
        ref={ref}
        value={val}
        onChange={e => setVal(e.target.value)}
        onKeyDown={e => e.key === 'Enter' && !e.shiftKey && (e.preventDefault(), submit())}
        placeholder="Type a message or ask the AI…"
        aria-label="Message input"
        style={{
          flex: 1, background: 'transparent', border: 'none', outline: 'none',
          fontFamily: K.sans, fontSize: 14, color: K.pri,
          WebkitFontSmoothing: 'antialiased',
        }}
      />
      <button
        onClick={submit}
        disabled={!val.trim()}
        aria-label="Send message"
        style={{
          padding: '8px 18px', borderRadius: K.r, border: 'none',
          background: val.trim() ? K.accent : K.ter,
          color: '#fff', fontFamily: K.sans, fontSize: 13, fontWeight: 500,
          cursor: val.trim() ? 'pointer' : 'default',
          transition: 'background 0.15s', flexShrink: 0,
        }}
      >
        Send
      </button>
    </div>
  );
};

/* ══════════════════════════════════════════════════════════════════════════════
   PROPS
══════════════════════════════════════════════════════════════════════════════ */
interface Props {
  phase: Phase; amplitude: number; logs: AppLog[];
  dlUrl: string | null; pptxUrl: string | null; sessionId: string;
  isMicMuted: boolean; isSpeakerMuted: boolean;
  onDisconnect: () => void; onToggleMic: () => void;
  onToggleSpeaker: () => void; onDispatch: (t: string) => void;
}

/* ══════════════════════════════════════════════════════════════════════════════
   ROOT — ConsoleView

   Layout (3-col + bottom bar):
   ┌─────────────────────────────────────────────────────────┐
   │  NAV  Compliance Advisor · Connected · Session ID       │
   ├────────────┬──────────────────────────┬─────────────────┤
   │  TIMELINE  │       CENTER STAGE       │  QUICK ACTIONS  │
   │  (280px)   │       (flex-1)           │   (260px)       │
   │            │   Orb + Translation      │                 │
   │            │   Conversation           │                 │
   ├────────────┴──────────────────────────┴─────────────────┤
   │  BOTTOM: Floating Dock + Text Input                     │
   └─────────────────────────────────────────────────────────┘
══════════════════════════════════════════════════════════════════════════════ */
export const ConsoleView: React.FC<Props> = ({
  phase, logs, dlUrl, pptxUrl, sessionId,
  isMicMuted, isSpeakerMuted,
  onDisconnect, onToggleMic, onToggleSpeaker, onDispatch,
}) => {
  const [translationOn, setTranslationOn] = useState(true);
  const [transcriptOpen, setTranscriptOpen] = useState(true);
  const [exportOpen, setExportOpen] = useState(false);
  const feedRef = useRef<HTMLDivElement>(null);

  const uiState = toUIState(phase);

  // Build timeline from logs
  const timeline: TimelineEvent[] = useMemo(() => {
    const events: TimelineEvent[] = [{ id: 'connect', ts: logs[logs.length - 1]?.ts ?? '--:--:--', label: 'Session connected', type: 'connect' }];
    logs.slice().reverse().forEach(l => {
      if (l.source === 'USER')   events.push({ id: l.id, ts: l.ts, label: 'User spoke', type: 'user' });
      if (l.source === 'AI')     events.push({ id: l.id, ts: l.ts, label: 'AI responded', type: 'ai' });
      if (l.source === 'SYSTEM' && l.message.includes('report')) events.push({ id: l.id + 's', ts: l.ts, label: 'Report generated', type: 'system' });
    });
    return events.slice(0, 12);
  }, [logs]);

  const chatLogs = useMemo(() => logs.filter(l => l.source !== 'SYSTEM').slice().reverse(), [logs]);

  useEffect(() => {
    if (feedRef.current) {
      feedRef.current.scrollTop = feedRef.current.scrollHeight;
    }
  }, [chatLogs.length]);

  const stateColor = uiState === 'listening' ? K.green : uiState === 'thinking' ? K.amber : uiState === 'speaking' ? K.accent : K.ter;

  return (
    <>
      <style>{CSS}</style>
      <div style={{
        height: '100%', display: 'flex', flexDirection: 'column',
        background: K.bg, color: K.pri, fontFamily: K.sans,
        WebkitFontSmoothing: 'antialiased', overflow: 'hidden',
      }}>

        {/* ── NAV ───────────────────────────────────────────────────────── */}
        <nav style={{
          height: 52, display: 'flex', alignItems: 'center',
          padding: '0 24px', borderBottom: `1px solid ${K.glassBorder}`,
          background: K.surface, flexShrink: 0, gap: 16,
        }}>
          <span style={{ fontFamily: K.sans, fontSize: 14, fontWeight: 600, color: K.pri, letterSpacing: '-0.02em' }}>
            Compliance Advisor
          </span>
          <div style={{ display: 'flex', alignItems: 'center', gap: 5, padding: '3px 10px', borderRadius: K.rFull, background: K.greenLo, border: `1px solid ${K.green}25` }}>
            <div style={{ width: 5, height: 5, borderRadius: '50%', background: K.green, animation: 'pulse-dot 2s infinite' }} />
            <span style={{ fontFamily: K.mono, fontSize: 9, color: K.green, letterSpacing: 1, fontWeight: 500 }}>CONNECTED</span>
          </div>
          <div style={{ flex: 1 }} />
          <span style={{ fontFamily: K.mono, fontSize: 10, color: K.ter }}>{sessionId.slice(-10)}</span>
        </nav>

        {/* ── BODY GRID ─────────────────────────────────────────────────── */}
        <div style={{
          flex: 1, display: 'grid', minHeight: 0, overflow: 'hidden',
          gridTemplateColumns: '260px 1fr 260px',
        }}>

          {/* ═══ LEFT — Session Timeline ══════════════════════════════════ */}
          <div style={{
            borderRight: `1px solid ${K.glassBorder}`,
            display: 'flex', flexDirection: 'column', overflow: 'hidden',
            background: K.surface,
          }}>
            <div style={{ padding: '16px 16px 12px', borderBottom: `1px solid ${K.glassBorder}`, flexShrink: 0 }}>
              <p style={{ fontFamily: K.mono, fontSize: 9, color: K.ter, letterSpacing: 2, textTransform: 'uppercase' }}>Session Timeline</p>
            </div>
            <div style={{ flex: 1, overflowY: 'auto', padding: '16px' }}>
              <Timeline events={timeline} />
            </div>
          </div>

          {/* ═══ CENTER — Stage ═══════════════════════════════════════════ */}
          <div style={{ display: 'flex', flexDirection: 'column', overflow: 'hidden', position: 'relative' }}>

            {/* Orb area */}
            <div style={{
              display: 'flex', flexDirection: 'column', alignItems: 'center',
              justifyContent: 'center', padding: '28px 32px 20px', flexShrink: 0, gap: 14,
            }}>
              <Orb state={uiState} />

              {/* State pill */}
              <div style={{
                display: 'inline-flex', alignItems: 'center', gap: 8,
                padding: '5px 14px', borderRadius: K.rFull,
                background: `${stateColor}12`, border: `1px solid ${stateColor}25`,
              }}>
                <div style={{ width: 6, height: 6, borderRadius: '50%', background: stateColor, animation: uiState !== 'idle' ? 'pulse-dot 1.5s infinite' : 'none' }} />
                <span style={{ fontFamily: K.sans, fontSize: 12, fontWeight: 500, color: stateColor }}>
                  {uiState === 'listening' ? 'Listening — speak now'
                   : uiState === 'thinking' ? 'Processing your request'
                   : uiState === 'speaking' ? 'AI is responding'
                   : 'Ready'}
                </span>
                {uiState === 'thinking' && (
                  <span style={{ display: 'inline-flex', gap: 3 }} aria-hidden="true">
                    {[0, 1, 2].map(i => <span key={i} style={{ width: 4, height: 4, borderRadius: '50%', background: K.amber, animation: `think-dot 1.2s ease-in-out ${i * 0.15}s infinite`, display: 'inline-block' }} />)}
                  </span>
                )}
              </div>
            </div>

            {/* Conversation feed */}
            {transcriptOpen && (
              <div
                ref={feedRef}
                style={{
                  flex: 1, overflowY: 'auto', padding: '0 32px 16px',
                  borderTop: `1px solid ${K.glassBorder}`,
                }}
                role="log" aria-label="Conversation" aria-live="polite"
              >
                {chatLogs.length === 0 ? (
                  <div style={{ padding: '40px 0', textAlign: 'center' }}>
                    <p style={{ fontFamily: K.sans, fontSize: 13, color: K.ter, lineHeight: 1.7 }}>
                      Your conversation will appear here.<br/>
                      Speak or type a message to begin.
                    </p>
                  </div>
                ) : (
                  chatLogs.map(log => (
                    <ConversationTurn
                      key={log.id}
                      log={log}
                      translation={translationOn ? fakeTranslate(log.message) : null}
                    />
                  ))
                )}
              </div>
            )}
          </div>

          {/* ═══ RIGHT — Quick Actions ════════════════════════════════════ */}
          <div style={{
            borderLeft: `1px solid ${K.glassBorder}`,
            display: 'flex', flexDirection: 'column', overflow: 'hidden',
            background: K.surface,
          }}>
            <div style={{ padding: '16px 16px 12px', borderBottom: `1px solid ${K.glassBorder}`, flexShrink: 0 }}>
              <p style={{ fontFamily: K.mono, fontSize: 9, color: K.ter, letterSpacing: 2, textTransform: 'uppercase' }}>Quick Actions</p>
            </div>
            <div style={{ flex: 1, overflowY: 'auto', padding: '12px' }}>
              <QuickActions onAction={onDispatch} onExport={() => setExportOpen(true)} dlUrl={dlUrl} pptxUrl={pptxUrl} />
            </div>
          </div>
        </div>

        {/* ── BOTTOM BAR ────────────────────────────────────────────────── */}
        <div style={{
          borderTop: `1px solid ${K.glassBorder}`,
          background: K.surface, flexShrink: 0,
          padding: '14px 24px', display: 'flex',
          alignItems: 'center', gap: 16,
        }}>
          {/* Floating dock */}
          <CommandDock
            isMicMuted={isMicMuted}
            isSpeakerMuted={isSpeakerMuted}
            translationOn={translationOn}
            transcriptOpen={transcriptOpen}
            onToggleMic={onToggleMic}
            onToggleSpeaker={onToggleSpeaker}
            onToggleTranslation={() => setTranslationOn(v => !v)}
            onToggleTranscript={() => setTranscriptOpen(v => !v)}
            onDisconnect={onDisconnect}
          />

          {/* Text input */}
          <div style={{ flex: 1 }}>
            <TextInput onSend={onDispatch} />
          </div>
        </div>

      </div>
      {exportOpen && <ExportModal logs={logs} sessionId={sessionId} onClose={() => setExportOpen(false)} />}
    </>
  );
};
