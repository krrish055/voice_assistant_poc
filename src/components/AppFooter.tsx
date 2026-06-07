// ── C4: AppFooter Component ───────────────────────────────────────────────────
import React from 'react';
import { ITT_THEME as T } from '../theme';

const BADGES = [
  { label: 'Inc.',  sub: '5000',                    style: { fontSize: 22, fontWeight: 900 } },
  { label: 'HP',    sub: 'Partner',                 style: { fontSize: 18, fontWeight: 700 } },
  { label: 'Idaho', sub: 'Private 100',             style: { fontSize: 11, fontWeight: 700 } },
  { label: '★',    sub: 'Best Places to Work Idaho', style: { fontSize: 13, fontWeight: 600 } },
] as const;

const SOCIALS = [
  { icon: 'in', href: 'https://linkedin.com/company/intimetec' },
  { icon: '▷',  href: 'https://youtube.com' },
  { icon: 'f',  href: 'https://facebook.com' },
] as const;

const PRODUCTS_SM = ['ClearSpend', 'Court Access Tracking System', 'NextGen Ag Tech', 'Roll On Dispatch'] as const;
const PRODUCTS_LG = [
  { name: 'DataInsight AI', accent: T.colors.accentTeal, icon: '◉' },
  { name: 'cartos suite',   accent: '#A78BFA',           icon: '◎' },
] as const;

export const AppFooter: React.FC = () => (
  <footer style={{ borderTop: '1px solid rgba(255,255,255,0.06)', padding: '48px 64px 28px', marginTop: 'auto' }}>
    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 48, marginBottom: 32 }}>

      {/* Brand */}
      <div>
        <span style={{ fontSize: 28, fontWeight: 900, letterSpacing: '-0.5px' }}>
          <span style={{ color: '#F97316' }}>in</span> time <span style={{ color: '#F97316' }}>t</span>ec
        </span>
        <div style={{ fontSize: 10, fontWeight: 700, letterSpacing: '2px', color: '#F97316', textTransform: 'uppercase', margin: '6px 0 20px' }}>
          Creating Abundance
        </div>
        <p style={{ fontSize: 13, color: T.colors.textMuted, lineHeight: 1.7, maxWidth: 380, marginBottom: 28 }}>
          In Time Tec is an award-winning software development and IT company with offices in the{' '}
          <span style={{ color: T.colors.accentTeal }}>US, Netherlands, Saudi Arabia, UAE, India, Australia, South Korea, and Colombia.</span>
        </p>
        <div style={{ display: 'flex', alignItems: 'center', gap: 16, flexWrap: 'wrap', marginBottom: 20 }}>
          {BADGES.map((b, i) => (
            <div key={i} style={{ border: '1px solid rgba(255,255,255,0.12)', borderRadius: 8, padding: '8px 14px', textAlign: 'center', minWidth: 60 }}>
              <div style={b.style as React.CSSProperties}>{b.label}</div>
              <div style={{ fontSize: 9, color: T.colors.textMuted, marginTop: 2 }}>{b.sub}</div>
            </div>
          ))}
        </div>
        <div style={{ display: 'flex', gap: 12 }}>
          {SOCIALS.map((s, i) => (
            <a key={i} href={s.href} target="_blank" rel="noreferrer" style={{
              width: 32, height: 32, borderRadius: '50%',
              border: '1px solid rgba(255,255,255,0.15)',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              color: T.colors.textMuted, fontSize: 12, textDecoration: 'none',
              transition: T.transitions,
            }}
              onMouseEnter={e => { e.currentTarget.style.borderColor = T.colors.accentTeal; e.currentTarget.style.color = T.colors.accentTeal; }}
              onMouseLeave={e => { e.currentTarget.style.borderColor = 'rgba(255,255,255,0.15)'; e.currentTarget.style.color = T.colors.textMuted; }}
            >
              {s.icon}
            </a>
          ))}
        </div>
      </div>

      {/* Products */}
      <div>
        <div style={{ fontSize: 13, fontWeight: 700, color: T.colors.accentTeal, fontStyle: 'italic', marginBottom: 20 }}>Our products</div>
        <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap', marginBottom: 16 }}>
          {PRODUCTS_SM.map((p, i) => (
            <div key={i} style={{ border: '1px solid rgba(255,255,255,0.1)', borderRadius: 8, padding: '7px 12px', fontSize: 11, fontWeight: 600, color: T.colors.textMuted, backgroundColor: 'rgba(255,255,255,0.03)' }}>
              {p}
            </div>
          ))}
        </div>
        <div style={{ display: 'flex', gap: 14, marginBottom: 14 }}>
          {PRODUCTS_LG.map((p, i) => (
            <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '10px 18px', borderRadius: 12, border: `1px solid ${p.accent}40`, backgroundColor: `${p.accent}10`, fontSize: 15, fontWeight: 700 }}>
              <span style={{ color: p.accent, fontSize: 18 }}>{p.icon}</span>{p.name}
            </div>
          ))}
        </div>
        <div style={{ display: 'inline-flex', alignItems: 'center', gap: 8, padding: '10px 20px', borderRadius: 12, border: '1px solid rgba(249,115,22,0.3)', backgroundColor: 'rgba(249,115,22,0.07)', fontSize: 14, fontWeight: 700 }}>
          <span style={{ color: '#F97316' }}>◉</span>
          <span><span style={{ color: '#F97316' }}>itt</span> racknap</span>
          <span style={{ fontSize: 9, color: T.colors.textMuted, letterSpacing: '1px', textTransform: 'uppercase' }}>Creating Abundance</span>
        </div>
      </div>
    </div>

    <div style={{ borderTop: '1px solid rgba(255,255,255,0.05)', paddingTop: 18, display: 'flex', justifyContent: 'space-between', fontSize: 12, color: T.colors.textMuted }}>
      <span>Copyright © 2026 In Time Tec, LLC All rights reserved.</span>
      <a href="https://intimetec.com/privacy-policy" target="_blank" rel="noreferrer" style={{ color: T.colors.accentTeal, fontWeight: 600, textDecoration: 'none' }}>
        Privacy Policy
      </a>
    </div>
  </footer>
);
