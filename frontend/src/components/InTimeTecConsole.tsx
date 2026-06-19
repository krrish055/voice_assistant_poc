// ── C4: InTimeTecConsole — System Orchestrator ────────────────────────────────
import React, { useState, useEffect, useCallback, useRef } from 'react';
import { ITT_THEME as T } from '../theme';
import { SESSION_ID } from '../constants';
import { useVADEngine, mkId } from '../hooks/useVADEngine';
import { useAudioPlayer } from '../hooks/useAudioPlayer';
import { normalizeFaqKey, findFaqHit, loadFaqMap } from '../hooks/useFaqResolver';
import VoiceService from '../services/VoiceService';
import { AppHeader }   from './AppHeader';
import { LandingView } from './LandingView';
import { ConsoleView } from './ConsoleView';
import { AppFooter }   from './AppFooter';
import type { Phase, AppLog } from '../types';

export interface InTimeTecConsoleProps { onAdminClick?: () => void }

function extractAiText(raw: string | undefined): string | null {
  if (!raw) return null;
  try {
    const parsed = JSON.parse(raw);
    return parsed.ai_response_text || parsed.ai_summary || parsed.sections?.[0]?.body || raw;
  } catch {
    return raw;
  }
}

const InTimeTecConsole: React.FC<InTimeTecConsoleProps> = ({ onAdminClick }) => {
  const [connected,      setConnected]      = useState(false);
  const [phase,          setPhase]          = useState<Phase>('idle');
  const [logs,           setLogs]           = useState<AppLog[]>([]);
  const [docUrls,        setDocUrls]        = useState<{ pdf: string | null; pptx: string | null }>({ pdf: null, pptx: null });
  const [amplitude,      setAmplitude]      = useState(1);
  const [isMicMuted,     setIsMicMuted]     = useState(false);
  const [isSpeakerMuted, setIsSpeakerMuted] = useState(false);
  const [faqMap,         setFaqMap]         = useState<Record<string, string>>({});
  const speakerMutedRef = useRef(false);
  const userId = 'user_open_mic';

  // Single shared phaseRef passed into VAD — both read/write the same object.
  const phaseRef = useRef<Phase>('idle');

  const setUI = useCallback((p: Phase) => {
    phaseRef.current = p;
    setPhase(p);
  }, []);

  const pushLog = useCallback((source: AppLog['source'], message: string) => {
    setLogs(prev => [{ id: mkId(), source, message, ts: new Date().toLocaleTimeString() }, ...prev.slice(0, 79)]);
  }, []);

  // playerRef lets onBlob always access the latest player without stale closure
  const playerRef = useRef<ReturnType<typeof useAudioPlayer> | null>(null);

  const onBlob = useCallback(async (blob: Blob) => {
    if (phaseRef.current !== 'waiting') return;
    setUI('processing');
    pushLog('SYSTEM', `Dispatching ${(blob.size / 1024).toFixed(1)} KB to pipeline…`);
    try {
      const res = await VoiceService.sendChunk(blob, userId, SESSION_ID);
      if ((phaseRef.current as Phase) === 'idle') return;
      if (res.status === 'success' && res.voice_response_url) {
        if (res.user_said) pushLog('USER', res.user_said);
        const aiText = extractAiText(res.ai_response_text);
        if (aiText) pushLog('AI', aiText);
        setDocUrls({ pdf: res.download_url ?? null, pptx: res.pptx_url ?? null });
        if (res.download_url) pushLog('SYSTEM', 'Compliance report generated.');
        if (res.pptx_url)     pushLog('SYSTEM', 'Presentation generated.');
        playerRef.current!.play(res.voice_response_url);
        if (speakerMutedRef.current) setTimeout(() => { if (playerRef.current?.audioRef.current) playerRef.current.audioRef.current.volume = 0; }, 0);
      } else if (res.status === 'queued') {
        const aiText = extractAiText(res.ai_response_text);
        if (aiText) pushLog('AI', aiText);
        setUI('waiting');
      } else {
        setUI('waiting');
        if (res.status !== 'silence') pushLog('SYSTEM', 'No response. Re-arming VAD.');
      }
    } catch {
      setUI('waiting');
    }
  }, [pushLog, setUI]);

  const vad = useVADEngine({
    phaseRef,
    onPhase    : setUI,
    onAmplitude: setAmplitude,
    onLog      : msg => pushLog('SYSTEM', msg),
    onBlob,
  });

  const player = useAudioPlayer({
    onPhase  : setUI,
    onDone   : () => { if (phaseRef.current === 'speaking') setUI('waiting'); },
    sessionId: SESSION_ID,
  });

  // Keep playerRef current every render
  playerRef.current = player;

  useEffect(() => { player.activeRef.current = vad.activeRef.current; });
  useEffect(() => () => { vad.teardown(); player.stop(); }, []); // eslint-disable-line

  const handleConnect = useCallback(async () => {
    setConnected(true);
    vad.activeRef.current = player.activeRef.current = true;
    setUI('processing');
    pushLog('SYSTEM', 'Initializing compliance node…');
    loadFaqMap().then(setFaqMap);

    try {
      await vad.startPipeline();
      // VAD calibration runs in background; phase → 'waiting' when done
    } catch (e: any) {
      pushLog('SYSTEM', `Microphone access denied: ${e?.message ?? e}`);
      vad.teardown(); player.stop();
      setUI('idle'); setConnected(false);
      return;
    }

    try {
      const data = await VoiceService.fetchWelcome();
      if (!vad.activeRef.current) return;
      if (data.audio_url) {
        pushLog('AI', 'Playing onboarding greeting.');
        // Use raw Audio — NOT player.play() — so phase is never set to 'speaking'.
        // VAD calibration owns the phase transition to 'waiting'.
        // We still call signalPlaybackComplete when audio ends.
        const audio = new Audio(VoiceService.fullUrl(data.audio_url) + `?t=${Date.now()}`);
        if (speakerMutedRef.current) audio.volume = 0;
        const onEnd = () => VoiceService.signalPlaybackComplete(SESSION_ID);
        audio.onended = onEnd;
        audio.onerror = onEnd;
        audio.play().catch(() => {});
      }
    } catch {
      pushLog('SYSTEM', 'Welcome audio unavailable. Listening…');
    }
  }, [vad, player, pushLog, setUI]);

  const toggleMic = useCallback(() => {
    const stream = vad.streamRef.current;
    if (!stream) return;
    stream.getAudioTracks().forEach(t => { t.enabled = isMicMuted; });
    setIsMicMuted(prev => !prev);
  }, [vad, isMicMuted]);

  const toggleSpeaker = useCallback(() => {
    const nowMuting = !speakerMutedRef.current;
    speakerMutedRef.current = nowMuting;
    setIsSpeakerMuted(nowMuting);
    if (player.audioRef.current) player.audioRef.current.volume = nowMuting ? 0 : 1;
  }, [player]);

  const handleDisconnect = useCallback(() => {
    vad.teardown(); player.stop();
    setUI('idle');
    setConnected(false); setIsMicMuted(false); setIsSpeakerMuted(false);
    speakerMutedRef.current = false;
  }, [vad, player, setUI]);

  const handleDispatch = useCallback(async (text: string) => {
    if (phaseRef.current === 'idle') return;
    if (phaseRef.current !== 'waiting') setUI('waiting');

    pushLog('USER', text);

    const faqHit = findFaqHit(normalizeFaqKey(text), faqMap);
    if (faqHit) {
      pushLog('AI', faqHit);
      setUI('processing');
      const audioUrl = await VoiceService.speakFaq(faqHit, SESSION_ID + '_faq');
      if (audioUrl && vad.activeRef.current) {
        player.play(audioUrl);
        if (speakerMutedRef.current) setTimeout(() => { if (player.audioRef.current) player.audioRef.current.volume = 0; }, 0);
      } else if (vad.activeRef.current) setUI('waiting');
      return;
    }

    vad.clearTimers();
    if (vad.recRef.current?.state === 'recording') { vad.recRef.current.onstop = null; vad.recRef.current.stop(); }
    setUI('processing');

    const res = await VoiceService.sendText(text, userId, SESSION_ID);
    if ((phaseRef.current as Phase) === 'idle') return;

    if (res.status === 'success' && res.voice_response_url) {
      const aiText = extractAiText(res.ai_response_text);
      if (aiText) pushLog('AI', aiText);
      setDocUrls({ pdf: res.download_url ?? null, pptx: res.pptx_url ?? null });
      if (res.download_url) pushLog('SYSTEM', 'Report ready.');
      if (res.pptx_url)     pushLog('SYSTEM', 'Presentation ready.');
      player.play(res.voice_response_url);
      if (speakerMutedRef.current) setTimeout(() => { if (player.audioRef.current) player.audioRef.current.volume = 0; }, 0);
    } else {
      setUI('waiting');
    }
  }, [vad, player, pushLog, faqMap, setUI]);

  return (
    <div style={{
      minHeight: '100vh',
      height: connected ? '100vh' : 'auto',
      backgroundColor: connected ? '#0A0B0F' : T.colors.primaryBg,
      color: T.colors.textMain,
      fontFamily: '"Inter", system-ui, sans-serif',
      display: 'flex', flexDirection: 'column',
      overflow: connected ? 'hidden' : 'visible',
    }}>
      {!connected && <AppHeader onAdminClick={onAdminClick} />}
      {!connected
        ? <LandingView onConnect={handleConnect} />
        : <ConsoleView
            phase={phase} amplitude={amplitude} logs={logs}
            dlUrl={docUrls.pdf} pptxUrl={docUrls.pptx} sessionId={SESSION_ID}
            isMicMuted={isMicMuted} isSpeakerMuted={isSpeakerMuted}
            onDisconnect={handleDisconnect}
            onToggleMic={toggleMic}
            onToggleSpeaker={toggleSpeaker}
            onDispatch={handleDispatch}
            audioElement={player.audioRef.current}
          />
      }
      {!connected && <AppFooter />}
    </div>
  );
};

export default InTimeTecConsole;
