import clsx from 'clsx';

import type { BenchmarkRun } from '@/lib/types';

import { PROVIDER_LABEL } from './BenchmarkComparison';

/**
 * Sponsor Outcome Delta.
 *
 * Two rules govern this card, and both are about not overclaiming:
 *
 *   1. If the run touched a placeholder fixture, the number is a pipeline smoke
 *      test and the card refuses to show it as a result. A benchmark figure that
 *      came from a fixture someone wrote by hand is not a measurement, and
 *      rendering it in large type would be the single most dishonest thing this
 *      product could do.
 *   2. A small delta is reported as a small delta. If the mediation layer
 *      absorbs the difference between speech models, the honest conclusion is
 *      that the evaluation set is too easy — not that the metric should go away.
 */
export function SponsorDeltaCard({ run }: { run: BenchmarkRun }) {
  const publishable = run.results?.publishable !== false;
  const delta = run.sponsor_outcome_delta;

  if (!publishable) {
    return (
      <section className="rounded-card border border-pending/45 bg-pending-soft/50 p-6">
        <h2 className="font-medium">Not a measured result</h2>
        <p className="mt-2 max-w-prose text-sm leading-relaxed">
          {run.results?.publishability_note ??
            'At least one clip in this run was scored from a placeholder fixture rather than a captured provider output.'}
        </p>
        <p className="mt-3 max-w-prose text-sm leading-relaxed text-ink-soft">
          The pipeline ran end to end, which is what this run demonstrates. No number from
          it describes any speech model&rsquo;s real behaviour, so none is shown here.
        </p>
      </section>
    );
  }

  if (delta === null) {
    return (
      <section className="card p-6">
        <h2 className="font-medium">Sponsor Outcome Delta</h2>
        <p className="mt-2 text-sm text-ink-soft">This run has not finished scoring.</p>
      </section>
    );
  }

  const strong = delta >= 5;

  return (
    <section className="card p-6">
      <h2 className="text-sm font-medium text-ink-soft">Sponsor Outcome Delta</h2>

      <p className={clsx('tabular mt-2 text-5xl font-medium', strong ? 'text-ink' : 'text-ink-soft')}>
        {delta > 0 ? '+' : ''}
        {delta.toFixed(1)}
        <span className="ml-2 text-lg font-normal text-ink-faint">points</span>
      </p>

      <p className="mt-4 max-w-prose text-sm leading-relaxed">
        {strong ? (
          <>
            On identical audio, Sahara produced the correct mediation state more often than{' '}
            {PROVIDER_LABEL[run.best_competitor ?? ''] ?? 'the strongest alternative'}. Only
            the speech model changed.
          </>
        ) : (
          <>
            The mediation layer absorbed most of the difference between speech models on
            this evaluation set. The honest response is a harder code-switch split, not a
            softer metric.
          </>
        )}
      </p>

      <p className="mt-4 border-t border-rule pt-3 text-micro text-ink-faint">
        Correct Mediation State Rate for Sahara minus the best of the other models. An
        internal discipline metric the team uses to check whether the sponsor model is
        load-bearing — not an official challenge criterion.
      </p>
    </section>
  );
}

/** The five headline numbers. Everything else lives further down the page. */
export function MetricCards({ run }: { run: BenchmarkRun }) {
  const headline = [
    { metric: 'word_error_rate', label: 'Word error rate', better: 'lower' as const },
    { metric: 'critical_fact_accuracy', label: 'Critical fact accuracy', better: 'higher' as const },
    {
      metric: 'negation_preservation_rate',
      label: 'Negation preserved',
      better: 'higher' as const,
    },
    {
      metric: 'claim_attribution_accuracy',
      label: 'Attribution accuracy',
      better: 'higher' as const,
    },
    {
      metric: 'correct_mediation_state_rate',
      label: 'Correct mediation state',
      better: 'higher' as const,
    },
  ];

  const providers = run.providers;

  return (
    <div className="overflow-x-auto">
      <table className="w-full border-collapse text-sm">
        <caption className="mb-3 text-left text-sm text-ink-soft">
          Confidence intervals are bootstrapped over{' '}
          <span className="tabular">{run.metrics[0]?.sample_count ?? 0}</span> scenarios. The
          set is small, so the intervals are wide — that is the honest picture, not a
          rounding problem.
        </caption>

        <thead>
          <tr className="border-b border-rule">
            <th scope="col" className="px-4 py-2.5 text-left font-medium text-ink-soft">
              Metric
            </th>
            {providers.map((provider) => (
              <th key={provider} scope="col" className="px-4 py-2.5 text-left font-medium">
                {PROVIDER_LABEL[provider] ?? provider}
              </th>
            ))}
          </tr>
        </thead>

        <tbody>
          {headline.map((row) => (
            <tr key={row.metric} className="border-b border-rule/70">
              <th scope="row" className="px-4 py-3 text-left font-normal text-ink-soft">
                {row.label}
                <span className="ml-1.5 text-micro text-ink-faint">
                  {row.better === 'lower' ? '↓ better' : '↑ better'}
                </span>
              </th>

              {providers.map((provider) => {
                const cell = run.metrics.find(
                  (metric) => metric.provider === provider && metric.metric === row.metric,
                );

                if (!cell) {
                  return (
                    <td key={provider} className="px-4 py-3 text-ink-faint">
                      —
                    </td>
                  );
                }

                const isPercent = row.metric === 'correct_mediation_state_rate';

                return (
                  <td key={provider} className="tabular px-4 py-3">
                    {isPercent ? `${cell.value.toFixed(0)}%` : cell.value.toFixed(3)}
                    {cell.ci_low !== null && cell.ci_high !== null && !isPercent && (
                      <span className="ml-1.5 text-micro text-ink-faint">
                        {cell.ci_low.toFixed(2)}–{cell.ci_high.toFixed(2)}
                      </span>
                    )}
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
