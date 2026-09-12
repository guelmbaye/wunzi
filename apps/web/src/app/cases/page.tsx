import Link from 'next/link';

import { api } from '@/lib/api';
import { CASE_STATUS_LABEL, formatRelative, sentenceCase } from '@/lib/states';
import { Count } from '@/components/StateBadge';
import { ServiceUnavailable } from '@/components/ServiceUnavailable';

export const metadata = { title: 'Cases' };

/** Deliberately not a metrics dashboard. The list exists to get out of the way. */
export default async function CasesPage() {
  // Keep the failure, don't flatten it: the reason is what tells a developer
  // whether the API is down, unreachable, or refusing the token.
  let cases: Awaited<ReturnType<typeof api.listCases>> | null = null;
  let failure: unknown = null;

  try {
    cases = await api.listCases();
  } catch (cause) {
    failure = cause;
  }

  return (
    <div className="mx-auto w-full max-w-6xl px-5 py-10">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <h1 className="text-3xl font-medium">Mediation cases</h1>
        <Link href="/cases/new" className="btn-primary">
          New case
        </Link>
      </div>

      {cases === null ? (
        <div className="mt-8">
          <ServiceUnavailable error={failure} subject="The case list" />
        </div>
      ) : cases.length === 0 ? (
        <div className="card mt-8 p-8">
          <h2 className="font-medium">No cases yet</h2>
          <p className="mt-2 max-w-prose text-sm leading-relaxed text-ink-soft">
            A case begins with one person describing what happened, in whatever mix of
            languages they normally speak. The second account comes after.
          </p>
          <Link href="/cases/new" className="btn-primary mt-5">
            Start the first case
          </Link>
        </div>
      ) : (
        <ul className="mt-8 divide-y divide-rule border-y border-rule">
          {cases.map((item) => (
            <li key={item.id}>
              <Link
                href={`/cases/${item.id}`}
                className="group flex flex-wrap items-center gap-x-6 gap-y-2 py-5 transition-colors hover:bg-paper-sunken/60"
              >
                <div className="min-w-0 flex-1">
                  <p className="font-medium">
                    {item.title ?? sentenceCase(item.category)}
                  </p>
                  <p className="mt-1 text-sm text-ink-faint">
                    <span className="tabular">{item.public_reference}</span>
                    {' · '}
                    {item.parties.map((party) => party.display_name).join(' and ')}
                  </p>
                </div>

                {item.counts && item.counts.pending_critical_fields > 0 && (
                  <span className="flex items-center gap-2 text-sm text-pending-ink">
                    <Count value={item.counts.pending_critical_fields} tone="alert" />
                    to verify
                  </span>
                )}

                <span className="text-sm text-ink-soft">
                  {CASE_STATUS_LABEL[item.status]}
                </span>

                <span className="w-24 text-right text-sm text-ink-faint">
                  {formatRelative(item.updated_at)}
                </span>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
