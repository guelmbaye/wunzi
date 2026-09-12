import Link from 'next/link';

import { VerificationCard } from '@/components/VerificationCard';
import { api } from '@/lib/api';

export const metadata = { title: 'Verify' };

/**
 * Only the speaker verifies their own words. This screen exists because the
 * alternative — a wrong amount entering a case with no flag on it — is the
 * failure with the highest cost in mediation.
 */
export default async function VerifyPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const fields = await api.listCriticalFields(id).catch(() => []);

  const pending = fields.filter((field) => field.status === 'NEEDS_CONFIRMATION');
  const settled = fields.filter((field) => field.status !== 'NEEDS_CONFIRMATION');

  return (
    <div className="space-y-8">
      <header>
        <h2 className="text-xl font-medium">Confirm what was heard</h2>
        <p className="mt-2 max-w-prose text-sm leading-relaxed text-ink-soft">
          These are values WUNZI could not hear reliably enough to put in a case unmarked.
          Each question goes to the person who said it — a mediator can read a case, but
          cannot rewrite a party&rsquo;s words.
        </p>
      </header>

      {pending.length === 0 && settled.length === 0 && (
        <p className="card p-6 text-sm text-ink-soft">
          Nothing needs confirming. Every critical value in both accounts was heard clearly.
        </p>
      )}

      {pending.length > 0 && (
        <section className="space-y-3">
          {pending.map((field) => (
            <VerificationCard key={field.id} field={field} />
          ))}
        </section>
      )}

      {pending.length === 0 && settled.length > 0 && (
        <div className="flex flex-wrap items-center gap-4 rounded-card border border-rule bg-paper-raised px-5 py-4">
          <p className="flex-1 text-sm">Everything critical has been settled.</p>
          <Link href={`/cases/${id}/issues`} className="btn-primary">
            Go to the issue map
          </Link>
        </div>
      )}

      {settled.length > 0 && (
        <section>
          <h3 className="mb-3 text-sm font-medium">Already settled</h3>
          <div className="space-y-3">
            {settled.map((field) => (
              <VerificationCard key={field.id} field={field} />
            ))}
          </div>
        </section>
      )}
    </div>
  );
}
