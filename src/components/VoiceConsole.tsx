import React, { useState, useRef, useEffect, useCallback } from 'react';
import { Mic, MicOff, Square, MessageSquare, X, Send, Download, Radio } from 'lucide-react';
import VoiceService, { StreamResponse } from '../services/VoiceService';

type Phase = 'idle' | 'connecting' | 'waiting' | 'recording' | 'ai-speaking' | 'processing';
type Log   = { ts: string; msg: string; level: 'info' | 'ok' | 'warn' | 'err' };

const MIME             = MediaRecorder.isTypeSupported('audio/webm;codecs=opus') ? 'audio/webm;codecs=opus' : 'audio/webm';
const SESSION_ID       = 'session_' + Date.now();
const WAVE_COUNT       = 10;
const WAVE_DELAYS      = Array.from({ length: WAVE_COUNT }, (_, i) => (i * 0.07) % 0.2);
const SPEECH_START_MS  = 140;   // sustained speech needed to begin recording
const SPEECH_STOP_MS   = 2400;  // sustained silence needed to stop & send
const MAX_RECORD_MS    = 25000; // hard cap
const CALIBRATE_FRAMES = 90;    // ~1.5s @ 60fps
const NOISE_MULT       = 1.6;

const ORBS: Record<Phase, { ring: string; glow: string; label: string; icon: string }> = {
  idle:          { ring: 'border-slate-700',   glow: 'shadow-slate-700/30',  label: 'SYSTEM IDLE', icon: '○' },
  connecting:    { ring: 'border-violet-500',  glow: 'shadow-violet-500/50', label: 'CONNECTING',  icon: '◌' },
  waiting:       { ring: 'border-violet-400',  glow: 'shadow-violet-400/40', label: 'WAITING',     icon: '◎' },
  recording:     { ring: 'border-emerald-400', glow: 'shadow-emerald-500/60',label: 'RECORDING',   icon: '●' },
  'ai-speaking': { ring: 'border-cyan-400',    glow: 'shadow-cyan-500/60',   label: 'AI SPEAKING', icon: '▶' },
  processing:    { ring: 'border-amber-400',   glow: 'shadow-amber-500/50',  label: 'PROCESSING',  icon: '…' },
};

const RING_COLORS: Record<Phase, string> = {
  idle: 'bg-slate-500/10', connecting: 'bg-violet-500/15', waiting: 'bg-violet-400/10',
  recording: 'bg-emerald-400/25', 'ai-speaking': 'bg-cyan-400/20', processing: 'bg-amber-400/15',
};

const fmtTs = () => new Date().toLocaleTimeString('en-US', { hour12: false });

