'use client';

import clsx from 'clsx';
import { useRouter } from 'next/navigation';
import { useState } from 'react';

import { PARTY, sentenceCase } from '@/lib/states';
import type { CriticalField } from '@/lib/types';
import { verificationUrl } from '@/lib/urls';

import { AudioSourceButton } from './AudioSourceButton';

/**
 * A targeted verification for one critical field.
 *
 * Only the speaker may confirm or correct their own words — a mediator can
 * annotate a case but cannot rewrite what a party said. The question comes from
 * the server verbatim and is never rephrased here: the Critical Speech Guard
 * writes it to be non-suggestive ("I heard the amount as 150,000 RWF. Is that
 * correct?"), and a friendlier rewrite in the UI would tell the speaker what to
 * answer.
 *
 * "Not sure" is a first-class answer. Forcing a choice between yes and no would
 * manufacture certainty that does not exist, which is the failure this whole
 * screen exists to prevent.
 */
export function VerificationCard({ field }: { field: CriticalField }) {
  const router = useRouter();
  const party = PARTY[field.party_role];

  const [correcting, setCorrecting] = useState(false);
  const [correctedValue, setCorrectedValue] = useState(field.detected_value ?? '');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const resolved = field.status !== 'NEEDS_CONFIRMATION';

  async function resolve(
    resolution: 'CONFIRMED' | 'CORRECTED' | 'UNRESOLVED',
    value?: string,
  ) {
    setBusy(true);
    setError(null);

    try {
      const response = await fetch(verificationUrl(field.id), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ resolution, corrected_value: value }),
      });

      if (!response.ok) {
        const body = await response.json().catch(() => null);
        throw new Error(body?.message ?? `Could not save (${response.status}).`);
      }

      router.refresh();
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Could not save.');
    } finally {
      setBusy(false);
    }
  }

  return (
    <article
      className={clsx(
        'card overflow-hidden',
        resolved ? 'opacity-70' : 'border-pending/35',
      )}
    >
      <div className="flex items-center gap-3 border-b border-rule px-5 py-2.5">
        <span aria-hidden className={clsx('h-3 w-1 rounded-full', party.bg)} />
        <span className={clsx('text-micro font-medium', party.text)}>{party.label}</span>
        <span className="text-micro text-ink-faint">{sentenceCase(field.field_type)}</span>

        {resolved && (
          <span className="ml-auto text-micro text-ink-soft">
            {field.status === 'CORRECTED' ? 'Corrected' : sentenceCase(field.status)}
          </span>
        )}
      </div>

      <div className="px-5 py-4">
        <p className="text-sm leading-relaxed text-ink-soft">{field.claim_statement}</p>

        <p className="mt-3 text-base leading-relaxed">{field.prompt_text}</p>

        {field.has_audio_source && (
          <AudioSourceButton
            claimId={field.claim_id}
            label="Hear what was recorded"
            className="-ml-2 mt-2"
          />
        )}

        {error && (
          <p className="mt-3 rounded-card border border-pending/40 bg-pending-soft px-3 py-2 text-sm text-pending-ink">
            {error}
          </p>
        )}

        {!resolved && (
          <div className="mt-4">
            {correcting ? (
              <div className="flex flex-wrap items-end gap-3">
                <label className="flex-1">
                  <span className="label">What it should say</span>
                  <input
                    value={correctedValue}
                    onChange={(event) => setCorrectedValue(event.target.value)}
                    className="field tabular"
                    autoFocus
                  />
                </label>

                <button
                  type="button"
                  disabled={busy || !correctedValue.trim()}
                  onClick={() => resolve('CORRECTED', correctedValue.trim())}
                  className="btn-primary"
                >
                  Save correction
                </button>
                <button
                  type="button"
                  onClick={() => setCorrecting(false)}
                  className="btn-quiet"
                >
                  Cancel
                </button>
              </div>
            ) : (
              <div className="flex flex-wrap gap-2">
                <button
                  type="button"
                  disabled={busy}
                  onClick={() => resolve('CONFIRMED')}
                  className="btn-primary"
                >
                  Yes, that is correct
                </button>
                <button
                  type="button"
                  disabled={busy}
                  onClick={() => setCorrecting(true)}
                  className="btn-secondary"
                >
                  No, correct it
                </button>
                <button
                  type="button"
                  disabled={busy}
                  onClick={() => resolve('UNRESOLVED')}
                  className="btn-quiet"
                >
                  Not sure
                </button>
              </div>
            )}
          </div>
        )}

        {!resolved && field.guard_reason.length > 0 && (
          <details className="mt-4 border-t border-rule pt-3">
            <summary className="cursor-pointer text-micro text-ink-faint">
              Why this is being checked
            </summary>
            <ul className="mt-2 space-y-1 text-micro text-ink-soft">
              {field.guard_reason.map((reason) => (
                <li key={reason}>{sentenceCase(reason)}</li>
              ))}
            </ul>
          </details>
        )}
      </div>
    </article>
  );
}
