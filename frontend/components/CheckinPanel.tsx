"use client";

import { useEffect, useRef, useState, useSyncExternalStore } from "react";
import AppleHealthButton from "@/components/AppleHealthButton";
import Orb from "@/components/Orb";
import UrgentCard from "@/components/UrgentCard";
import { checkin, replyAudioSrc } from "@/lib/api";
import { usePatientId } from "@/lib/session";
import {
  getSpokenReplies,
  spokenRepliesServerValue,
  subscribeSpokenReplies,
} from "@/lib/prefs";
import type { CheckinResponse } from "@/lib/types";
import { btnPrimary, focusRing } from "@/lib/ui";
import { useRecorder } from "@/lib/useRecorder";

export default function CheckinPanel() {
  const patientId = usePatientId();
  const { state, seconds, levelRef, start, stop } = useRecorder();
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState<CheckinResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [showText, setShowText] = useState(false);
  const [text, setText] = useState("");
  const [needsTap, setNeedsTap] = useState(false);
  const [playing, setPlaying] = useState(false);
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const spoken = useSyncExternalStore(
    subscribeSpokenReplies,
    getSpokenReplies,
    spokenRepliesServerValue
  );

  const recording = state === "recording";

  // Stop any reply audio if the page goes away.
  useEffect(() => {
    return () => {
      audioRef.current?.pause();
    };
  }, []);

  function stopAudio() {
    audioRef.current?.pause();
    audioRef.current = null;
    setPlaying(false);
  }

  function play(b64: string) {
    audioRef.current?.pause();
    const audio = new Audio(replyAudioSrc(b64));
    audioRef.current = audio;
    audio.onended = () => setPlaying(false);
    // Some phones block autoplay after a network call. Offer a Play button if so.
    audio.play().then(
      () => {
        setNeedsTap(false);
        setPlaying(true);
      },
      () => {
        setNeedsTap(true);
        setPlaying(false);
      }
    );
  }

  async function send(input: { text?: string; audio?: Blob }) {
    if (!patientId) return; // RequirePatient renders this panel only once there is an id
    setBusy(true);
    setError(null);
    setResult(null);
    setNeedsTap(false);
    try {
      const res = await checkin(patientId, input);
      setResult(res);
      if (res.red_flag) stopAudio();
      else if (res.reply_audio_base64 && spoken) play(res.reply_audio_base64);
    } catch {
      setError("Something went wrong sending your check-in. Please try again, or type instead.");
    } finally {
      setBusy(false);
    }
  }

  async function onMic() {
    // aria-disabled keeps keyboard focus on the button, so ignore taps while busy.
    if (busy) return;
    setError(null);
    if (recording) {
      try {
        const audio = await stop();
        await send({ audio });
      } catch {
        setError("We couldn't save that recording. Please try again, or type instead.");
      }
      return;
    }
    stopAudio(); // so the microphone does not pick up the reply
    try {
      await start();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Couldn't start the microphone.");
    }
  }

  async function onSubmitText(e: React.FormEvent) {
    e.preventDefault();
    const value = text.trim();
    if (!value || busy) return;
    setText("");
    await send({ text: value });
  }

  // SAFETY: the urgent card shows only fixed text and never the reply text.
  if (result?.red_flag)
    return (
      <UrgentCard
        level={result.red_flag_level ?? "emergency"}
        supportAlerted={Boolean(result.support_alerted)}
        onBack={() => setResult(null)}
      />
    );

  const status = recording
    ? "Listening. Tap the button again when you are done."
    : busy
      ? "Thinking about what you said."
      : result
        ? ""
        : "Tap the button and tell me how you are feeling today.";

  const sendDisabled = busy || !text.trim();
  const orbState = recording ? "recording" : busy ? "busy" : "idle";

  return (
    <div className="flex flex-1 flex-col items-center">
      <p aria-live="polite" className="min-h-14 max-w-[26ch] text-center text-xl leading-snug">
        {status}
      </p>

      <Orb state={orbState} seconds={seconds} levelRef={levelRef} onClick={onMic} />

      <AppleHealthButton />

      <div aria-live="polite" className="mt-6 w-full">
        {result && (
          <section
            aria-label="Tidewell's reply"
            className="rounded-2xl bg-white p-6 shadow-paper ring-1 ring-navy/10 motion-safe:animate-reply-in motion-reduce:animate-fade-in"
          >
            <p className="text-xl leading-relaxed">{result.reply_text}</p>
            {result.citations && result.citations.length > 0 && (
              <p className="mt-4 text-base text-navy/80">
                Source:{" "}
                {result.citations.map((c, i) => (
                  <span key={c.url}>
                    {i > 0 && ", "}
                    <a
                      href={c.url}
                      target="_blank"
                      rel="noreferrer"
                      className={`rounded font-semibold underline underline-offset-2 ${focusRing}`}
                    >
                      {c.source}
                    </a>
                  </span>
                ))}
              </p>
            )}
            <div className="mt-5 flex flex-wrap gap-3">
              {result.reply_audio_base64 && (
                <button
                  type="button"
                  onClick={() => (playing ? stopAudio() : play(result.reply_audio_base64!))}
                  className={`inline-flex min-h-12 items-center rounded-full border-2 border-navy px-5 font-semibold ${focusRing}`}
                >
                  {playing ? "Stop audio" : needsTap || !spoken ? "Hear the reply" : "Play again"}
                </button>
              )}
              <button
                type="button"
                onClick={() => {
                  stopAudio();
                  setResult(null);
                }}
                className={`inline-flex min-h-12 items-center rounded-full bg-navy px-5 font-semibold text-white ${focusRing}`}
              >
                New check-in
              </button>
            </div>
          </section>
        )}
        {error && (
          <p role="alert" className="rounded-2xl bg-white p-5 text-lg text-alert ring-2 ring-alert/30">
            {error}
          </p>
        )}
      </div>

      <div className="mt-8 w-full max-w-md">
        {!showText ? (
          <button
            type="button"
            onClick={() => setShowText(true)}
            className={`min-h-12 w-full rounded-full px-4 text-lg font-semibold underline underline-offset-4 ${focusRing}`}
          >
            Type instead
          </button>
        ) : (
          <form onSubmit={onSubmitText} className="flex flex-col gap-3 motion-safe:animate-step-in">
            <label htmlFor="checkin-text" className="text-lg font-semibold">
              How are you feeling today?
            </label>
            <textarea
              id="checkin-text"
              value={text}
              onChange={(e) => setText(e.target.value)}
              rows={4}
              className={`w-full rounded-2xl border-2 border-navy bg-white p-3 text-lg ${focusRing}`}
            />
            <button type="submit" aria-disabled={sendDisabled} className={btnPrimary}>
              Send
            </button>
          </form>
        )}
      </div>
    </div>
  );
}
