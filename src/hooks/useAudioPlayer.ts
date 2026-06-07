// ── C4: useAudioPlayer Hook ───────────────────────────────────────────────────
// Single Responsibility: owns HTMLAudioElement lifecycle only.

import { useRef, useCallback } from 'react';
import VoiceService from '../services/VoiceService';
import type { Phase } from '../types';

interface PlayerCallbacks {
  onPhase: (p: Phase) => void;
  onDone : () => void;
}

export function useAudioPlayer(cb: PlayerCallbacks) {
  const audioRef  = useRef<HTMLAudioElement | null>(null);
  const activeRef = useRef(false);

  const play = useCallback((url: string, onDone?: () => void) => {
    const a = new Audio(VoiceService.fullUrl(url) + `?t=${Date.now()}`);
    audioRef.current = a;
    cb.onPhase('speaking');
    const finish = () => {
      if (audioRef.current !== a) return;
      audioRef.current = null;
      onDone ? onDone() : (activeRef.current && cb.onDone());
    };
    a.onended = finish;
    a.onerror = finish;
    a.play().catch(finish);
  }, [cb]);

  const stop = useCallback(() => {
    if (audioRef.current) {
      audioRef.current.onended = null;
      audioRef.current.pause();
      audioRef.current.src = '';
      audioRef.current = null;
    }
  }, []);

  return { play, stop, audioRef, activeRef };
}
