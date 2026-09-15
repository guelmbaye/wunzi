'use client';

import clsx from 'clsx';
import { useCallback, useEffect, useRef, useState } from 'react';

import { formatDuration } from '@/lib/states';
import type { PartyRole } from '@/lib/types';
import { partyRecordingsUrl } from '@/lib/urls';
import { PARTY } from '@/lib/states';

type Phase = 'idle' | 'consent' | 'recording' | 'review' | 'uploading' | 'done' | 'error';

/**
 * Voice capture for one party.
 *
 * Consent is a gate, not a checkbox buried in a footer: recording cannot start
 * until it is given, because the person about to speak is describing a dispute
 * they are party to. The API enforces the same rule — this is the humane half
 * of it, not the whole of it.
 *
 * Speakers are told plainly that mixing Kinyarwanda, English and French is fine.
 * Most speech products quietly punish switching, so people self-censor into one
 * language and lose the detail that matters.
 */
export function VoiceRecorder({
  caseId,
  partyId,
  role,
  partyName,
  fixtureKey,
  onUploaded,
}: {
  caseId: string;
  partyId: string;
  role: PartyRole;
  partyName: string;
  /**
   * Set only when the deployment replays stored provider output.
   *
   * In fixture mode a freshly recorded file has no cached transcription, so the
   * job fails and the recording is marked FAILED. Rather than let that look like
   * a bug, the screen offers the stored consented clip as a clearly labelled
   * alternative — it never substitutes it for something the speaker just said.
   */
  fixtureKey?: string | null;
  onUploaded: (recordingId: string) => void;
}) {
  const [phase, setPhase] = useState<Phase>('idle');
  const [consent, setConsent] = useState(false);
  const [elapsed, setElapsed] = useState(0);
  const [blob, setBlob] = useState<Blob | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const recorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const party = PARTY[role];

  const stopTimer = useCallback(() => {
    if (timerRef.current) clearInterval(timerRef.current);
    timerRef.current = null;
  }, []);

  useEffect(() => {
    return () => {
      stopTimer();
      recorderRef.current?.stream.getTracks().forEach((track) => track.stop());
      if (previewUrl) URL.revokeObjectURL(previewUrl);
    };
  }, [previewUrl, stopTimer]);

  async function startRecording() {
    setError(null);

    if (typeof navigator === 'undefined' || !navigator.mediaDevices) {
      setError('This browser cannot record audio. Use the file upload below instead.');
      setPhase('error');
      return;
    }

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const recorder = new MediaRecorder(stream);

      chunksRef.current = [];
      recorder.ondataavailable = (event) => {
        if (event.data.size > 0) chunksRef.current.push(event.data);
      };
      recorder.onstop = () => {
        const recorded = new Blob(chunksRef.current, { type: recorder.mimeType });
        setBlob(recorded);
        setPreviewUrl(URL.createObjectURL(recorded));
        stream.getTracks().forEach((track) => track.stop());
        setPhase('review');
      };

      recorder.start();
      recorderRef.current = recorder;
      setElapsed(0);
      setPhase('recording');
      timerRef.current = setInterval(() => setElapsed((value) => value + 1), 1000);
    } catch {
      setError('Microphone access was refused. Grant permission, or upload a file instead.');
      setPhase('error');
    }
  }

  function stopRecording() {
    stopTimer();
    recorderRef.current?.stop();
  }

  function discard() {
    if (previewUrl) URL.revokeObjectURL(previewUrl);
    setBlob(null);
    setPreviewUrl(null);
    setElapsed(0);
    setPhase('consent');
  }

  async function upload(file: Blob | null, durationMs: number, storedKey?: string) {
    setPhase('uploading');
    setError(null);

    const form = new FormData();
    if (file) {
      form.append('audio', file, 'account.webm');
    } else if (storedKey) {
      // No file: the API treats this as a replay of a stored consented clip.
      form.append('fixture_key', storedKey);
    }
    form.append('consent_recorded', 'true');
    form.append('duration_ms', String(durationMs));

    try {
      const response = await fetch(partyRecordingsUrl(partyId), {
        method: 'POST',
        body: form,
      });

      if (!response.ok) {
        const body = await response.json().catch(() => null);
        throw new Error(body?.message ?? `Upload failed (${response.status}).`);
      }

      const payload = await response.json();
      setPhase('done');
      onUploaded(payload.data?.id ?? payload.id);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Upload failed.');
      setPhase('error');
    }
  }

  // ── consent gate ─────────────────────────────────────────────────────────
  if (phase === 'idle') {
    return (
      <div className="card p-6">
        <h2 className="text-lg font-medium">Before {partyName} speaks</h2>
        <p className="mt-2 max-w-prose text-sm leading-relaxed text-ink-soft">
          This recording is stored privately and used to build a case for a human mediator.
          It is not shared with the other party without agreement, and it can be withdrawn.
          Nothing is recorded until consent is given.
        </p>

        <label className="mt-5 flex cursor-pointer items-start gap-3 rounded-card bg-paper-sunken p-4 text-sm">
          <input
            type="checkbox"
            checked={consent}
            onChange={(event) => setConsent(event.target.checked)}
            className="mt-0.5 h-4 w-4 accent-[#152131]"
          />
          <span>
            {partyName} consents to being recorded for this mediation case.
          </span>
        </label>

        <button
          type="button"
          disabled={!consent}
          onClick={() => setPhase('consent')}
          className="btn-primary mt-5"
        >
          Continue
        </button>
      </div>
    );
  }

  return (
    <div className={clsx('card overflow-hidden')}>
      <div className={clsx('h-1', party.bg)} aria-hidden />

      <div className="p-6">
        <div className="flex items-baseline justify-between gap-4">
          <div>
            <h2 className="text-lg font-medium">{partyName}, tell your side</h2>
            <p className="mt-1 text-sm text-ink-soft">
              Speak the way you normally would. Mixing Kinyarwanda, English and French in one
              sentence is expected here — you do not need to pick one.
            </p>
          </div>
          <span className="tabular shrink-0 text-2xl text-ink-soft" aria-live="polite">
            {formatDuration(elapsed * 1000)}
          </span>
        </div>

        {error && (
          <p className="mt-4 rounded-card border border-pending/40 bg-pending-soft px-3 py-2 text-sm text-pending-ink">
            {error}
          </p>
        )}

        <div className="mt-6 flex flex-wrap items-center gap-3">
          {(phase === 'consent' || phase === 'error') && (
            <button type="button" onClick={startRecording} className="btn-primary">
              <span aria-hidden className={clsx('h-2.5 w-2.5 rounded-full', party.bg)} />
              Start recording
            </button>
          )}

          {phase === 'recording' && (
            <button type="button" onClick={stopRecording} className="btn-primary">
              <span aria-hidden className="h-2.5 w-2.5 rounded-[2px] bg-paper" />
              Stop recording
            </button>
          )}

          {phase === 'review' && blob && (
            <>
              <button
                type="button"
                onClick={() => upload(blob, elapsed * 1000)}
                className="btn-primary"
              >
                Send for transcription
              </button>
              <button type="button" onClick={discard} className="btn-secondary">
                Record again
              </button>
            </>
          )}

          {phase === 'uploading' && (
            <p className="text-sm text-ink-soft">Uploading and transcribing…</p>
          )}

          {phase === 'done' && (
            <p className="text-sm text-ink">
              Recording received. Transcription is running.
            </p>
          )}
        </div>

        {previewUrl && phase === 'review' && (
          <audio controls src={previewUrl} className="mt-5 w-full" />
        )}

        {fixtureKey && (phase === 'consent' || phase === 'error') && (
          <div className="mt-6 border-t border-rule pt-5">
            <p className="text-sm text-ink-soft">
              This deployment replays stored provider output rather than calling a
              speech API, so a recording made now has no transcription to return.
              Use the stored consented clip instead.
            </p>
            <button
              type="button"
              onClick={() => upload(null, 0, fixtureKey)}
              className="btn-secondary mt-3"
            >
              Use the stored recording for {partyName}
            </button>
            <p className="tabular mt-2 text-micro text-ink-faint">{fixtureKey}</p>
          </div>
        )}

        {/* A microphone that will not open must never end the intake. */}
        {(phase === 'consent' || phase === 'error') && (
          <label className="mt-6 block border-t border-rule pt-5 text-sm text-ink-soft">
            <span className="label">Or upload an existing recording</span>
            <input
              type="file"
              accept="audio/*"
              onChange={(event) => {
                const file = event.target.files?.[0];
                if (file) void upload(file, 0);
              }}
              className="block w-full text-sm file:mr-3 file:rounded-card file:border file:border-rule-strong file:bg-paper-raised file:px-3 file:py-1.5 file:text-sm file:text-ink"
            />
          </label>
        )}
      </div>
    </div>
  );
}
