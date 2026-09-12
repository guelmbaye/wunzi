'use client';

export default function Error({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <div className="mx-auto w-full max-w-2xl px-5 py-20">
      <h1 className="text-2xl font-medium">This page could not load</h1>
      <p className="mt-2 max-w-prose text-sm leading-relaxed text-ink-soft">
        Nothing was changed. The case and its recordings are unaffected — this screen failed
        to read them.
      </p>

      {/* Server Components strip error details in production, so the message is
          only shown in development, where it is what a developer needs. */}
      {process.env.NODE_ENV === 'development' && (
        <p className="mt-4 max-w-prose rounded-card bg-paper-sunken px-4 py-3 text-sm leading-relaxed">
          {error.message}
        </p>
      )}
      {error.digest && (
        <p className="tabular mt-3 text-micro text-ink-faint">Reference {error.digest}</p>
      )}
      <button type="button" onClick={reset} className="btn-primary mt-6">
        Try again
      </button>
    </div>
  );
}
