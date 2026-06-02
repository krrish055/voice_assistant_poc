import React, { useState, useEffect, useRef } from 'react';
import VoiceService, { VoiceResponse } from '../services/VoiceService';

type NetState = 'online' | 'offline' | 'pending';

interface UIState {
  textChunk: string;
  interim: string;
  isListening: boolean;
  isSpeechSupported: boolean;
}

interface AsyncState {
  isLoading: boolean;
  response: VoiceResponse | null;
  error: string | null;
  net: NetState;
}

const NET_CONFIG: Record<NetState, { badge: string; dot: string; label: string }> = {
  online:  { badge: 'linear-gradient(135deg,#1cad74,#0d8659)', dot: '#1cad74', label: '✓ GATEWAY LINKED'  },
  offline: { badge: 'linear-gradient(135deg,#e74c3c,#c0392b)', dot: '#e74c3c', label: '✕ DISCONNECTED'    },
  pending: { badge: 'linear-gradient(135deg,#f39c12,#e67e22)', dot: '#f39c12', label: '⊙ CONNECTING...'   },
};

const WAVE_DELAYS = [0, 0.08, 0.16, 0.24, 0.32];

const VoiceConsole: React.FC = () => {
  const [ui, setUi] = useState<UIState>({ textChunk: localStorage.getItem('vc_draft') ?? '', interim: '', isListening: false, isSpeechSupported: false });
  const [async_, setAsync] = useState<AsyncState>({ isLoading: false, response: null, error: null, net: 'pending' });

  useEffect(() => { localStorage.setItem('vc_draft', ui.textChunk); }, [ui.textChunk]);

  const recognitionRef = useRef<any>(null);
  const userId    = useRef('user_'    + Date.now());
  const sessionId = useRef('session_' + Date.now());

  useEffect(() => {
    const SR = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    if (!SR) return;
    const r = new SR();
    r.continuous = true; r.interimResults = true; r.lang = 'en-US';
    r.onstart  = () => setUi(p => ({ ...p, isListening: true,  interim: '' }));
    r.onend    = () => setUi(p => ({ ...p, isListening: false }));
    r.onerror  = (e: any) => setAsync(p => ({ ...p, error: `Speech error: ${e.error}` }));
    r.onresult = (e: any) => {
      let interim = '';
      for (let i = e.resultIndex; i < e.results.length; i++) {
        const t = e.results[i][0].transcript;
        e.results[i].isFinal ? setUi(p => ({ ...p, textChunk: p.textChunk + t + ' ' })) : (interim += t);
      }
      setUi(p => ({ ...p, interim }));
    };
    recognitionRef.current = r;
    setUi(p => ({ ...p, isSpeechSupported: true }));
    return () => r.abort();
  }, []);

  const toggleMic = () =>
    ui.isListening ? recognitionRef.current?.stop() : recognitionRef.current?.start();

  const handleSendChunk = async () => {
    if (!ui.textChunk.trim()) return;
    setAsync(p => ({ ...p, isLoading: true, error: null, net: 'pending' }));
    const res = await VoiceService.sendTranscriptChunk({
      userId: userId.current, sessionId: sessionId.current, textChunk: ui.textChunk,
    });
    setAsync({ isLoading: false, response: res, error: res.status === 'error' ? res.message ?? 'Unknown error' : null,
      net: res.status === 'success' ? 'online' : 'offline' });
    if (res.status === 'success') { localStorage.removeItem('vc_draft'); setUi(p => ({ ...p, textChunk: '', interim: '' })); }
  };

  const { badge, dot, label } = NET_CONFIG[async_.net];

  return (
    <div style={s.container}>
      <style>{s.keyframes}</style>
      <h1 style={s.title}>Voice Assistant Console</h1>

      {/* Network Badge */}
      <div style={{ ...s.badge, background: badge, boxShadow: `0 0 12px ${dot}` }}>
        <span style={{ ...s.dot, background: dot }} />
        {label}
      </div>

      {/* Error / Success banners */}
      {async_.error && (
        <div style={s.errorBanner}>
          <span>{async_.error}</span>
          <button style={s.dismiss} onClick={() => setAsync(p => ({ ...p, error: null }))}>✕</button>
        </div>
      )}
      {async_.response?.status === 'success' && <div style={s.successBanner}>✓ Message sent successfully</div>}

      {/* Voice controls */}
      <div style={s.section}>
        <h2 style={s.h2}>Voice Input</h2>
        <button style={{ ...s.btn, ...(ui.isListening ? s.btnDanger : {}) }}
          onClick={toggleMic} disabled={async_.isLoading || !ui.isSpeechSupported}>
          {ui.isListening ? '⏹ Stop Listening' : '🎤 Start Listening'}
        </button>
        {ui.interim && <div style={s.interim}>{ui.interim}</div>}
        {!ui.isSpeechSupported && <p style={s.noSupport}>Speech Recognition not supported in this browser.</p>}
      </div>

      {/* Mic Pulse Widget */}
      <div style={s.micSection}>
        <div style={s.micHeader}>
          <span style={s.micTitle}>🎙️ Voice Stream</span>
          <span style={{ ...s.liveTag, color: ui.isListening ? '#28a745' : '#999' }}>
            {ui.isListening ? '● LIVE' : '○ INACTIVE'}
          </span>
        </div>
        {ui.isListening
          ? <div style={s.waveBox}>{WAVE_DELAYS.map((d, i) => <div key={i} style={{ ...s.bar, animationDelay: `${d}s` }} />)}</div>
          : <div style={s.waveIdle}>🎧 Press "Start Listening" to activate voice stream</div>}
      </div>

      {/* Text input */}
      <div style={s.section}>
        <h2 style={s.h2}>Text Input</h2>
        <div style={s.row}>
          <input style={s.input} type="text" placeholder="Enter text or use voice input"
            value={ui.textChunk} onChange={e => setUi(p => ({ ...p, textChunk: e.target.value }))}
            disabled={async_.isLoading} />
          <button style={{ ...s.btn, ...(async_.isLoading ? s.btnDisabled : {}) }}
            onClick={handleSendChunk} disabled={!ui.textChunk.trim() || async_.isLoading}>
            {async_.isLoading ? '⏳ Sending...' : '📤 Send'}
          </button>
          <button style={{ ...s.btn, ...s.btnDanger }} onClick={() => setUi(p => ({ ...p, textChunk: '', interim: '' }))}
            disabled={async_.isLoading}>Clear</button>
        </div>
      </div>

      {/* Last response */}
      {async_.response && (
        <div style={s.section}>
          <h2 style={s.h2}>Last Response</h2>
          <p><strong>Status:</strong> {async_.response.status}</p>
          {async_.response.ai_response_text && <p><strong>AI:</strong> {async_.response.ai_response_text}</p>}
          {async_.response.next_step        && <p><strong>Next Step:</strong> {async_.response.next_step}</p>}
          {async_.response.confidence_score !== undefined && <p><strong>Confidence:</strong> {(async_.response.confidence_score * 100).toFixed(0)}%</p>}
          {async_.response.message          && <p><strong>Message:</strong> {async_.response.message}</p>}
          <p style={s.ts}>Received at {new Date().toLocaleTimeString()}</p>
        </div>
      )}
    </div>
  );
};

