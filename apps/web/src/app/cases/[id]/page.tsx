import Link from 'next/link';

import { IssueSummary } from '@/components/IssueMap';
import { Count } from '@/components/StateBadge';
import { api } from '@/lib/api';
import { formatDuration, sentenceCase } from '@/lib/states';

export const metadata = { title: 'Overview' };

export default async function CaseOverviewPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const [overview, graph] = await Promise.all([
    api.getOverview(id),
    api.listIssues(id).catch(() => ({ issues: [], evidence: [] })),
  ]);

  const pending = overview.pending_critical_fields;

  return (
    <div className="space-y-10">
      {pending > 0 && (
        <div className="flex flex-wrap items-center gap-4 rounded-card border border-pending/35 bg-pending-soft/50 px-5 py-4">
          <Count value={pending} tone="alert" />
          <p className="flex-1 text-sm">
            {pending === 1
              ? 'One critical value could not be heard reliably.'
              : `${pending} critical values could not be heard reliably.`}{' '}
            The case cannot be finalised until the speakers confirm their own words.
          </p>
          <Link href={`/cases/${id}/verify`} className="btn-primary">
            Verify now
          </Link>
        </div>
      )}

      <section>
        <h2 className="mb-3 text-sm font-medium">Issue map</h2>
        {graph.issues.length > 0 ? (
          <>
            <IssueSummary issues={graph.issues} />
            <Link
              href={`/cases/${id}/issues`}
              className="mt-3 inline-block text-sm text-ink-soft hover:text-ink"
            >
              Open the issue map
            </Link>
          </>
        ) : (
          <p className="card p-5 text-sm text-ink-soft">
            The issue map is built once both accounts have been captured.
          </p>
        )}
      </section>

      <section>
        <h2 className="mb-3 text-sm font-medium">Accounts</h2>
        <div className="grid gap-4 sm:grid-cols-2">
          {overview.case.parties.map((party) => {
            const recordings = overview.recordings.filter((r) => r.party_id === party.id);
            const claims = overview.claims.filter((c) => c.party_role === party.role);
            const href = `/cases/${id}/${party.role === 'PARTY_A' ? 'party-a' : 'party-b'}`;

            return (
              <Link key={party.id} href={href} className="card p-5 hover:bg-paper-sunken/40">
                <div className="flex items-center gap-2">
                  <span
                    aria-hidden
                    className={`h-3 w-1 rounded-full ${
                      party.role === 'PARTY_A' ? 'bg-partyA' : 'bg-partyB'
                    }`}
                  />
                  <span
                    className={`text-micro font-medium ${
                      party.role === 'PARTY_A' ? 'text-partyA' : 'text-partyB'
                    }`}
                  >
                    {party.display_name}
                  </span>
                </div>

                {recordings.length === 0 ? (
                  <p className="mt-3 text-sm text-ink-faint">Not recorded yet</p>
                ) : (
                  <p className="mt-3 text-sm text-ink-soft">
                    <span className="tabular">{claims.length}</span>{' '}
                    {claims.length === 1 ? 'claim' : 'claims'} ·{' '}
                    <span className="tabular">
                      {formatDuration(recordings[0].duration_ms)}
                    </span>{' '}
                    recorded
                  </p>
                )}

                {recordings.some((r) => r.processing_status === 'FAILED') && (
                  <p className="mt-2 text-micro text-pending-ink">
                    Transcription failed — open to retry
                  </p>
                )}
              </Link>
            );
          })}
        </div>
      </section>

      <section>
        <h2 className="mb-3 text-sm font-medium">Case</h2>
        <p className="card p-5 text-sm text-ink-soft">
          {overview.case.status === 'READY'
            ? 'The mediation case is ready.'
            : 'The mediation case can be created once the issue map is built and every critical value is settled.'}{' '}
          <Link href={`/cases/${id}/packet`} className="text-ink underline underline-offset-2">
            {sentenceCase('open case packet')}
          </Link>
        </p>
      </section>
    </div>
  );
}
