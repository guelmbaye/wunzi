import Link from 'next/link';
import { notFound } from 'next/navigation';

import { BenchmarkComparison } from '@/components/BenchmarkComparison';
import { MetricCards, SponsorDeltaCard } from '@/components/SponsorDeltaCard';
import { ApiError, api } from '@/lib/api';

export const metadata = { title: 'Benchmark run' };

export default async function BenchmarkRunPage({
  params,
}: {
  params: Promise<{ run: string }>;
}) {
  const { run: runId } = await params;

  let run;
  try {
    run = await api.getBenchmarkRun(runId);
  } catch (cause) {
    if (cause instanceof ApiError && cause.status === 404) notFound();
    throw cause;
  }

  const comparison = await api.getSameAudioComparison(runId).catch(() => null);

  return (
    <div className="mx-auto w-full max-w-6xl space-y-12 px-5 py-10">
      <header>
        <Link href="/benchmark" className="text-sm text-ink-soft hover:text-ink">
          Benchmark
        </Link>

        <h1 className="mt-3 text-3xl font-medium">Did the speech model preserve the dispute?</h1>

        <p className="mt-3 text-sm text-ink-soft">
          {run.dataset_version} · {run.split} split ·{' '}
          {run.guard_enabled ? 'Critical Speech Guard enabled' : 'Guard disabled (ablation)'}
          {run.git_commit && (
            <>
              {' · '}
              <span className="tabular">{run.git_commit}</span>
            </>
          )}
        </p>
      </header>

      {/* Consequence first, transcription accuracy second. */}
      {comparison && <BenchmarkComparison comparison={comparison} />}

      <SponsorDeltaCard run={run} />

      <section>
        <h2 className="mb-4 text-sm font-medium">Metrics</h2>
        <MetricCards run={run} />
      </section>

      <section className="max-w-prose">
        <h2 className="mb-3 text-sm font-medium">How to read this</h2>
        <div className="space-y-3 text-sm leading-relaxed text-ink-soft">
          <p>
            Word error rate is reported for comparability with the wider speech field, never
            as the headline. A model can score well on words and still lose the one number
            that decides a mediation.
          </p>
          <p>
            Critical fact accuracy is exact: 150,000 heard as 50,000 scores zero. Partial
            credit for sharing digits would misrepresent the risk.
          </p>
          <p>
            Correct mediation state is all or nothing per case. A mediator handed one wrong
            disputed issue among six correct ones still walks into the room carrying a
            conflict that does not exist.
          </p>
        </div>
      </section>
    </div>
  );
}
