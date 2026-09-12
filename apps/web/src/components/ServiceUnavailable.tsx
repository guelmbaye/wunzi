import { ApiError } from '@/lib/api';

/**
 * Shown when a screen could not read from the System of Record.
 *
 * It names the specific cause and the specific fix. "The service is not
 * responding" cannot tell a stopped API apart from a wrong hostname or a
 * missing token, and those need three different actions — a message that
 * covers all three tells you nothing about any of them.
 *
 * It also states plainly that nothing was lost. A mediator who sees an error on
 * a case screen needs to know the recordings are still there.
 */
export function ServiceUnavailable({
  error,
  subject = 'This page',
}: {
  error: unknown;
  subject?: string;
}) {
  const apiError = error instanceof ApiError ? error : null;

  const heading = apiError?.isUnreachable
    ? 'The API is not reachable'
    : apiError?.isUnauthenticated
      ? 'The API refused this request'
      : 'The API could not answer';

  return (
    <div className="card p-6">
      <h2 className="font-medium">{heading}</h2>

      <p className="mt-2 max-w-prose text-sm leading-relaxed text-ink-soft">
        {subject} could not read from the System of Record. Nothing was changed —
        cases, recordings and claims are unaffected.
      </p>

      {apiError && (
        <p className="mt-4 max-w-prose rounded-card bg-paper-sunken px-4 py-3 text-sm leading-relaxed">
          {apiError.remedy}
        </p>
      )}

      {apiError && !apiError.isUnreachable && (
        <p className="tabular mt-3 text-micro text-ink-faint">
          {apiError.status} · {apiError.path}
        </p>
      )}
    </div>
  );
}
