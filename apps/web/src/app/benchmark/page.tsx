import Link from 'next/link';

import { api } from '@/lib/api';
import { formatRelative } from '@/lib/states';
import { PROVIDER_LABEL } from '@/components/BenchmarkComparison';
import { ServiceUnavailable } from '@/components/ServiceUnavailable';

export const metadata = { title: 'Benchmark' };

/**
 * Benchmark mode is separate from the mediator workflow on purpose. A mediator
 * should never have to read a confidence interval to run a case; a technical
 * judge should never have to dig for one.
 */
export default async function BenchmarkPage() {
  let runs: Awaited<ReturnType<typeof api.listBenchmarkRuns>> | null = null;
  let failure: unknown = null;

  try {
    runs = await api.listBenchmarkRuns();
  } catch (cause) {
    failure = cause;
  }
  const latest = runs?.[0] ?? null;

  return (
    <div className="mx-auto w-full max-w-6xl px-5 py-10">
      <header className="max-w-prose">
        <h1 className="text-display font-medium">Same voice. Different outcome.</h1>
        <p className="mt-5 text-lg leading-relaxed text-ink-soft">
          The question is not which model transcribes more words correctly. It is whether
          the speech model preserved the dispute — whether a mediator reading the case would
          have understood the same thing.
        </p>
      </header>

      {runs === null ? (
        <div className="mt-10">
          <ServiceUnavailable error={failure} subject="The benchmark list" />
        </div>
      ) : runs.length === 0 ? (
        <div className="card mt-10 p-8">
          <h2 className="font-medium">No runs yet</h2>
          <p className="mt-2 max-w-prose text-sm leading-relaxed text-ink-soft">
            Start one with <span className="tabular">make benchmark</span>, or from the API.
            A run scores every scenario against each speech model over identical audio.
          </p>
        </div>
      ) : (
        <>
          {latest && (
            <Link
              href={`/benchmark/${latest.id}`}
              className="card mt-10 block p-6 transition-colors hover:bg-paper-sunken/40"
            >
              <p className="text-sm text-ink-soft">Most recent run</p>
              <p className="mt-1 font-medium">
                {latest.dataset_version} · {latest.split} split ·{' '}
                {latest.providers.map((p) => PROVIDER_LABEL[p] ?? p).join(', ')}
              </p>
              {latest.results?.publishable === false && (
                <p className="mt-3 inline-block rounded-card border border-pending/40 bg-pending-soft px-2.5 py-1 text-micro text-pending-ink">
                  Pipeline smoke test — not a measured result
                </p>
              )}
            </Link>
          )}

          <h2 className="mt-12 mb-3 text-sm font-medium">All runs</h2>
          <ul className="divide-y divide-rule border-y border-rule">
            {runs.map((run) => (
              <li key={run.id}>
                <Link
                  href={`/benchmark/${run.id}`}
                  className="flex flex-wrap items-center gap-x-6 gap-y-1 py-4 hover:bg-paper-sunken/40"
                >
                  <span className="min-w-0 flex-1 text-sm">
                    {run.dataset_version} · {run.split}
                    {!run.guard_enabled && (
                      <span className="ml-2 text-micro text-ink-faint">guard disabled</span>
                    )}
                  </span>

                  <span className="tabular text-sm text-ink-soft">
                    {run.results?.publishable === false
                      ? '—'
                      : run.sponsor_outcome_delta !== null
                        ? `${run.sponsor_outcome_delta > 0 ? '+' : ''}${run.sponsor_outcome_delta.toFixed(1)} pts`
                        : run.status}
                  </span>

                  <span className="w-24 text-right text-sm text-ink-faint">
                    {run.completed_at ? formatRelative(run.completed_at) : run.status}
                  </span>
                </Link>
              </li>
            ))}
          </ul>
        </>
      )}
    </div>
  );
}
