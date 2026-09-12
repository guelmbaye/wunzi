import clsx from 'clsx';

import { PARTY, formatValue, sentenceCase } from '@/lib/states';
import type { Claim } from '@/lib/types';

import { AudioSourceButton } from './AudioSourceButton';

const VERIFICATION_LABEL: Record<Claim['verification_status'], string> = {
  UNVERIFIED: 'Not yet verified',
  CONFIRMED_BY_SPEAKER: 'Speaker confirmed',
  CORRECTED_BY_SPEAKER: 'Corrected by speaker',
  UNRESOLVED: 'Unresolved',
};

/**
 * One atomic claim.
 *
 * The card never renders a bare fact. "Deposit amount: 150,000 RWF" would turn
 * one person's account into the record; every card leads with who said it. Two
 * further distinctions survive to the surface:
 *
 *   reported speech — "Party A states that Party B promised a refund" is not
 *                     "Party B promised a refund", and the card says so
 *   negation        — a lost "not" reverses an issue, so polarity is shown as
 *                     part of the sentence rather than as a flag
 */
export function ClaimCard({ claim }: { claim: Claim }) {
  const party = PARTY[claim.party_role];
  const value = formatValue(claim.canonical_value);
  const verified =
    claim.verification_status === 'CONFIRMED_BY_SPEAKER' ||
    claim.verification_status === 'CORRECTED_BY_SPEAKER';

  return (
    <article
      className={clsx(
        'card flex gap-4 p-4',
        claim.is_superseded && 'opacity-60',
      )}
    >
      <span aria-hidden className={clsx('w-1 shrink-0 rounded-full', party.bg)} />

      <div className="min-w-0 flex-1">
        <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1">
          <h3 className="text-sm font-medium">{sentenceCase(claim.type)}</h3>

          {claim.reported_speech && (
            <span className="rounded-full border border-rule-strong px-2 py-0.5 text-micro text-ink-soft">
              Quoting the other party
            </span>
          )}

          {claim.is_superseded && (
            <span className="text-micro text-ink-faint">Corrected by the speaker</span>
          )}
        </div>

        <p className="mt-1.5 text-sm leading-relaxed text-ink">{claim.statement}</p>

        {value && (
          <p className={clsx('tabular mt-2 text-amount', party.text)}>{value}</p>
        )}

        <div className="mt-3 flex flex-wrap items-center gap-x-4 gap-y-1">
          <span
            className={clsx(
              'text-micro',
              verified ? 'text-ink' : 'text-ink-faint',
            )}
          >
            {verified && <span aria-hidden>✓ </span>}
            {VERIFICATION_LABEL[claim.verification_status]}
          </span>

          {claim.audio && (
            <AudioSourceButton
              recordingId={claim.audio.recording_id}
              startMs={claim.audio.start_ms}
              endMs={claim.audio.end_ms}
              className="-ml-2"
            />
          )}
        </div>
      </div>
    </article>
  );
}
