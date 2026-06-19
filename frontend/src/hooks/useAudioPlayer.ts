import { useRef, useCallback } from 'react';
import VoiceService from '../services/VoiceService';
import type { Phase } from '../types';

interface PlayerCallbacks {
  onPhase   : (p: Phase) => void;
  onDone    : () => void;
  sessionId : string;
}

export function useAudioPlayer(cb: PlayerCallbacks) {
  // Store callbacks in a ref so closures always read the latest version.
  // This eliminates every stale-closure bug without needing useCallback deps.
  const cbRef    = useRef(cb);
  cbRef.current  = cb;

  const audioRef  = useRef<HTMLAudioElement | null>(null);
  const activeRef = useRef(false);

  const play = useCallback((url: string, onDone?: () => void) => {
    const a = new Audio(VoiceService.fullUrl(url) + `?t=${Date.now()}`);
    audioRef.current = a;
    cbRef.current.onPhase('speaking');

    const finish = () => {
      if (audioRef.current !== a) return;
      audioRef.current = null;
      VoiceService.signalPlaybackComplete(cbRef.current.sessionId).finally(() => {
        if (onDone) {
          onDone();
        } else if (activeRef.current) {
          cbRef.current.onDone();
        }
      });
    };

    a.onended = finish;
    a.onerror = finish;
    a.play().catch(finish);
  }, []); // no deps — cbRef always current

  const stop = useCallback(() => {
    if (audioRef.current) {
      audioRef.current.onended = null;
      audioRef.current.onerror = null;
      audioRef.current.pause();
      audioRef.current.src = '';
      audioRef.current = null;
      VoiceService.signalPlaybackComplete(cbRef.current.sessionId);
    }
  }, []);

  return { play, stop, audioRef, activeRef };
}
