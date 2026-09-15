import clsx from 'clsx';

import { LANGUAGE_LABEL, PARTY, formatDuration } from '@/lib/states';
import type { PartyRole, TranscriptRun } from '@/lib/types';

/**
 * The transcript, with language spans marked where — and only where — the
 * provider actually reported them.
 *
 * Providers differ in what they expose. Intron's file-upload endpoint returns a
 * flat transcript with no segments and no confidence; Whisper reports one
 * language per request. Neither gives per-segment boundaries, so none are shown
 * for them — a language tag WUNZI invented would be a fabricated audit trail.
 *
 * Where a provider does report spans, they are marked. Where it does not, the
 * absence is stated instead of filled in.
 */
export function TranscriptViewer({
  run,
  role,
}: {
  run: TranscriptRun;
  role: PartyRole;
}) {
  const party = PARTY[role];
  const switches = countSwitches(run);
  const hasLanguageSpans = run.segments.some((segment) => segment.language_code);

  return (
    <section className="card overflow-hidden">
      <header className="flex flex-wrap items-center justify-between gap-3 border-b border-rule px-5 py-3">
        <h3 className="text-sm font-medium">Transcript</h3>

        <dl className="flex flex-wrap items-center gap-x-5 gap-y-1 text-micro text-ink-faint">
          <Meta term="Model" value={run.model ?? run.provider} />
          {run.latency_ms !== null && <Meta term="Latency" value={`${run.latency_ms} ms`} />}
          {hasLanguageSpans && (
            <Meta term="Language switches" value={String(switches)} />
          )}
          {run.source_mode === 'fixture' && <Meta term="Source" value="Cached provider output" />}
        </dl>
      </header>

      <div className="px-5 py-4">
        {run.segments.length === 0 ? (
          <p className="text-sm leading-relaxed text-ink">{run.normalized_transcript}</p>
        ) : (
          <ol className="space-y-3">
            {run.segments.map((segment) => (
              <li key={segment.id} className="flex gap-4">
                <span className="tabular w-12 shrink-0 pt-0.5 text-micro text-ink-faint">
                  {formatDuration(segment.start_ms)}
                </span>

                <p className="flex-1 text-sm leading-relaxed">
                  <span
                    className={clsx(
                      segment.language_code && 'border-b-2 pb-px',
                      segment.language_code && party.border,
                    )}
                  >
                    {segment.text}
                  </span>

                  {segment.language_code && (
                    <span className="ml-2 align-middle text-micro text-ink-faint">
                      {LANGUAGE_LABEL[segment.language_code] ?? segment.language_code}
                    </span>
                  )}
                </p>
              </li>
            ))}
          </ol>
        )}

        {!hasLanguageSpans && run.segments.length > 0 && (
          <p className="mt-4 border-t border-rule pt-3 text-micro text-ink-faint">
            This provider does not report language per segment, so switches are not marked.
            WUNZI does not guess them.
          </p>
        )}

        {run.fixture_origin && (
          <p className="mt-4 border-t border-rule pt-3 text-micro text-ink-faint">
            Replayed from a stored provider run · {run.fixture_origin}
          </p>
        )}
      </div>
    </section>
  );
}

function Meta({ term, value }: { term: string; value: string }) {
  return (
    <div className="flex items-center gap-1.5">
      <dt className="text-ink-faint">{term}</dt>
      <dd className="tabular text-ink-soft">{value}</dd>
    </div>
  );
}

function countSwitches(run: TranscriptRun): number {
  const languages = run.segments
    .map((segment) => segment.language_code)
    .filter((language): language is string => Boolean(language));

  return languages.reduce(
    (total, language, index) =>
      index > 0 && language !== languages[index - 1] ? total + 1 : total,
    0,
  );
}
