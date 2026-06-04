import React, { useState, useRef, useEffect, useCallback } from 'react';
import VoiceService, { AudioStreamResponse } from '../services/VoiceService';

// ── Types ─────────────────────────────────────────────────────────────────────

type NetStatus = 'disconnected' | 'connecting' | 'connected' | 'error';

interface ChatTurn {
  role: 'user' | 'ai';
  text: string;
  download_url?: string | null;
}

interface LogEntry {
  ts: string;
  msg: string;
  type: 'info' | 'success' | 'error' | 'warn';
}

// ── Constants ─────────────────────────────────────────────────────────────────

const now = () => new Date().toLocaleTimeString('en-US', { hour12: false });

const STATUS_STYLES: Record<NetStatus, { bg: string; dot: string; label: string }> = {
  disconnected: { bg: 'bg-slate-700',      dot: 'bg-slate-400',   label: 'Disconnected'         },
  connecting:   { bg: 'bg-amber-900/60',   dot: 'bg-amber-400',   label: 'Connecting...'        },
  connected:    { bg: 'bg-emerald-900/60', dot: 'bg-emerald-400', label: 'Connected via WebRTC' },
  error:        { bg: 'bg-red-900/60',     dot: 'bg-red-400',     label: 'Connection Error'     },
};

const LOG_COLORS: Record<LogEntry['type'], string> = {
  info:    'text-slate-400',
  success: 'text-emerald-400',
  error:   'text-red-400',
  warn:    'text-amber-400',
};

const WAVE_DELAYS = [0, 0.08, 0.16, 0.12, 0.04, 0.18, 0.09];

// ── Component ─────────────────────────────────────────────────────────────────

