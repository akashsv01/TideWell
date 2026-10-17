"use client";

import { useCallback, useEffect, useRef, useState } from "react";

export type RecorderState = "idle" | "recording";

// Chrome and Firefox record webm. Safari and iOS record mp4.
function pickMimeType(): string | undefined {
  if (typeof MediaRecorder === "undefined") return undefined;
  const options = ["audio/webm;codecs=opus", "audio/webm", "audio/mp4"];
  return options.find((t) => MediaRecorder.isTypeSupported(t));
}

type AudioContextCtor = typeof AudioContext;

/**
 * Browser microphone recorder. start() may throw an Error with a message safe to show the user.
 * levelRef.current is the live voice loudness from 0 to 1. It is a ref, not state, so reading it
 * every animation frame does not re-render the page.
 */
export function useRecorder() {
  const [state, setState] = useState<RecorderState>("idle");
  const [seconds, setSeconds] = useState(0);
  const levelRef = useRef(0);
  const recorder = useRef<MediaRecorder | null>(null);
  const stream = useRef<MediaStream | null>(null);
  const chunks = useRef<Blob[]>([]);
  const timer = useRef<ReturnType<typeof setInterval> | null>(null);
  const meter = useRef<{ ctx: AudioContext; raf: number } | null>(null);

  const cleanup = useCallback(() => {
    if (timer.current) clearInterval(timer.current);
    timer.current = null;
    if (meter.current) {
      cancelAnimationFrame(meter.current.raf);
      void meter.current.ctx.close().catch(() => {});
      meter.current = null;
    }
    levelRef.current = 0;
    stream.current?.getTracks().forEach((t) => t.stop());
    stream.current = null;
    recorder.current = null;
  }, []);

  // Release the microphone if the page unmounts mid-recording.
  useEffect(() => cleanup, [cleanup]);

  // Measures loudness for the orb animation. Failing here must never break recording.
  const startMeter = useCallback((media: MediaStream) => {
    try {
      const Ctx: AudioContextCtor | undefined =
        window.AudioContext ??
        (window as unknown as { webkitAudioContext?: AudioContextCtor }).webkitAudioContext;
      if (!Ctx) return;
      const ctx = new Ctx();
      const analyser = ctx.createAnalyser();
      analyser.fftSize = 256;
      ctx.createMediaStreamSource(media).connect(analyser);
      const samples = new Uint8Array(analyser.fftSize);
      const state = { ctx, raf: 0 };
      const tick = () => {
        analyser.getByteTimeDomainData(samples);
        let sum = 0;
        for (const s of samples) {
          const v = (s - 128) / 128;
          sum += v * v;
        }
        const rms = Math.sqrt(sum / samples.length);
        // Ease toward the new value so the water moves smoothly instead of jittering.
        levelRef.current += (Math.min(1, rms * 5) - levelRef.current) * 0.25;
        state.raf = requestAnimationFrame(tick);
      };
      state.raf = requestAnimationFrame(tick);
      meter.current = state;
    } catch {
      /* no animation, recording still works */
    }
  }, []);

  const start = useCallback(async () => {
    if (!navigator.mediaDevices?.getUserMedia || typeof MediaRecorder === "undefined") {
      throw new Error("This browser can't record audio. Please type instead.");
    }
    let media: MediaStream;
    try {
      media = await navigator.mediaDevices.getUserMedia({ audio: true });
    } catch {
      throw new Error("Microphone access is blocked. Allow the microphone in your browser, or type instead.");
    }
    const mimeType = pickMimeType();
    const rec = new MediaRecorder(media, mimeType ? { mimeType } : undefined);
    chunks.current = [];
    rec.ondataavailable = (e) => {
      if (e.data.size > 0) chunks.current.push(e.data);
    };
    rec.start();
    stream.current = media;
    recorder.current = rec;
    startMeter(media);
    setSeconds(0);
    setState("recording");
    timer.current = setInterval(() => setSeconds((n) => n + 1), 1000);
  }, [startMeter]);

  const stop = useCallback(
    () =>
      new Promise<Blob>((resolve, reject) => {
        const rec = recorder.current;
        if (!rec) {
          reject(new Error("Not recording"));
          return;
        }
        rec.onstop = () => {
          const blob = new Blob(chunks.current, { type: rec.mimeType || "audio/webm" });
          cleanup();
          setState("idle");
          resolve(blob);
        };
        rec.stop();
      }),
    [cleanup]
  );

  return { state, seconds, levelRef, start, stop };
}
