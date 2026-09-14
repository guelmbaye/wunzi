import Link from 'next/link';

import { Count } from '@/components/StateBadge';
import { api } from '@/lib/api';
import { ISSUE_STATE, sentenceCase } from '@/lib/states';
import type { IssueStatus } from '@/lib/types';

export const metadata = { title: 'Overview' };

/**
 * Case overview.
 *
 * Reads Laravel's own `{case, progress, summary}` shape rather than a second
 * one invented here. The API already counts the four mediation states and the
 * pending verifications in a single query; recomputing them from a claim dump
 * would be slower and would let the two counts drift apart.
 */
export default async function CaseOverviewPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const overview = await api.getOverview(id);

  const { summary, progress } = overview;
  const pending = summary.fields_needing_verification;
  const hasIssues = summary.agreed + summary.disputed + summary.missing + summary.unverified > 0;

  const counts: { status: IssueStatus; value: number }[] = [
    { status: 'DISPUTED', value: summary.disputed },
    { status: 'UNVERIFIED', value: summary.unverified },
    { status: 'MISSING', value: summary.missing },
    { status: 'AGREED', value: summary.agreed },
  ];

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

        {hasIssues ? (
          <>
            <dl className="grid grid-cols-2 gap-3 sm:grid-cols-4">
              {counts.map(({ status, value }) => (
                <div
                  key={status}
                  className={`rounded-card border p-4 ${ISSUE_STATE[status].panel}`}
                >
                  <dt className="text-micro text-ink-soft">{ISSUE_STATE[status].label}</dt>
                  <dd className="tabular mt-1 text-2xl">{value}</dd>
                </div>
              ))}
            </dl>
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
            const captured = party.role === 'PARTY_A' ? progress.party_a : progress.party_b;
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

                <p className="mt-3 text-sm text-ink-soft">
                  {captured ? 'Account captured' : 'Not recorded yet'}
                </p>
              </Link>
            );
          })}
        </div>
      </section>

      <section>
        <h2 className="mb-3 text-sm font-medium">Case</h2>
        <div className="card p-5">
          <p className="text-sm text-ink-soft">
            {progress.packet
              ? 'The mediation case has been created.'
              : progress.verification && progress.issue_map
                ? 'Everything critical is settled. The mediation case can be created.'
                : 'The mediation case can be created once the issue map is built and every critical value is settled.'}
          </p>
          <Link
            href={`/cases/${id}/packet`}
            className="mt-3 inline-block text-sm text-ink underline underline-offset-2"
          >
            {progress.packet ? 'Open the case packet' : 'Go to the case packet'}
          </Link>
        </div>
      </section>

      <p className="text-micro text-ink-faint">
        {sentenceCase(overview.case.category)} ·{' '}
        <span className="tabular">{overview.case.public_reference}</span>
      </p>
    </div>
  );
}
