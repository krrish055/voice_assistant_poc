// ── C4: FallbackDrawer Component ──────────────────────────────────────────────
import React, { useState } from 'react';
import { ITT_THEME as T } from '../theme';
import { FAQ_QUESTIONS } from '../constants';
import type { AppLog } from '../types';

interface Props {
  open      : boolean;
  logs      : AppLog[];
  onClose   : () => void;
  onDispatch: (text: string) => void;
}

export const FallbackDrawer: React.FC<Props> = ({ open, logs, onClose, onDispatch }) => {
  const [textIn, setTextIn] = useState('');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const text = textIn.trim();
    if (!text) return;
    setTextIn('');
    onDispatch(text);
  };

  const chatLogs = logs.filter(l => l.source !== 'SYSTEM');

  return (
    <div style={{
      position: 'fixed', top: 0, right: 0,
      width: 380, height: '100vh',
      backgroundColor: '#0F172A',
      borderLeft: '1px solid rgba(255,255,255,0.06)',
      boxShadow: '-12px 0 40px rgba(0,0,0,0.5)',
      transform: open ? 'translateX(0)' : 'translateX(100%)',
      transition: 'transform 0.4s cubic-bezier(0.16, 1, 0.3, 1)',
      zIndex: 1000,
      display: 'flex', flexDirection: 'column',
    }}>

      {/* Header */}
      <div style={{
        padding: '20px 22px', borderBottom: '1px solid rgba(255,255,255,0.05)',
        display: 'flex', justifyContent: 'space-between', alignItems: 'center',
      }}>
        <div>
          <div style={{ fontSize: 14, fontWeight: 700 }}>Dual-Channel Text Fallback</div>
          <div style={{ fontSize: 11, color: T.colors.textMuted, marginTop: 2 }}>Bypass audio — send text directly</div>
        </div>
        <button onClick={onClose} style={{ background: 'transparent', border: 'none', color: T.colors.textMuted, cursor: 'pointer', fontSize: 16 }}>✕</button>
      </div>

      {/* Chat log */}
      <div style={{ flex: 1, padding: '16px 20px', overflowY: 'auto', display: 'flex', flexDirection: 'column-reverse', gap: 10 }}>
        {chatLogs.length === 0
          ? <div style={{ color: T.colors.textMuted, fontSize: 12, fontStyle: 'italic', textAlign: 'center', marginTop: 20 }}>No messages yet. Type below to begin.</div>
          : chatLogs.map(msg => (
            <div key={msg.id} style={{
              alignSelf: msg.source === 'USER' ? 'flex-end' : 'flex-start',
              backgroundColor: msg.source === 'USER' ? T.colors.accentBlue : 'rgba(255,255,255,0.06)',
              padding: '10px 14px', borderRadius: 12,
              maxWidth: '85%', fontSize: 13, lineHeight: 1.45,
            }}>
              {msg.message}
            </div>
          ))
        }
      </div>

      {/* FAQ Chips */}
      <div style={{ padding: '12px 20px', borderTop: '1px solid rgba(255,255,255,0.05)' }}>
        <div style={{ fontSize: 10, fontWeight: 700, letterSpacing: '1px', color: T.colors.textMuted, textTransform: 'uppercase', marginBottom: 10 }}>
          Frequently Asked
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 7 }}>
          {FAQ_QUESTIONS.map((q, i) => (
            <button key={i} onClick={() => onDispatch(q)} style={{
              background: 'rgba(255,255,255,0.04)', border: '1px solid rgba(255,255,255,0.08)',
              borderRadius: 8, padding: '9px 14px', color: T.colors.textMuted,
              fontSize: 12, textAlign: 'left', cursor: 'pointer',
              transition: T.transitions, lineHeight: 1.3,
            }}
              onMouseEnter={e => { e.currentTarget.style.borderColor = T.colors.accentTeal; e.currentTarget.style.color = T.colors.textMain; }}
              onMouseLeave={e => { e.currentTarget.style.borderColor = 'rgba(255,255,255,0.08)'; e.currentTarget.style.color = T.colors.textMuted; }}
            >
              {q}
            </button>
          ))}
        </div>
      </div>

      {/* Input */}
      <form onSubmit={handleSubmit} style={{ padding: '16px 20px', borderTop: '1px solid rgba(255,255,255,0.05)', display: 'flex', gap: 8 }}>
        <input
          type="text" value={textIn}
          onChange={e => setTextIn(e.target.value)}
          placeholder="Type your override query…"
          style={{
            flex: 1, backgroundColor: 'rgba(0,0,0,0.25)',
            border: '1px solid rgba(255,255,255,0.1)', borderRadius: 8,
            padding: '11px 14px', color: '#fff', fontSize: 13, outline: 'none',
          }}
        />
        <button type="submit" style={{
          backgroundColor: T.colors.accentTeal, color: '#000',
          border: 'none', borderRadius: 8, padding: '0 18px',
          fontWeight: 700, cursor: 'pointer', fontSize: 13,
        }}>
          Send
        </button>
      </form>
    </div>
  );
};
