// ── C4: useVADEngine Hook ─────────────────────────────────────────────────────
// Single Responsibility: owns mic access, calibration, VAD loop, recording.
// Interface Segregation: exposes only { amplitude, startPipeline, teardown }.

import { useRef, useCallback } from 'react';
import { MIME, VAD_CONFIG } from '../constants';
import type { Phase } from '../types';

interface VADCallbacks {
  onPhase    : (p: Phase) => void;
  onAmplitude: (a: number) => void;
  onLog      : (msg: string) => void;
  onBlob     : (blob: Blob) => void;
}

const mkId = () => Math.random().toString(36).slice(2, 8);
export { mkId };

export function useVADEngine(cb: VADCallbacks) {
  const activeRef   = useRef(false);
  const streamRef   = useRef<MediaStream | null>(null);
  const actxRef     = useRef<AudioContext | null>(null);
  const analyserRef = useRef<AnalyserNode | null>(null);
  const recRef      = useRef<MediaRecorder | null>(null);
  const chunksRef   = useRef<Blob[]>([]);
  const rafRef      = useRef<number | null>(null);
  const phaseRef    = useRef<Phase>('idle');
  const noiseFloor  = useRef(20);
  const speechTim   = useRef<ReturnType<typeof setTimeout> | null>(null);
  const silenceTim  = useRef<ReturnType<typeof setTimeout> | null>(null);
  const maxTim      = useRef<ReturnType<typeof setTimeout> | null>(null);

  const setPhase = useCallback((p: Phase) => {
    phaseRef.current = p;
    cb.onPhase(p);
  }, [cb]);

  const clearTimers = useCallback(() => {
    [speechTim, silenceTim, maxTim].forEach(r => {
      if (r.current) { clearTimeout(r.current); r.current = null; }
    });
  }, []);

  const stopAndSend = useCallback(() => {
    clearTimers();
    const rec = recRef.current;
    if (!rec || rec.state !== 'recording') return;
    rec.onstop = () => {
      const blob = new Blob(chunksRef.current, { type: MIME });
      chunksRef.current = []; recRef.current = null;
      if (activeRef.current) cb.onBlob(blob);
    };
    rec.stop();
  }, [clearTimers, cb]);

  const startRecording = useCallback((stream: MediaStream) => {
    if (recRef.current?.state === 'recording') return;
    chunksRef.current = [];
    const rec = new MediaRecorder(stream, { mimeType: MIME });
    rec.ondataavailable = e => { if (e.data.size > 0) chunksRef.current.push(e.data); };
    recRef.current = rec;
    rec.start(100);
    setPhase('recording');
    cb.onLog('Recording active audio buffer…');
    maxTim.current = setTimeout(stopAndSend, VAD_CONFIG.MAX_RECORD_MS);
  }, [setPhase, cb, stopAndSend]);

  const startVADLoop = useCallback(() => {
    const analyser = analyserRef.current;
    if (!analyser) return;
    const buf = new Uint8Array(analyser.frequencyBinCount);

    const tick = () => {
      if (!activeRef.current) return;
      analyser.getByteFrequencyData(buf);
      const avg = buf.reduce((s, v) => s + v, 0) / buf.length;
      cb.onAmplitude(1 + avg / 50);
      const p    = phaseRef.current;
      const loud = avg > noiseFloor.current;

      if (p === 'waiting') {
        if (loud) {
          if (!speechTim.current)
            speechTim.current = setTimeout(() => {
              speechTim.current = null;
              if (phaseRef.current === 'waiting' && activeRef.current && streamRef.current)
                startRecording(streamRef.current);
            }, VAD_CONFIG.SPEECH_START_MS);
        } else if (speechTim.current) {
          clearTimeout(speechTim.current); speechTim.current = null;
        }
      }

      if (p === 'recording') {
        if (!loud) {
          if (!silenceTim.current)
            silenceTim.current = setTimeout(() => {
              silenceTim.current = null;
              if (phaseRef.current === 'recording' && activeRef.current) stopAndSend();
            }, VAD_CONFIG.SPEECH_STOP_MS);
        } else if (silenceTim.current) {
          clearTimeout(silenceTim.current); silenceTim.current = null;
        }
      }

      rafRef.current = requestAnimationFrame(tick);
    };
    rafRef.current = requestAnimationFrame(tick);
  }, [startRecording, stopAndSend, cb]);

  const startPipeline = useCallback(async () => {
    activeRef.current = true;
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true, video: false });
      streamRef.current = stream;

      const ctx      = new AudioContext();
      const analyser = ctx.createAnalyser();
      analyser.fftSize = VAD_CONFIG.FFT_SIZE;
      ctx.createMediaStreamSource(stream).connect(analyser);
      actxRef.current   = ctx;
      analyserRef.current = analyser;

      const buf = new Uint8Array(analyser.frequencyBinCount);
      let sum = 0, frames = 0;
      cb.onLog('Calibrating microphone noise floor…');

      const calibTick = () => {
        if (!activeRef.current) return;
        analyser.getByteFrequencyData(buf);
        sum += buf.reduce((s, v) => s + v, 0) / buf.length;
        if (++frames < VAD_CONFIG.CALIB_FRAMES) { requestAnimationFrame(calibTick); return; }
        noiseFloor.current = Math.min(55, Math.max(12, (sum / frames) * VAD_CONFIG.NOISE_MULT));
        cb.onLog(`Noise floor calibrated: ${noiseFloor.current.toFixed(1)}`);
        setPhase('waiting');
        cb.onLog('VAD loop active. Speak to begin.');
        startVADLoop();
      };
      requestAnimationFrame(calibTick);

      return stream;
    } catch {
      activeRef.current = false;
      throw new Error('Microphone access denied.');
    }
  }, [setPhase, cb, startVADLoop]);

  const teardown = useCallback(() => {
    activeRef.current = false;
    clearTimers();
    if (rafRef.current) { cancelAnimationFrame(rafRef.current); rafRef.current = null; }
    if (recRef.current?.state === 'recording') { recRef.current.onstop = null; recRef.current.stop(); }
    recRef.current = null; chunksRef.current = [];
    streamRef.current?.getTracks().forEach(t => t.stop()); streamRef.current = null;
    actxRef.current?.close(); actxRef.current = null; analyserRef.current = null;
    cb.onLog('Audio pipeline isolated. Hardware resources freed.');
  }, [clearTimers, cb]);

  return { activeRef, startPipeline, teardown, clearTimers, recRef };
}
