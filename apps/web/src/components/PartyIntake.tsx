'use client';

import { useRouter } from 'next/navigation';
import { useCallback, useEffect, useState } from 'react';

import { ClaimCard } from '@/components/ClaimCard';
import { TranscriptViewer } from '@/components/TranscriptViewer';
import { VoiceRecorder } from '@/components/VoiceRecorder';
import { PARTY } from '@/lib/states';
import { claimsUrl, recordingsUrl } from '@/lib/urls';
import { toClaim, toRecording } from '@/lib/mappers';
import type { Claim, PartyRole, Recording } from '@/lib/types';

const TERMINAL: Recording['processing_status'][] = ['CLAIMS_READY', 'FAILED'];

const PROGRESS: Record<Recording['processing_status'], string> = {
  PENDING: 'Queued',
  TRANSCRIBING: 'Transcribing',
  TRANSCRIBED: 'Transcript ready — reading the account',
  EXTRACTING: 'Reading the account',
  CLAIMS_READY: 'Done',
  FAILED: 'Failed',
};

/**
 * One party's intake: record, transcript, claims.
 *
 * Processing is asynchronous — transcription plus claim extraction is a queued
 * job, not a request — so this screen polls while work is in flight and stops
 * as soon as it lands. The transcript appears before the claims do, because
 * watching your own words arrive is what makes the next screen trustworthy.
 */
export function PartyIntake({
  caseId,
  role,
  partyId,
  partyName,
  initialRecording,
  initialClaims,
  fixtureKey,
}: {
  caseId: string;
  role: PartyRole;
  partyId: string;
  partyName: string;
  initialRecording: Recording | null;
  initialClaims: Claim[];
  fixtureKey?: string | null;
}) {
  const router = useRouter();
  const [recording, setRecording] = useState(initialRecording);
  const [claims, setClaims] = useState(initialClaims);

  const inFlight = Boolean(recording && !TERMINAL.includes(recording.processing_status));

  const poll = useCallback(async () => {
    const response = await fetch(recordingsUrl(caseId), { cache: 'no-store' });
    if (!response.ok) return;

    // Same mappers as the server path. Parsing the envelope by hand here is how
    // the two sides drift the moment a Laravel resource changes.
    const body = await response.json();
    const recordings: Recording[] = (body.data ?? []).map(toRecording);
    const mine = recordings.find((item) => item.party_id === partyId) ?? null;
    setRecording(mine);

    if (mine && TERMINAL.includes(mine.processing_status)) {
      const claimsResponse = await fetch(claimsUrl(caseId, role), { cache: 'no-store' });
      if (claimsResponse.ok) {
        const claimsBody = await claimsResponse.json();
        setClaims((claimsBody.data ?? []).map(toClaim));
      }
      // Refresh the stepper and the pending-verification count in the layout.
      router.refresh();
    }
  }, [caseId, partyId, role, router]);

  useEffect(() => {
    if (!inFlight) return;
    const timer = setInterval(poll, 2500);
    return () => clearInterval(timer);
  }, [inFlight, poll]);

  const party = PARTY[role];
  const run = recording?.transcript_run ?? null;
  const current = claims.filter((claim) => !claim.is_superseded);
  const superseded = claims.filter((claim) => claim.is_superseded);

  return (
    <div className="space-y-8">
      {!recording && (
        <VoiceRecorder
          caseId={caseId}
          partyId={partyId}
          role={role}
          partyName={partyName}
          fixtureKey={fixtureKey}
          onUploaded={() => void poll()}
        />
      )}

      {recording && !TERMINAL.includes(recording.processing_status) && (
        <p className="card px-5 py-4 text-sm text-ink-soft" aria-live="polite">
          {PROGRESS[recording.processing_status]}…
        </p>
      )}

      {recording?.processing_status === 'FAILED' && (
        <div className="card border-pending/35 px-5 py-4">
          <p className="text-sm">
            Transcription did not complete
            {recording.failure_reason ? `: ${recording.failure_reason}` : '.'}
          </p>
          <p className="mt-1.5 text-sm text-ink-soft">
            The recording is kept. WUNZI does not substitute another speech model when one
            fails — that would change what the case is built on without saying so.
          </p>
        </div>
      )}

      {run && <TranscriptViewer run={run} role={role} />}

      {current.length > 0 && (
        <section>
          <h2 className="mb-1 text-sm font-medium">
            What {partyName} stated
          </h2>
          <p className="mb-4 max-w-prose text-sm text-ink-soft">
            Each card records one thing {partyName} said. Nothing here is treated as
            established — the other account has not been compared yet.
          </p>

          <div className={`grid gap-3 border-l-2 pl-4 ${party.border}`}>
            {current.map((claim) => (
              <ClaimCard key={claim.id} claim={claim} />
            ))}
          </div>
        </section>
      )}

      {superseded.length > 0 && (
        <details className="card px-5 py-4">
          <summary className="cursor-pointer text-sm text-ink-soft">
            {superseded.length === 1
              ? 'One statement the speaker corrected'
              : `${superseded.length} statements the speaker corrected`}
          </summary>
          <p className="mt-2 max-w-prose text-micro text-ink-faint">
            Corrections are kept alongside what was originally said. Both readings stay in
            the record; only the later one is current.
          </p>
          <div className="mt-3 grid gap-3">
            {superseded.map((claim) => (
              <ClaimCard key={claim.id} claim={claim} />
            ))}
          </div>
        </details>
      )}
    </div>
  );
}
