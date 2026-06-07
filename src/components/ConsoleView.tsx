// ── C4: ConsoleView Component ─────────────────────────────────────────────────
import React from 'react';
import { ITT_THEME as T } from '../theme';
import { PHASE_COLOR, PHASE_GLOW, PHASE_LABEL, PHASE_STATUS_TEXT } from '../constants';
import VoiceService from '../services/VoiceService';
import type { Phase, AppLog } from '../types';

interface Props {
  phase       : Phase;
  amplitude   : number;
  logs        : AppLog[];
  dlUrl       : string | null;
  sessionId   : string;
  onDisconnect: () => void;
  onOpenDrawer: () => void;
}

const cardBase: React.CSSProperties = {
  backgroundColor: T.colors.cardBg,
  border: '1px solid rgba(255,255,255,0.04)',
  borderRadius: 20,
  backdropFilter: 'blur(12px)',
};

const LOG_COLOR: Record<AppLog['source'], string> = {
  USER  : T.colors.accentTeal,
  AI    : T.colors.accentBlue,
  SYSTEM: T.colors.textMuted + '55',
};

export const ConsoleView: React.FC<Props> = ({ phase, amplitude, logs, dlUrl, sessionId, onDisconnect, onOpenDrawer }) => {
  const color = PHASE_COLOR[phase];
  const glow  = PHASE_GLOW[phase];

  return (
    <main style={{ flex: 1, display: 'grid', gridTemplateColumns: '1fr 340px', gap: 24, padding: '28px 48px' }}>

      {/* LEFT: Orb Node */}
      <div style={{ ...cardBase, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', position: 'relative', minHeight: 480 }}>

        <button onClick={onDisconnect} style={{
          position: 'absolute', top: 20, left: 20,
          background: 'transparent', border: '1px solid rgba(255,255,255,0.1)',
          color: T.colors.textMuted, padding: '7px 14px', borderRadius: 20,
          cursor: 'pointer', fontSize: 11, fontWeight: 600,
        }}>
          Disconnect Node
        </button>

        <button onClick={onOpenDrawer} style={{
          position: 'absolute', top: 20, right: 20,
          background: T.colors.accentBlue, border: 'none',
          color: '#fff', padding: '7px 18px', borderRadius: 20,
          cursor: 'pointer', fontSize: 11, fontWeight: 700,
        }}>
          Text Fallback ›
        </button>

        <div style={{
          width: 200, height: 200, borderRadius: '50%',
          border: `2px solid ${color}`, boxShadow: `0 0 60px ${glow}`,
          transform: `scale(${amplitude})`,
          transition: 'transform 0.08s ease-out, border-color 0.4s ease, box-shadow 0.4s ease',
          display: 'flex', alignItems: 'center', justifyContent: 'center', marginBottom: 36,
        }}>
          <div style={{
            width: 130, height: 130, borderRadius: '50%',
            backgroundColor: 'rgba(255,255,255,0.02)', border: `1px solid ${color}30`,
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            fontSize: 10, fontWeight: 700, letterSpacing: '2px',
            textTransform: 'uppercase', color: T.colors.textMuted,
          }}>
            {PHASE_LABEL[phase]}
          </div>
        </div>

        <h2 style={{ fontSize: 20, fontWeight: 700, margin: '0 0 8px', textAlign: 'center' }}>
          {PHASE_STATUS_TEXT[phase]}
        </h2>
        <p style={{ color: T.colors.textMuted, fontSize: 13, margin: 0 }}>
          Hands-free · Client-side VAD · {sessionId.slice(-10)}
        </p>

        {dlUrl && (
          <a href={VoiceService.fullUrl(dlUrl)} target="_blank" rel="noreferrer" style={{
            marginTop: 28, display: 'flex', alignItems: 'center', gap: 8,
            padding: '10px 22px', borderRadius: 12,
            background: 'rgba(16,185,129,0.12)', border: '1px solid rgba(16,185,129,0.3)',
            color: '#10B981', fontSize: 13, fontWeight: 600, textDecoration: 'none',
            transition: T.transitions,
          }}>
            ↓ Download Compliance Report
          </a>
        )}
      </div>

      {/* RIGHT: Telemetry */}
      <div style={{ ...cardBase, padding: 22, display: 'flex', flexDirection: 'column' }}>
        <div style={{
          fontSize: 11, fontWeight: 800, letterSpacing: '1px', color: T.colors.textMuted,
          textTransform: 'uppercase', borderBottom: '1px solid rgba(255,255,255,0.05)',
          paddingBottom: 12, marginBottom: 14,
        }}>
          NODE TELEMETRY
        </div>
        <div style={{ flex: 1, overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: 10 }}>
          {logs.length === 0
            ? <div style={{ color: T.colors.textMuted, fontSize: 12, fontStyle: 'italic', textAlign: 'center', marginTop: 20 }}>Awaiting telemetry…</div>
            : logs.map(log => (
              <div key={log.id} style={{
                fontSize: 12, lineHeight: 1.45,
                backgroundColor: 'rgba(0,0,0,0.15)',
                padding: '10px 12px', borderRadius: 8,
                borderLeft: `3px solid ${LOG_COLOR[log.source]}`,
              }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 10, fontWeight: 700, color: T.colors.textMuted, marginBottom: 3 }}>
                  <span>[{log.source}]</span><span>{log.ts}</span>
                </div>
                <div style={{ color: T.colors.textMain }}>{log.message}</div>
              </div>
            ))
          }
        </div>
      </div>
    </main>
  );
};
