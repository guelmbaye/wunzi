import Link from 'next/link';
import { notFound } from 'next/navigation';

import { CaseStatusStepper } from '@/components/CaseStatusStepper';
import { ApiError, api } from '@/lib/api';
import { CASE_STATUS_LABEL, sentenceCase } from '@/lib/states';

export default async function CaseLayout({
  children,
  params,
}: {
  children: React.ReactNode;
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;

  let record;
  try {
    record = await api.getCase(id);
  } catch (cause) {
    if (cause instanceof ApiError && cause.status === 404) notFound();
    throw cause;
  }

  const pending = record.counts?.pending_critical_fields ?? 0;

  return (
    <>
      <div className="border-b border-rule bg-paper-raised">
        <div className="mx-auto w-full max-w-6xl px-5 pb-4 pt-6">
          <Link href="/cases" className="text-sm text-ink-soft hover:text-ink">
            Cases
          </Link>

          <div className="mt-2 flex flex-wrap items-baseline justify-between gap-x-6 gap-y-2">
            <h1 className="text-2xl font-medium">
              {record.title ?? sentenceCase(record.category)}
            </h1>

            <p className="text-sm text-ink-soft">
              <span className="tabular">{record.public_reference}</span>
              {' · '}
              {CASE_STATUS_LABEL[record.status]}
            </p>
          </div>

          <p className="mt-1 flex flex-wrap items-center gap-x-4 gap-y-1 text-sm">
            {record.parties.map((party) => (
              <span key={party.id} className="inline-flex items-center gap-2">
                <span
                  aria-hidden
                  className={`h-3 w-1 rounded-full ${
                    party.role === 'PARTY_A' ? 'bg-partyA' : 'bg-partyB'
                  }`}
                />
                <span className={party.role === 'PARTY_A' ? 'text-partyA' : 'text-partyB'}>
                  {party.display_name}
                </span>
              </span>
            ))}
          </p>
        </div>
      </div>

      <CaseStatusStepper caseId={id} status={record.status} pendingFields={pending} />

      <div className="mx-auto w-full max-w-6xl px-5 py-8">{children}</div>
    </>
  );
}
