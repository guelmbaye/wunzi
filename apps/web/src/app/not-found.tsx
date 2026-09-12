import Link from 'next/link';

export default function NotFound() {
  return (
    <div className="mx-auto w-full max-w-2xl px-5 py-20">
      <h1 className="text-2xl font-medium">That page does not exist</h1>
      <p className="mt-2 text-sm text-ink-soft">
        The link may be out of date, or the case may have been removed.
      </p>
      <Link href="/cases" className="btn-primary mt-6">
        Go to cases
      </Link>
    </div>
  );
}
