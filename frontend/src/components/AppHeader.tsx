// ── C4: AppHeader Component ───────────────────────────────────────────────────
import React from 'react';
import { Settings } from 'lucide-react';
import { ITT_THEME as T } from '../theme';

interface Props { onAdminClick?: () => void }

export const AppHeader: React.FC<Props> = ({ onAdminClick }) => (
  <header style={{
    display: 'flex', justifyContent: 'space-between', alignItems: 'center',
    padding: '20px 48px', borderBottom: '1px solid rgba(255,255,255,0.05)',
  }}>
    <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
      <div style={{ width: 10, height: 10, borderRadius: '50%', backgroundColor: T.colors.accentTeal }} />
      <span style={{ fontSize: 18, fontWeight: 800, letterSpacing: '0.5px' }}>
        InTimeTec <span style={{ fontWeight: 300, color: T.colors.textMuted }}>COMPLIANCE NODE</span>
      </span>
    </div>
    <div style={{ display: 'flex', gap: 24, fontSize: 13, color: T.colors.textMuted, alignItems: 'center' }}>
      <span>Software Engineering</span>
      <span>Security Compliance</span>
      <span>Cognitive Pipelines</span>
      {onAdminClick && (
        <button onClick={onAdminClick} style={{
          display: 'flex', alignItems: 'center', gap: 6,
          background: 'rgba(72,202,228,0.1)', border: '1px solid rgba(72,202,228,0.25)',
          color: T.colors.accentTeal, borderRadius: 8, padding: '6px 14px',
          fontSize: 13, cursor: 'pointer', fontWeight: 500,
        }}>
          <Settings size={14} /> Admin
        </button>
      )}
    </div>
  </header>
);
