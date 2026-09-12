import clsx from 'clsx';

import type { SameAudioComparison } from '@/lib/types';

const PROVIDER_LABEL: Record<string, string> = {
  sahara: 'Sahara',
  whisper: 'Whisper',
  model_b: 'Model B',
  model_c: 'Model C',
};

/**
 * One row per critical element, one column per speech model, over identical
 * audio.
 *
 * This is the screen that makes the argument, so it starts with consequence and
 * ends with the transcription detail — never the other way round. The last row
 * is the issue state, because that is what a mediator would actually have
 * walked into the room believing.
 *
 * Sahara gets no visual privilege beyond a label. If the sponsor column wins,
 * it has to win on the values in the cells.
 */
export function BenchmarkComparison({
  comparison,
}: {
  comparison: SameAudioComparison;
}) {
  return (
    <figure className="card overflow-hidden">
      <figcaption className="flex flex-wrap items-baseline justify-between gap-3 border-b border-rule px-5 py-3">
        <h3 className="text-sm font-medium">Same audio, four speech models</h3>
        <span className="tabular text-micro text-ink-faint">{comparison.clip_id}</span>
      </figcaption>

      <div className="overflow-x-auto">
        <table className="w-full border-collapse text-sm">
          <thead>
            <tr className="border-b border-rule">
              <th scope="col" className="px-5 py-2.5 text-left font-medium text-ink-soft">
                Critical element
              </th>
              {comparison.providers.map((provider) => (
                <th
                  key={provider}
                  scope="col"
                  className="px-4 py-2.5 text-left font-medium"
                >
                  {PROVIDER_LABEL[provider] ?? provider}
                </th>
              ))}
            </tr>
          </thead>

          <tbody>
            {comparison.rows.map((row, index) => {
              const isState = row.element === 'issue_state';

              return (
                <tr
                  key={row.element}
                  className={clsx(
                    index > 0 && 'border-t border-rule/70',
                    isState && 'border-t-2 border-ink bg-paper-sunken/50',
                  )}
                >
                  <th
                    scope="row"
                    className={clsx(
                      'px-5 py-3 text-left font-normal',
                      isState ? 'font-medium text-ink' : 'text-ink-soft',
                    )}
                  >
                    {row.label}
                  </th>

                  {comparison.providers.map((provider) => {
                    const cell = row.by_provider[provider];

                    return (
                      <td key={provider} className="px-4 py-3">
                        <span
                          className={clsx(
                            'tabular',
                            cell?.correct === false && 'text-pending-ink',
                            isState && 'font-medium',
                          )}
                        >
                          {cell?.value ?? '—'}
                        </span>

                        {cell?.correct === false && (
                          <span className="ml-1.5 text-micro text-pending-ink" aria-label="incorrect">
                            ✕
                          </span>
                        )}
                        {cell?.correct === true && (
                          <span className="ml-1.5 text-micro text-ink-faint" aria-label="correct">
                            ✓
                          </span>
                        )}
                      </td>
                    );
                  })}
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      <p className="border-t border-rule px-5 py-3 text-micro text-ink-faint">
        {comparison.integrity_note}
      </p>
    </figure>
  );
}

export { PROVIDER_LABEL };