export default VoiceConsole;

// ─── Styles ───────────────────────────────────────────────────────────────────
const s: Record<string, React.CSSProperties & { [k: string]: any }> = {
  keyframes: `
    @keyframes waveFlow   { 0%,100%{transform:scaleY(.5);opacity:.6} 50%{transform:scaleY(1);opacity:1} }
    @keyframes glowGreen  { 0%,100%{box-shadow:0 0 8px #1cad74} 50%{box-shadow:0 0 18px #1cad74} }
  ` as any,
  container:    { maxWidth:600, margin:'0 auto', padding:20, fontFamily:'Arial,sans-serif', background:'#f5f5f5', borderRadius:8 },
  title:        { fontSize:24, fontWeight:'bold', marginBottom:15, color:'#333' },
  badge:        { display:'inline-flex', alignItems:'center', gap:8, padding:'10px 14px', borderRadius:25, fontSize:12,
                  fontWeight:'bold', marginBottom:20, textTransform:'uppercase', letterSpacing:'.7px', color:'#fff',
                  border:'1.5px solid rgba(255,255,255,.3)', transition:'all .4s ease' },
  dot:          { width:12, height:12, borderRadius:'50%', display:'inline-block' },
  errorBanner:  { padding:12, background:'#f8d7da', color:'#721c24', borderRadius:4, marginBottom:15,
                  display:'flex', justifyContent:'space-between', alignItems:'center' },
  successBanner:{ padding:12, background:'#d4edda', color:'#155724', borderRadius:4, marginBottom:15 },
  dismiss:      { background:'transparent', border:'none', color:'#721c24', cursor:'pointer', fontSize:18 },
  section:      { marginBottom:20, padding:15, background:'#fff', borderRadius:4, border:'1px solid #ddd' },
  h2:           { marginTop:0 },
  btn:          { padding:'10px 15px', fontSize:14, fontWeight:'bold', border:'none', borderRadius:4,
                  cursor:'pointer', background:'#007bff', color:'#fff' },
  btnDanger:    { background:'#dc3545' },
  btnDisabled:  { background:'#ccc', cursor:'not-allowed' },
  interim:      { fontSize:14, color:'#666', fontStyle:'italic', padding:10, background:'#f9f9f9', borderRadius:4, marginTop:10 },
  noSupport:    { color:'red', fontSize:12 },
  row:          { display:'flex', gap:10 },
  input:        { flex:1, padding:10, fontSize:14, border:'1px solid #ddd', borderRadius:4 },
  micSection:   { marginBottom:20, padding:15, background:'#f9f9f9', borderRadius:4, border:'1px solid #e0e0e0' },
  micHeader:    { display:'flex', alignItems:'center', justifyContent:'space-between', marginBottom:15 },
  micTitle:     { fontSize:14, fontWeight:600, color:'#333' },
  liveTag:      { fontSize:11, fontWeight:'bold', textTransform:'uppercase' },
  waveBox:      { display:'flex', alignItems:'center', justifyContent:'center', gap:5, height:50,
                  background:'linear-gradient(135deg,#f8f9fa,#e9ecef)', borderRadius:8, border:'1.5px solid #dee2e6' },
  bar:          { width:5, height:35, background:'#007bff', borderRadius:3, boxShadow:'0 0 8px rgba(0,123,255,.6)',
                  animation:'waveFlow .6s ease-in-out infinite' },
  waveIdle:     { display:'flex', alignItems:'center', justifyContent:'center', height:50,
                  background:'linear-gradient(135deg,#f8f9fa,#e9ecef)', borderRadius:8,
                  border:'1.5px dashed #adb5bd', color:'#6c757d', fontSize:13 },
  ts:           { fontSize:12, color:'#666', marginTop:10 },
};
