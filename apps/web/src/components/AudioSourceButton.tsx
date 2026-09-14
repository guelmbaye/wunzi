'use client';

import clsx from 'clsx';
import { useEffect, useRef, useState } from 'react';

import { claimAudioSourceUrl } from '@/lib/urls';

/**
 * The audit trail made clickable: plays only the span of audio a claim came
 * from.
 *
 * The signed URL is fetched on the first press, never shipped with the list.
 * Signed URLs expire in ten minutes, so a page of forty claims carrying forty
 * of them would hand the browser thirty-nine links that are already dead by the
 * time anyone clicks one — and would put thirty-nine live grants to private
 * mediation audio in a payload nobody asked for.
 */
export function AudioSourceButton({
  claimId,
  label = 'Hear source',
  className,
}: {
  claimId: string;
  label?: string;
  className?: string;
}) {
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const [playing, setPlaying] = useState(false);
  const [loading, setLoading] = useState(false);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    return () => {
      audioRef.current?.pause();
      audioRef.current = null;
    };
  }, []);

  async function toggle() {
    if (playing) {
      audioRef.current?.pause();
      setPlaying(false);
      return;
    }

    setFailed(false);

    try {
      if (!audioRef.current) {
        setLoading(true);
        const response = await fetch(claimAudioSourceUrl(claimId), { cache: 'no-store' });
        if (!response.ok) throw new Error(String(response.status));

        const source = await response.json();
        const audio = new Audio(source.audio_url);
        const endSeconds = (source.end_ms ?? 0) / 1000;

        audio.currentTime = (source.start_ms ?? 0) / 1000;
        // Stop at the end of the claim's span, not the end of the recording:
        // the point is to hear the sentence, not the whole account.
        audio.ontimeupdate = () => {
          if (endSeconds && audio.currentTime >= endSeconds) {
            audio.pause();
            setPlaying(false);
          }
        };
        audio.onended = () => setPlaying(false);
        audio.onerror = () => {
          setFailed(true);
          setPlaying(false);
        };

        audioRef.current = audio;
        setLoading(false);
      }

      await audioRef.current.play();
      setPlaying(true);
    } catch {
      setLoading(false);
      setFailed(true);
    }
  }

  if (failed) {
    return (
      <span className={clsx('text-micro text-ink-faint', className)}>
        Source audio unavailable
      </span>
    );
  }

  return (
    <button
      type="button"
      onClick={toggle}
      disabled={loading}
      className={clsx(
        'inline-flex items-center gap-1.5 rounded-card px-2 py-1 text-micro text-ink-soft transition-colors hover:bg-paper-sunken hover:text-ink disabled:opacity-50',
        className,
      )}
    >
      <span aria-hidden className="text-[9px] leading-none">
        {playing ? '❙❙' : '▶'}
      </span>
      {loading ? 'Loading' : playing ? 'Playing' : label}
    </button>
  );
}
