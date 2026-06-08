// ── C4: InTimeTecConsole — System Orchestrator ────────────────────────────────
// Single Responsibility: wires hooks to sub-components. Zero UI logic here.
// Dependency Inversion: depends on abstractions (hooks/services), not concretions.

import React, { useState, useEffect, useCallback } from 'react';
import { ITT_THEME as T } from '../theme';
import { SESSION_ID } from '../constants';
import { useVADEngine, mkId } from '../hooks/useVADEngine';
import { useAudioPlayer } from '../hooks/useAudioPlayer';
import { normalizeFaqKey, findFaqHit } from '../hooks/useFaqResolver';
import VoiceService from '../services/VoiceService';
import { AppHeader }      from './AppHeader';
import { LandingView }    from './LandingView';
import { ConsoleView }    from './ConsoleView';
import { FallbackDrawer } from './FallbackDrawer';
import { AppFooter }      from './AppFooter';
import type { Phase, AppLog } from '../types';

const InTimeTecConsole: React.FC = () => {
  const [connected,  setConnected]  = useState(false);
  const [phase,      setPhase]      = useState<Phase>('idle');
  const [logs,       setLogs]       = useState<AppLog[]>([]);
  const [docUrls, setDocUrls] = useState<{ pdf: string | null; pptx: string | null }>({ pdf: null, pptx: null });
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [amplitude,  setAmplitude]  = useState(1);

  const pushLog = useCallback((source: AppLog['source'], message: string) => {
    setLogs(prev => [{ id: mkId(), source, message, ts: new Date().toLocaleTimeString() }, ...prev.slice(0, 79)]);
  }, []);

  const player = useAudioPlayer({
    onPhase: setPhase,
    onDone : () => { setPhase('waiting'); pushLog('SYSTEM', 'VAD loop active. Speak to begin.'); },
  });

  const vad = useVADEngine({
    onPhase    : setPhase,
    onAmplitude: setAmplitude,
    onLog      : msg => pushLog('SYSTEM', msg),
    onBlob     : async (blob) => {
      setPhase('processing');
      pushLog('SYSTEM', `Dispatching ${(blob.size / 1024).toFixed(1)} KB to pipeline…`);
      const res = await VoiceService.sendChunk(blob, SESSION_ID);
      if (!vad.activeRef.current) return;
      if (res.status === 'success' && res.voice_response_url) {
        if (res.user_said)        pushLog('USER', res.user_said);
        if (res.ai_response_text) pushLog('AI',   res.ai_response_text);
        setDocUrls({ pdf: res.download_url ?? null, pptx: res.pptx_url ?? null });
        if (res.download_url) pushLog('SYSTEM', 'Compliance report generated.');
        if (res.pptx_url)     pushLog('SYSTEM', 'Presentation generated.');
        player.play(res.voice_response_url);
      } else {
        setPhase('waiting');
        pushLog('SYSTEM', 'Silent sample received. Re-arming VAD.');
      }
    },
  });

  // Sync player's activeRef with vad's activeRef
  useEffect(() => { player.activeRef.current = vad.activeRef.current; });

  useEffect(() => () => { vad.teardown(); player.stop(); }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const handleConnect = useCallback(async () => {
    setConnected(true);
    vad.activeRef.current    = true;
    player.activeRef.current = true;
    setPhase('processing');
    pushLog('SYSTEM', 'Initializing compliance node authentication…');
    try {
      const data = await VoiceService.fetchWelcome();
      if (!vad.activeRef.current) return;
      if (data.audio_url) {
        pushLog('AI', 'Playing onboarding greeting.');
        player.play(data.audio_url, () => { if (vad.activeRef.current) vad.startPipeline(); });
      } else {
        vad.startPipeline();
      }
    } catch (e: any) {
      pushLog('SYSTEM', `Handshake failed: ${e?.message ?? e}`);
      vad.teardown(); player.stop();
      setConnected(false);
    }
  }, [vad, player, pushLog]);

  const handleDisconnect = useCallback(() => {
    vad.teardown(); player.stop();
    setConnected(false); setDrawerOpen(false);
  }, [vad, player]);

  const handleDispatch = useCallback(async (text: string) => {
    pushLog('USER', text);
    const faqHit = findFaqHit(normalizeFaqKey(text));
    if (faqHit) {
      pushLog('AI', faqHit);
      setPhase('processing');
      const audioUrl = await VoiceService.speakFaq(faqHit, SESSION_ID + '_faq');
      if (audioUrl && vad.activeRef.current) player.play(audioUrl);
      else if (vad.activeRef.current)        setPhase('waiting');
      return;
    }
    vad.clearTimers();
    if (vad.recRef.current?.state === 'recording') { vad.recRef.current.onstop = null; vad.recRef.current.stop(); }
    setPhase('processing');
    const res = await VoiceService.sendText(text, SESSION_ID);
    if (!vad.activeRef.current) return;
    if (res.status === 'success' && res.voice_response_url) {
      if (res.ai_response_text) pushLog('AI', res.ai_response_text);
      setDocUrls({ pdf: res.download_url ?? null, pptx: res.pptx_url ?? null });
      if (res.download_url) pushLog('SYSTEM', 'Report ready.');
      if (res.pptx_url)     pushLog('SYSTEM', 'Presentation ready.');
      player.play(res.voice_response_url);
    } else {
      setPhase('waiting');
    }
  }, [vad, player, pushLog]);

  return (
    <div style={{
      minHeight: '100vh', backgroundColor: T.colors.primaryBg,
      color: T.colors.textMain, fontFamily: '"Inter", system-ui, sans-serif',
      display: 'flex', flexDirection: 'column', overflowX: 'hidden',
    }}>
      <AppHeader />
      {!connected
        ? <LandingView onConnect={handleConnect} />
        : <ConsoleView
            phase={phase} amplitude={amplitude} logs={logs}
            dlUrl={docUrls.pdf} pptxUrl={docUrls.pptx} sessionId={SESSION_ID}
            onDisconnect={handleDisconnect}
            onOpenDrawer={() => setDrawerOpen(true)}
          />
      }
      <AppFooter />
      <FallbackDrawer
        open={drawerOpen} logs={logs}
        onClose={() => setDrawerOpen(false)}
        onDispatch={handleDispatch}
      />
    </div>
  );
};

export default InTimeTecConsole;