const VoiceConsole: React.FC = () => {
  const [phase,    setPhase]    = useState<Phase>('idle');
  const [logs,     setLogs]     = useState<Log[]>([]);
  const [dlUrl,    setDlUrl]    = useState<string | null>(null);
  const [chatOpen, setChatOpen] = useState(false);
  const [chatIn,   setChatIn]   = useState('');
  const [chatBusy, setChatBusy] = useState(false);
  const [amps,     setAmps]     = useState<number[]>(Array(WAVE_COUNT).fill(0.15));

  // ── Stable state refs (never stale in closures) ────────────────────────────
  const phaseRef      = useRef<Phase>('idle');
  const activeRef     = useRef(false);
  const streamRef     = useRef<MediaStream | null>(null);
  const recRef        = useRef<MediaRecorder | null>(null);
  const chunksRef     = useRef<Blob[]>([]);
  const audioRef      = useRef<HTMLAudioElement | null>(null);
  const actxRef       = useRef<AudioContext | null>(null);
  const analyserRef   = useRef<AnalyserNode | null>(null);
  const rafRef        = useRef<number | null>(null);
  const noiseFloor    = useRef(20);
  const speechTimRef  = useRef<ReturnType<typeof setTimeout> | null>(null);
  const silenceTimRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const maxTimRef     = useRef<ReturnType<typeof setTimeout> | null>(null);
  const logEndRef     = useRef<HTMLDivElement>(null);
  const dlUrlRef      = useRef<string | null>(null);

  // ── fn ref — single object; VAD loop reads from here, always fresh ─────────
  const fn = useRef({
    setPhase:   (p: Phase) => { phaseRef.current = p; setPhase(p); },
    log:        (msg: string, level: Log['level'] = 'info') =>
                  setLogs(prev => [...prev.slice(-49), { ts: fmtTs(), msg, level }]),
    clearTimers: () => {
      [speechTimRef, silenceTimRef, maxTimRef].forEach(r => {
        if (r.current) { clearTimeout(r.current); r.current = null; }
      });
    },
  });

  useEffect(() => { logEndRef.current?.scrollIntoView({ behavior: 'smooth' }); }, [logs]);

  // ── After AI audio finishes — go back to waiting ───────────────────────────
  const goWaiting = useCallback(() => {
    fn.current.setPhase('waiting');
    fn.current.log('🎙 Listening for speech…', 'info');
  }, []);

  // ── Play AI audio ──────────────────────────────────────────────────────────
  const playAudio = useCallback((url: string) => {
    const a = new Audio(VoiceService.fullUrl(url) + `?t=${Date.now()}`);
    audioRef.current = a;
    fn.current.setPhase('ai-speaking');
    const finish = () => {
      if (audioRef.current !== a) return;
      audioRef.current = null;
      if (activeRef.current) goWaiting();
    };
    a.onended = finish;
    a.onerror = finish;
    a.play().catch(finish);
  }, [goWaiting]);

  // ── Send blob to backend ───────────────────────────────────────────────────
  const sendBlob = useCallback(async (blob: Blob) => {
    fn.current.setPhase('processing');
    fn.current.log(`📡 Sending ${(blob.size / 1024).toFixed(1)} KB…`);

    const res: StreamResponse = await VoiceService.sendChunk(blob, SESSION_ID);
    if (!activeRef.current) return;

    if (res.status === 'success' && res.voice_response_url) {
      fn.current.log(`🤖 ${res.ai_response_text?.slice(0, 80) ?? 'AI replied.'}`, 'ok');
      if (res.download_url && res.download_url !== dlUrlRef.current) {
        dlUrlRef.current = res.download_url;
        setDlUrl(res.download_url);
        fn.current.log('📄 Report ready.', 'ok');
      }
      playAudio(res.voice_response_url);
    } else {
      fn.current.log('🔇 No speech — waiting…', 'warn');
      goWaiting();
    }
  }, [playAudio, goWaiting]);

  // ── Stop recorder & dispatch ───────────────────────────────────────────────
  const stopAndSend = useCallback(() => {
    fn.current.clearTimers();
    const rec = recRef.current;
    if (!rec || rec.state !== 'recording') return;

    rec.onstop = () => {
      const blob = new Blob(chunksRef.current, { type: MIME });
      chunksRef.current = [];
      recRef.current    = null;
      if (activeRef.current) sendBlob(blob);
    };
    rec.stop();
  }, [sendBlob]);

  // ── Start recorder ─────────────────────────────────────────────────────────
  const startRecording = useCallback((stream: MediaStream) => {
    if (recRef.current?.state === 'recording') return;
    chunksRef.current = [];
    const rec = new MediaRecorder(stream, { mimeType: MIME });
    rec.ondataavailable = e => { if (e.data.size > 0) chunksRef.current.push(e.data); };
    recRef.current = rec;
    rec.start(100);
    fn.current.setPhase('recording');
    fn.current.log('🔴 Recording…', 'ok');
    maxTimRef.current = setTimeout(stopAndSend, MAX_RECORD_MS);
  }, [stopAndSend]);

  // ── VAD tick — reads from refs, never stale ────────────────────────────────
  const vadTick = useCallback(() => {
    if (!activeRef.current || !analyserRef.current) return;
    const analyser = analyserRef.current;
    const buf = new Uint8Array(analyser.frequencyBinCount);

    const tick = () => {
      if (!activeRef.current) return;
      analyser.getByteFrequencyData(buf);
      const avg = buf.reduce((s, v) => s + v, 0) / buf.length;

      // Wave bar heights
      setAmps(Array.from({ length: WAVE_COUNT }, (_, i) => {
        const s = buf.slice(i * 4, i * 4 + 4);
        return Math.max(0.12, Math.min(1, s.reduce((a, v) => a + v, 0) / (s.length * 230)));
      }));

      const loud = avg > noiseFloor.current;
      const p    = phaseRef.current;          // always fresh — ref, not closure

      if (p === 'waiting') {
        if (loud) {
          if (!speechTimRef.current) {
            speechTimRef.current = setTimeout(() => {
              speechTimRef.current = null;
              // re-check phase from ref — not stale closure
              if (phaseRef.current === 'waiting' && activeRef.current && streamRef.current) {
                startRecording(streamRef.current);
              }
            }, SPEECH_START_MS);
          }
        } else {
          if (speechTimRef.current) { clearTimeout(speechTimRef.current); speechTimRef.current = null; }
        }
      }

      if (p === 'recording') {
        if (!loud) {
          if (!silenceTimRef.current) {
            silenceTimRef.current = setTimeout(() => {
              silenceTimRef.current = null;
              if (phaseRef.current === 'recording' && activeRef.current) {
                stopAndSend();
              }
            }, SPEECH_STOP_MS);
          }
        } else {
          if (silenceTimRef.current) { clearTimeout(silenceTimRef.current); silenceTimRef.current = null; }
        }
      }

      rafRef.current = requestAnimationFrame(tick);
    };

    rafRef.current = requestAnimationFrame(tick);
  }, [startRecording, stopAndSend]);

  // ── Calibrate then start VAD ───────────────────────────────────────────────
  const calibrateAndStart = useCallback((stream: MediaStream) => {
    if (actxRef.current) return;
    const ctx      = new AudioContext();
    const analyser = ctx.createAnalyser();
    analyser.fftSize = 256;
    ctx.createMediaStreamSource(stream).connect(analyser);
    actxRef.current   = ctx;
    analyserRef.current = analyser;

    const buf = new Uint8Array(analyser.frequencyBinCount);
    let sum = 0, frames = 0;

    fn.current.log('🔬 Calibrating mic…', 'info');

    const calibTick = () => {
      if (!activeRef.current) return;
      analyser.getByteFrequencyData(buf);
      sum += buf.reduce((s, v) => s + v, 0) / buf.length;
      if (++frames < CALIBRATE_FRAMES) { requestAnimationFrame(calibTick); return; }
      const ambient = sum / frames;
      noiseFloor.current = Math.min(55, Math.max(12, ambient * NOISE_MULT));
      fn.current.log(`🔬 Noise floor: ${noiseFloor.current.toFixed(1)}`, 'info');
      goWaiting();
      vadTick();
    };
    requestAnimationFrame(calibTick);
  }, [goWaiting, vadTick]);

  // ── Full teardown ──────────────────────────────────────────────────────────
  const teardown = useCallback(() => {
    activeRef.current = false;
    fn.current.clearTimers();
    rafRef.current && cancelAnimationFrame(rafRef.current); rafRef.current = null;
    if (recRef.current?.state === 'recording') { recRef.current.onstop = null; recRef.current.stop(); }
    recRef.current = null; chunksRef.current = [];
    streamRef.current?.getTracks().forEach(t => t.stop()); streamRef.current = null;
    actxRef.current?.close(); actxRef.current = null; analyserRef.current = null;
    if (audioRef.current) {
      audioRef.current.onended = null; audioRef.current.pause();
      audioRef.current.src = ''; audioRef.current = null;
    }
    setPhase('idle'); phaseRef.current = 'idle';
    setAmps(Array(WAVE_COUNT).fill(0.15));
  }, []);

  useEffect(() => () => teardown(), []); // eslint-disable-line react-hooks/exhaustive-deps

  // ── Connect ────────────────────────────────────────────────────────────────
  const handleConnect = useCallback(async () => {
    if (phaseRef.current !== 'idle') return;
    fn.current.setPhase('connecting');
    fn.current.log('🔗 Connecting…');
    activeRef.current = true;

    try {
      // Release any stale AudioContext before requesting mic
      if (actxRef.current) { actxRef.current.close(); actxRef.current = null; }

      const stream = await navigator.mediaDevices.getUserMedia({ audio: true, video: false });
      streamRef.current = stream;

      const data = await VoiceService.fetchWelcome();
      if (!activeRef.current) return;

      if (data.audio_url) {
        fn.current.setPhase('ai-speaking');
        fn.current.log('👋 Playing welcome…', 'ok');
        const a = new Audio(VoiceService.fullUrl(data.audio_url) + `?t=${Date.now()}`);
        audioRef.current = a;
        const done = () => { audioRef.current = null; if (activeRef.current) calibrateAndStart(stream); };
        a.onended = done; a.onerror = done;
        a.play().catch(done);
      } else {
        calibrateAndStart(stream);
      }
    } catch (e: any) {
      const msg = e?.name ? `${e.name}: ${e.message}` : (e?.message ?? String(e));
      fn.current.log(`❌ ${msg}`, 'err');
      teardown();
    }
  }, [calibrateAndStart, teardown]);

  // ── Chat fallback ──────────────────────────────────────────────────────────
  const handleChatSend = useCallback(async () => {
    const text = chatIn.trim();
    if (!text || chatBusy) return;
    setChatIn(''); setChatBusy(true);
    fn.current.log(`💬 "${text.slice(0, 60)}"`, 'info');

    fn.current.clearTimers();
    if (recRef.current?.state === 'recording') { recRef.current.onstop = null; recRef.current.stop(); recRef.current = null; }
    fn.current.setPhase('processing');

    const res = await VoiceService.sendText(text, SESSION_ID);
    setChatBusy(false);
    if (!activeRef.current) return;

    if (res.status === 'success' && res.voice_response_url) {
      fn.current.log(`🤖 ${res.ai_response_text?.slice(0, 80) ?? 'AI replied.'}`, 'ok');
      if (res.download_url) { setDlUrl(res.download_url); fn.current.log('📄 Report ready.', 'ok'); }
      playAudio(res.voice_response_url);
    } else {
      goWaiting();
    }
  }, [chatIn, chatBusy, playAudio, goWaiting]);

  const isActive = phase !== 'idle';
  const orb      = ORBS[phase];
  const LOG_C    = { info: 'text-slate-400', ok: 'text-emerald-400', warn: 'text-amber-400', err: 'text-red-400' };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col items-center p-6 gap-5 overflow-x-hidden">

      <div className="w-full max-w-2xl flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Radio size={18} className="text-cyan-400" />
          <div>
            <h1 className="text-sm font-bold tracking-widest uppercase text-slate-200">Compliance Voice Node</h1>
            <p className="text-[10px] text-slate-600 tracking-wide">AI · Hands-Free · Speech-Gated</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <button onClick={() => setChatOpen(o => !o)}
            className={`p-2 rounded-lg border transition-colors ${chatOpen
              ? 'bg-cyan-500/20 border-cyan-500/50 text-cyan-400'
              : 'bg-slate-900 border-slate-800 text-slate-500 hover:text-slate-300'}`}>
            <MessageSquare size={15} />
          </button>
          {isActive && (
            <button onClick={teardown}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-red-900/40 border border-red-800/60 text-red-400 hover:bg-red-900/70 text-xs font-semibold transition-colors">
              <Square size={11} /> Stop
            </button>
          )}
        </div>
      </div>

      <div className="w-full max-w-2xl bg-slate-900/50 backdrop-blur-md border border-slate-800/80 rounded-3xl p-8 flex flex-col items-center gap-8">
        <div className="relative flex items-center justify-center w-52 h-52">
          {isActive && [0, 0.5, 1].map(d => (
            <span key={d} className={`ripple-ring ${RING_COLORS[phase]}`} style={{ animationDelay: `${d}s` }} />
          ))}
          <div className={`absolute inset-6 rounded-full border-2 ${orb.ring} ${isActive ? `shadow-xl ${orb.glow}` : ''} transition-all duration-500`} />
          <div className={`relative z-10 flex flex-col items-center justify-center w-28 h-28 rounded-full bg-slate-950 border ${orb.ring} shadow-2xl ${orb.glow} transition-all duration-500`}>
            <span className="text-2xl leading-none">{orb.icon}</span>
            <span className="text-[9px] font-bold tracking-widest mt-1 text-slate-400">{orb.label}</span>
          </div>
        </div>

        <div className="flex items-end justify-center gap-1 h-10">
          {WAVE_DELAYS.map((delay, i) => (
            <div key={i} className={`wave-bar transition-colors duration-300 ${
              phase === 'recording'   ? 'bg-emerald-400' :
              phase === 'ai-speaking' ? 'bg-cyan-400'    : 'bg-slate-700'
            }`} style={{
              animationDelay: `${delay}s`,
              height: `${(isActive ? amps[i] : 0.15) * 40}px`,
              animationPlayState: isActive ? 'running' : 'paused',
            }} />
          ))}
        </div>

        {!isActive ? (
          <button onClick={handleConnect}
            className="flex items-center gap-2 px-8 py-3.5 rounded-2xl bg-gradient-to-r from-violet-600 to-cyan-600
              hover:from-violet-500 hover:to-cyan-500 text-white font-bold text-sm tracking-wide
              shadow-lg shadow-violet-500/20 transition-all active:scale-95 slide-up">
            <Mic size={16} /> Connect Compliance Node
          </button>
        ) : (
          <div className="flex items-center gap-2 px-4 py-2 rounded-full bg-slate-800/80 border border-slate-700/50 text-xs text-slate-400 slide-up">
            <span className={`w-1.5 h-1.5 rounded-full animate-pulse ${
              phase === 'recording'   ? 'bg-emerald-400' :
              phase === 'ai-speaking' ? 'bg-cyan-400'    :
              phase === 'processing'  ? 'bg-amber-400'   : 'bg-violet-400'
            }`} />
            {orb.label} · {SESSION_ID.slice(-8)}
            {phase === 'processing' && <span className="spinner ml-1" />}
          </div>
        )}

        {dlUrl && (
          <a href={VoiceService.fullUrl(dlUrl)} target="_blank" rel="noreferrer"
            className="flex items-center gap-2 px-5 py-2.5 rounded-xl bg-emerald-900/50 border border-emerald-700/50
              hover:bg-emerald-900/80 text-emerald-400 text-xs font-semibold transition-colors slide-up">
            <Download size={13} /> Download Compliance Report
          </a>
        )}
      </div>

      {chatOpen && (
        <div className="w-full max-w-2xl bg-slate-900/50 backdrop-blur-md border border-slate-800/80 rounded-3xl overflow-hidden slide-up">
          <div className="flex items-center justify-between px-5 py-3 border-b border-slate-800/80">
            <div className="flex items-center gap-2 text-xs">
              <MessageSquare size={13} className="text-cyan-400" />
              <span className="font-semibold text-slate-300">Chat Fallback</span>
              <span className="text-slate-600">· type instead of speaking</span>
            </div>
            <button onClick={() => setChatOpen(false)} className="text-slate-600 hover:text-slate-300"><X size={14} /></button>
          </div>
          <div className="p-4 flex gap-2">
            <input type="text" value={chatIn}
              onChange={e => setChatIn(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && handleChatSend()}
              disabled={chatBusy} placeholder="Type your request…"
              className="flex-1 bg-slate-950 border border-slate-800 rounded-xl px-4 py-2.5 text-sm
                text-slate-200 placeholder-slate-700 focus:outline-none focus:border-cyan-500/50
                disabled:opacity-40 transition-colors"
            />
            <button onClick={handleChatSend} disabled={chatBusy || !chatIn.trim()}
              className="px-4 py-2.5 rounded-xl bg-cyan-600 hover:bg-cyan-500 disabled:opacity-30 text-white text-sm font-semibold transition-colors">
              {chatBusy ? <span className="spinner" /> : <Send size={14} />}
            </button>
          </div>
        </div>
      )}

      <div className="w-full max-w-2xl bg-slate-900/50 backdrop-blur-md border border-slate-800/80 rounded-3xl p-5">
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2 text-xs">
            <span className="w-1.5 h-1.5 rounded-full bg-cyan-400 animate-pulse" />
            <span className="font-semibold text-slate-400 tracking-wide uppercase">Pipeline Log</span>
          </div>
          <div className="flex items-center gap-3">
            {isActive ? <Mic size={12} className="text-emerald-400 animate-pulse" /> : <MicOff size={12} className="text-slate-700" />}
            <button onClick={() => setLogs([])} className="text-[10px] text-slate-700 hover:text-slate-500">clear</button>
          </div>
        </div>
        <div className="font-mono text-[11px] space-y-0.5 max-h-44 overflow-y-auto pr-1">
          {logs.length === 0
            ? <span className="text-slate-800">No pipeline events yet.</span>
            : logs.map((l, i) => (
              <div key={i} className="flex gap-2 slide-up">
                <span className="text-slate-700 shrink-0">[{l.ts}]</span>
                <span className={LOG_C[l.level]}>{l.msg}</span>
              </div>
            ))
          }
          <div ref={logEndRef} />
        </div>
      </div>
    </div>
  );
};

export default VoiceConsole;
