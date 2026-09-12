'use client';

import clsx from 'clsx';
import { useEffect, useRef, useState } from 'react';

import { audioSourceUrl } from '@/lib/urls';

/**
 * The audit trail made clickable: plays only the span of audio a claim came
 * from.
 *
 * Every consequential sentence in WUNZI can be traced back to the voice that
 * produced it. That chain — statement → claim → segment → audio → timestamp —
 * is what separates a structured case from a summary a mediator has to trust.
 */
export function AudioSourceButton({
  recordingId,
  startMs,
  endMs,
  label = 'Hear source',
  className,
}: {
  recordingId: string;
  startMs: number;
  endMs: number;
  label?: string;
  className?: string;
}) {
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const [playing, setPlaying] = useState(false);
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

    const audio =
      audioRef.current ??
      new Audio(audioSourceUrl(recordingId, startMs, endMs));

    audioRef.current = audio;
    audio.currentTime = 0;
    audio.onended = () => setPlaying(false);
    audio.onerror = () => {
      setFailed(true);
      setPlaying(false);
    };

    try {
      await audio.play();
      setPlaying(true);
    } catch {
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
      className={clsx(
        'inline-flex items-center gap-1.5 rounded-card px-2 py-1 text-micro text-ink-soft transition-colors hover:bg-paper-sunken hover:text-ink',
        className,
      )}
    >
      <span aria-hidden className="text-[9px] leading-none">
        {playing ? '❙❙' : '▶'}
      </span>
      {playing ? 'Playing' : label}
    </button>
  );
}
