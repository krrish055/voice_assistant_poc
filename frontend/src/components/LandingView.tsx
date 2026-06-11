// ── C4: LandingView Component ─────────────────────────────────────────────────
import React from 'react';
import { ITT_THEME as T } from '../theme';
import { MISSION_CARDS, CLIENT_LOGOS, HERO_IMAGES } from '../constants';

interface Props { onConnect: () => void; }

const cardBase: React.CSSProperties = {
  backgroundColor: T.colors.cardBg,
  border: '1px solid rgba(255,255,255,0.04)',
  borderRadius: 20,
  backdropFilter: 'blur(12px)',
};

export const LandingView: React.FC<Props> = ({ onConnect }) => (
  <main style={{
    flex: 1, display: 'flex', flexDirection: 'column',
    alignItems: 'center', justifyContent: 'center',
    padding: '60px 40px', textAlign: 'center',
    maxWidth: 1100, margin: '0 auto', width: '100%',
  }}>
    <div style={{ fontSize: 11, fontWeight: 700, letterSpacing: '3px', color: T.colors.accentTeal, textTransform: 'uppercase', marginBottom: 14 }}>
      InTimeTec Cognitive Pipeline System
    </div>

    <h1 style={{ fontSize: 52, fontWeight: 800, lineHeight: 1.1, maxWidth: 820, margin: '0 0 20px' }}>
      InTimeTec Compliance Node —{' '}
      <span style={{ color: T.colors.accentTeal }}>Enabling Trust</span>{' '}
      through Autonomous Intelligence
    </h1>

    <p style={{ color: T.colors.textMuted, fontSize: 17, maxWidth: 580, lineHeight: 1.65, marginBottom: 56 }}>
      Hands-free voice engine built on open-source protocols. Generate validated enterprise reports automatically via clean speech interfaces.
    </p>

    {/* AI Expert Hero */}
    <div style={{ width: '100%', textAlign: 'left', marginBottom: 56 }}>
      <h2 style={{ fontSize: 44, fontWeight: 900, color: T.colors.textMain, margin: '0 0 8px', lineHeight: 1.1 }}>
        Results Driven By AI <span style={{ color: T.colors.accentTeal, fontWeight: 300 }}>|</span>
      </h2>
      <p style={{ fontSize: 18, fontWeight: 700, color: T.colors.textMuted, margin: '0 0 32px' }}>
        Custom AI Built for Systems You Already Run
      </p>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 20, marginBottom: 36 }}>
        {HERO_IMAGES.map((src, i) => (
          <div key={i} style={{ borderRadius: 16, overflow: 'hidden', aspectRatio: '4/3' }}>
            <img src={src} alt="" style={{ width: '100%', height: '100%', objectFit: 'cover', display: 'block' }} />
          </div>
        ))}
      </div>
      <button onClick={onConnect} style={{
        background: 'linear-gradient(135deg, #F97316, #EA580C)',
        border: 'none', borderRadius: 30, color: '#fff',
        padding: '16px 36px', fontSize: 16, fontWeight: 800,
        cursor: 'pointer', boxShadow: '0 4px 24px rgba(249,115,22,0.4)',
        transition: T.transitions, letterSpacing: '0.3px',
      }}
        onMouseEnter={e => { e.currentTarget.style.transform = 'scale(1.04)'; }}
        onMouseLeave={e => { e.currentTarget.style.transform = 'scale(1)'; }}
      >
        Talk to our AI Expert Now
      </button>
    </div>

    {/* Marquee */}
    <div style={{ width: '100%', overflow: 'hidden', marginBottom: 48 }}>
      <div style={{ display: 'flex', gap: 48, alignItems: 'center', animation: 'marquee 18s linear infinite', whiteSpace: 'nowrap' }}>
        {[...CLIENT_LOGOS, ...CLIENT_LOGOS].map((name, i) => (
          <span key={i} style={{ fontSize: 14, fontWeight: 700, color: T.colors.textMuted, opacity: 0.55, flexShrink: 0 }}>
            {name}
          </span>
        ))}
      </div>
    </div>

    <button onClick={onConnect} style={{
      background: 'transparent', border: `2px solid ${T.colors.accentTeal}`,
      color: T.colors.textMain, padding: '15px 38px', fontSize: 15,
      fontWeight: 700, borderRadius: 30, cursor: 'pointer',
      boxShadow: `0 0 24px rgba(72,202,228,0.18)`, transition: T.transitions,
    }}
      onMouseEnter={e => { Object.assign(e.currentTarget.style, { backgroundColor: T.colors.accentTeal, color: '#000', transform: 'scale(1.04)' }); }}
      onMouseLeave={e => { Object.assign(e.currentTarget.style, { backgroundColor: 'transparent', color: T.colors.textMain, transform: 'scale(1)' }); }}
    >
      Initiate Compliance Audio Handshake
    </button>

    {/* Mission Deck */}
    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 28, width: '100%', marginTop: 72, textAlign: 'left' }}>
      {MISSION_CARDS.map((f, i) => (
        <div key={i} style={{ ...cardBase, padding: 28 }}>
          <h3 style={{ fontSize: 16, fontWeight: 700, marginBottom: 10, color: T.colors.accentTeal }}>{f.title}</h3>
          <p style={{ color: T.colors.textMuted, fontSize: 13, lineHeight: 1.55, margin: 0 }}>{f.desc}</p>
        </div>
      ))}
    </div>
  </main>
);