const VoiceConsole: React.FC = () => {
  const [netStatus,    setNetStatus]    = useState<NetStatus>('disconnected');
  const [chat,         setChat]         = useState<ChatTurn[]>([]);
  const [logs,         setLogs]         = useState<LogEntry[]>([]);
  const [isRecording,  setIsRecording]  = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const [audioSrc,     setAudioSrc]     = useState<string | null>(null);
  const [textInput,    setTextInput]    = useState('');

  const userId    = useRef('user_'    + Date.now());
  const sessionId = useRef('session_' + Date.now());
  const recorderRef  = useRef<MediaRecorder | null>(null);
  const chunksRef    = useRef<Blob[]>([]);
  const streamRef    = useRef<MediaStream | null>(null);
  const chatEndRef   = useRef<HTMLDivElement>(null);
  const audioRef     = useRef<HTMLAudioElement>(null);

  const isConnected = netStatus === 'connected';

  // Auto-connect on mount
  useEffect(() => { handleConnect(); }, []); // eslint-disable-line react-hooks/exhaustive-deps

  // Auto-scroll chat
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [chat]);

  // Auto-play on new audio
  useEffect(() => {
    if (audioSrc && audioRef.current) {
      audioRef.current.load();
      audioRef.current.play().catch(() => {});
    }
  }, [audioSrc]);

  const log = useCallback((msg: string, type: LogEntry['type'] = 'info') => {
    setLogs(p => [...p.slice(-49), { ts: now(), msg, type }]);
  }, []);

  // ── Shared response handler ────────────────────────────────────────────────

  const handleResponse = useCallback((res: AudioStreamResponse, userText?: string) => {
    if (res.status !== 'success') {
      log(`Pipeline error: ${res.message}`, 'error');
      return;
    }

    const displayText = userText ?? res.user_said ?? '';
    log(`Transcription: "${res.user_said ?? userText}"`, 'success');

    setChat(p => [
      ...p,
      { role: 'user', text: displayText },
      { role: 'ai',   text: res.ai_response_text ?? '', download_url: res.download_url },
    ]);

    if (res.voice_response_url) {
      // Cache-buster: prevent browser serving stale audio asset
      setAudioSrc(`${VoiceService.audioUrl(res.voice_response_url)}?t=${Date.now()}`);
      log('TTS audio mounted — playing response.', 'success');
    }

    if (res.download_url) log('Compliance report ready — download available.', 'success');
  }, [log]);

  // ── LiveKit Handshake ──────────────────────────────────────────────────────

  const handleConnect = async () => {
    setNetStatus('connecting');
    log('Initiating LiveKit authentication handshake...');
    try {
      const data = await VoiceService.getLiveKitToken('main-room', userId.current);
      if (data.status === 'success' && data.token) {
        setNetStatus('connected');
        log(`Token acquired · Server: ${data.server_url}`, 'success');
      } else {
        throw new Error('Invalid token response');
      }
    } catch (e) {
      setNetStatus('error');
      log(`Handshake failed: ${e instanceof Error ? e.message : e}`, 'error');
    }
  };

  // ── Tap-to-Talk Toggle ────────────────────────────────────────────────────

  const handleMicToggle = async () => {
    if (isProcessing) return;

    // ── Second tap: stop recording ──
    if (isRecording) {
      recorderRef.current?.stop();         // fires onstop → handleAudioReady
      setIsRecording(false);
      log('Recording stopped — packaging blob...', 'info');
      return;
    }

    // ── First tap: start recording ──
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true, video: false });
      streamRef.current = stream;
      chunksRef.current = [];

      const mime = MediaRecorder.isTypeSupported('audio/webm;codecs=opus')
        ? 'audio/webm;codecs=opus' : 'audio/webm';

      const recorder = new MediaRecorder(stream, { mimeType: mime });
      recorder.ondataavailable = e => { if (e.data.size > 0) chunksRef.current.push(e.data); };
      recorder.onstop = () => handleAudioReady(mime);
      recorderRef.current = recorder;
      recorder.start(100);
      setIsRecording(true);
      log('VAD triggered — capturing audio frames...', 'info');
    } catch (e) {
      log(`Mic access denied: ${e instanceof Error ? e.message : e}`, 'error');
    }
  };

  const handleAudioReady = async (mime: string) => {
    // Explicit hardware teardown — prevent mic icon staying active
    streamRef.current?.getTracks().forEach(t => t.stop());
    streamRef.current = null;

    const blob = new Blob(chunksRef.current, { type: mime });
    chunksRef.current = [];

    if (blob.size < 500) {
      log('Audio too short — ignoring.', 'warn');
      return;
    }

    setIsProcessing(true);
    log(`Dispatching ${(blob.size / 1024).toFixed(1)} KB to STT pipeline...`);

    const res = await VoiceService.sendAudioBlob(userId.current, sessionId.current, blob);
    setIsProcessing(false);
    handleResponse(res);
  };

  // ── Text Fallback ─────────────────────────────────────────────────────────

  const handleSendText = async () => {
    const text = textInput.trim();
    if (!text || isProcessing) return;
    setTextInput('');
    setIsProcessing(true);
    log(`Dispatching text fallback: "${text}"`);

    const res = await VoiceService.sendTextFallback(userId.current, sessionId.current, text);
    setIsProcessing(false);
    handleResponse(res, text);
  };

  // ── New Session ───────────────────────────────────────────────────────────

  const handleNewSession = () => {
    recorderRef.current?.stop();
    streamRef.current?.getTracks().forEach(t => t.stop());
    streamRef.current = null;

    sessionId.current = 'session_' + Date.now();
    setNetStatus('disconnected');
    setChat([]);
    setLogs([]);
    setAudioSrc(null);
    setTextInput('');
    setIsRecording(false);
    setIsProcessing(false);
    log('New session initialized.', 'info');
  };

  // ── Render ────────────────────────────────────────────────────────────────

  const { bg, dot, label } = STATUS_STYLES[netStatus];
  const lastDownload = [...chat].reverse().find(t => t.role === 'ai' && t.download_url);

  return (
    <div className="min-h-screen bg-slate-900 text-slate-100 p-4 md:p-8">
      <div className="max-w-3xl mx-auto space-y-4">

        {/* ── Header ── */}
        <div className="flex items-start justify-between">
          <div>
            <h1 className="text-xl font-bold tracking-tight text-white">
              🎙️ Voice Compliance Console
            </h1>
            <p className="text-slate-500 text-xs mt-0.5">AI-powered document gateway</p>
          </div>
          <button
            onClick={handleNewSession}
            className="text-xs text-slate-400 hover:text-white border border-slate-700 hover:border-slate-500 px-3 py-1.5 rounded-lg transition-colors"
          >
            + New Session
          </button>
        </div>

        {/* ── Connection Bar ── */}
        <div className="bg-slate-800 border border-slate-700 rounded-2xl p-4 flex items-center gap-3">
          <div className={`flex items-center gap-2 px-3 py-1 rounded-full text-xs font-semibold ${bg}`}>
            <span className={`w-2 h-2 rounded-full ${dot} ${netStatus === 'connecting' ? 'animate-pulse' : ''}`} />
            {label}
          </div>
          {!isConnected && (
            <button
              onClick={handleConnect}
              disabled={netStatus === 'connecting'}
              className="text-xs bg-sky-600 hover:bg-sky-500 disabled:opacity-40 disabled:cursor-not-allowed px-4 py-1.5 rounded-full font-semibold transition-colors"
            >
              {netStatus === 'connecting' ? 'Connecting...' : 'Connect'}
            </button>
          )}
          {isConnected && (
            <span className="text-xs text-slate-600 ml-auto font-mono">
              {sessionId.current.slice(-10)}
            </span>
          )}
        </div>

        {/* ── Main Grid ── */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">

          {/* ── Tap-to-Talk Panel ── */}
          <div className="bg-slate-800 border border-slate-700 rounded-2xl p-6 flex flex-col items-center gap-5">
            <div className="text-center">
              <p className="text-sm font-semibold text-slate-200">Tap to Talk</p>
              <p className="text-xs text-slate-500 mt-0.5">Tap once to record · Tap again to send</p>
            </div>

            {/* Mic Button */}
            <div className="relative flex items-center justify-center w-24 h-24">
              {isRecording && (
                <span className="absolute inset-0 rounded-full bg-red-500/30 animate-ping" />
              )}
              <button
                onClick={handleMicToggle}
                disabled={isProcessing}
                className={`relative z-10 w-20 h-20 rounded-full flex items-center justify-center text-2xl
                  transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-sky-500 select-none
                  ${isProcessing
                    ? 'bg-slate-700 text-slate-500 cursor-not-allowed'
                    : isRecording
                    ? 'bg-red-500 text-white shadow-lg shadow-red-500/40 scale-105'
                    : 'bg-sky-600 hover:bg-sky-500 text-white shadow-lg shadow-sky-600/30 active:scale-95'
                  }`}
              >
                {isProcessing
                  ? <span className="spinner" />
                  : isRecording ? '⏹' : '🎤'
                }
              </button>
            </div>

            {/* Wave Visualizer */}
            <div className="flex items-center justify-center gap-1 h-10 w-full">
              {isRecording
                ? WAVE_DELAYS.map((d, i) => (
                    <div key={i} className="wave-bar" style={{ animationDelay: `${d}s` }} />
                  ))
                : <p className="text-xs text-slate-600">
                    {isProcessing ? 'Processing...' : 'Waveform idle'}
                  </p>
              }
            </div>

            <p className="text-xs font-mono text-center px-3 py-1.5 rounded-lg bg-slate-900/60 text-slate-500 w-full">
              {isRecording ? '● REC — Tap to send' : isProcessing ? '⏳ Pipeline running...' : '○ Ready'}
            </p>
          </div>

          {/* ── Audio Player + Download ── */}
          <div className="bg-slate-800 border border-slate-700 rounded-2xl p-6 flex flex-col gap-4">
            <p className="text-sm font-semibold text-slate-200">AI Voice Response</p>

            {audioSrc ? (
              <div className="space-y-2">
                <audio
                  ref={audioRef}
                  src={audioSrc}
                  controls
                  className="w-full rounded-lg"
                  style={{ colorScheme: 'dark', accentColor: '#38bdf8' }}
                />
                <p className="text-xs text-emerald-400">✓ TTS response loaded</p>
              </div>
            ) : (
              <div className="flex-1 flex items-center justify-center border border-dashed border-slate-700 rounded-xl h-20">
                <p className="text-xs text-slate-600">Response audio appears here</p>
              </div>
            )}

            {lastDownload && (
              <a
                href={VoiceService.audioUrl(lastDownload.download_url!)}
                target="_blank"
                rel="noreferrer"
                className="flex items-center justify-center gap-2 w-full py-2.5 rounded-xl
                           bg-emerald-700 hover:bg-emerald-600 text-white text-sm font-semibold transition-colors"
              >
                📄 Download Compliance Report
              </a>
            )}
          </div>
        </div>

        {/* ── Chat History ── */}
        <div className="bg-slate-800 border border-slate-700 rounded-2xl p-5">
          <p className="text-sm font-semibold text-slate-200 mb-3">Conversation</p>
          <div className="space-y-3 max-h-72 overflow-y-auto pr-1">
            {chat.length === 0
              ? <p className="text-xs text-slate-600 text-center py-8">
                  Connect and speak or type to begin...
                </p>
              : chat.map((turn, i) => (
                <div key={i} className={`flex ${turn.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                  <div className={`max-w-[80%] px-4 py-2.5 rounded-2xl text-sm leading-relaxed
                    ${turn.role === 'user'
                      ? 'bg-sky-600 text-white rounded-br-sm'
                      : 'bg-slate-700 text-slate-200 rounded-bl-sm'
                    }`}>
                    <p className="text-[10px] font-bold opacity-50 mb-1">
                      {turn.role === 'user' ? 'YOU' : 'AI ASSISTANT'}
                    </p>
                    {turn.text}
                  </div>
                </div>
              ))
            }
            {isProcessing && (
              <div className="flex justify-start">
                <div className="bg-slate-700 px-4 py-3 rounded-2xl rounded-bl-sm flex gap-1 items-center">
                  {[0, 0.15, 0.3].map(d => (
                    <span
                      key={d}
                      className="w-1.5 h-1.5 bg-slate-400 rounded-full animate-bounce"
                      style={{ animationDelay: `${d}s` }}
                    />
                  ))}
                </div>
              </div>
            )}
            <div ref={chatEndRef} />
          </div>
        </div>

        {/* ── Text Fallback ── */}
        <div className="bg-slate-800 border border-slate-700 rounded-2xl p-4">
          <p className="text-xs text-slate-500 mb-2 font-medium">Keyboard Fallback</p>
          <div className="flex gap-2">
            <input
              type="text"
              value={textInput}
              onChange={e => setTextInput(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && handleSendText()}
              disabled={isProcessing}
              placeholder="Type a message and press Enter or Send..."
              className="flex-1 bg-slate-900 border border-slate-700 rounded-xl px-4 py-2.5 text-sm
                         text-slate-200 placeholder-slate-600 focus:outline-none focus:border-sky-500
                         disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
            />
            <button
              onClick={handleSendText}
              disabled={isProcessing || !textInput.trim()}
              className="bg-sky-600 hover:bg-sky-500 disabled:opacity-40 disabled:cursor-not-allowed
                         px-4 py-2.5 rounded-xl text-sm font-semibold transition-colors"
            >
              Send
            </button>
          </div>
        </div>

        {/* ── Execution Log ── */}
        <div className="bg-slate-800 border border-slate-700 rounded-2xl p-5">
          <div className="flex items-center justify-between mb-3">
            <p className="text-sm font-semibold text-slate-200 flex items-center gap-2">
              <span className="w-1.5 h-1.5 rounded-full bg-sky-400 animate-pulse" />
              Execution Log
            </p>
            <button
              onClick={() => setLogs([])}
              className="text-xs text-slate-600 hover:text-slate-400 transition-colors"
            >
              Clear
            </button>
          </div>
          <div className="font-mono text-xs space-y-1 max-h-40 overflow-y-auto pr-1">
            {logs.length === 0
              ? <p className="text-slate-700">No events yet.</p>
              : logs.map((l, i) => (
                <div key={i} className="flex gap-2">
                  <span className="text-slate-600 shrink-0">[{l.ts}]</span>
                  <span className={LOG_COLORS[l.type]}>{l.msg}</span>
                </div>
              ))
            }
          </div>
        </div>

      </div>
    </div>
  );
};

export default VoiceConsole;
