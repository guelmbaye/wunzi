import Link from 'next/link';

import { StateBadge } from '@/components/StateBadge';
import { api } from '@/lib/api';
import { formatIsoDate, formatValue } from '@/lib/states';
import type { PacketIssueEntry } from '@/lib/types';

import { CreatePacketForm } from './CreatePacketForm';

export const metadata = { title: 'Case packet' };

/**
 * The packet is set in a serif at document width, because it is a document —
 * something a mediator prints, carries into a room and reads aloud from. The
 * rest of the product is a workspace; this is the artefact it produces.
 */
export default async function PacketPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const [record, packet] = await Promise.all([
    api.getCase(id),
    api.getPacket(id).catch(() => null),
  ]);

  if (!packet) {
    const blocked = (record.counts?.pending_critical_fields ?? 0) > 0;

    return (
      <div className="max-w-prose space-y-6">
        <h2 className="text-xl font-medium">Create the mediation case</h2>

        {blocked ? (
          <div className="card border-pending/35 p-5">
            <p className="text-sm leading-relaxed">
              {record.counts?.pending_critical_fields} critical{' '}
              {record.counts?.pending_critical_fields === 1 ? 'value is' : 'values are'} still
              unconfirmed. A case cannot be finalised while a consequential value rests on
              something WUNZI was not sure it heard.
            </p>
            <Link href={`/cases/${id}/verify`} className="btn-primary mt-4">
              Go to verification
            </Link>
          </div>
        ) : (
          <>
            <p className="text-sm leading-relaxed text-ink-soft">
              This assembles both accounts, the issue map and the evidence gaps into one
              document for a human mediator. Every sentence in it traces back to something a
              party actually said.
            </p>
            <CreatePacketForm caseId={id} />
          </>
        )}
      </div>
    );
  }

  const { payload } = packet;

  return (
    <article className="font-document">
      <header className="border-b-2 border-ink pb-5">
        <div className="flex flex-wrap items-baseline justify-between gap-4">
          <h2 className="text-3xl">Mediation case {payload.case_reference}</h2>
          <p className="font-sans text-sm text-ink-soft">
            Version <span className="tabular">{packet.version}</span> ·{' '}
            {formatIsoDate(packet.generated_at)}
          </p>
        </div>

        <p className="mt-3 font-sans text-sm">
          <span className="rounded-full bg-ink px-2.5 py-1 text-xs font-medium text-paper">
            {payload.status_label}
          </span>
        </p>
      </header>

      <div className="mt-8 max-w-prose space-y-10 leading-relaxed">
        <Section title="Parties">
          <ul className="space-y-1">
            {payload.parties.map((party) => (
              <li key={party.role}>
                <span
                  className={
                    party.role === 'PARTY_A'
                      ? 'font-sans text-sm text-partyA'
                      : 'font-sans text-sm text-partyB'
                  }
                >
                  {party.role === 'PARTY_A' ? 'Party A' : 'Party B'}
                </span>{' '}
                — {party.display_name}
              </li>
            ))}
          </ul>
        </Section>

        <IssueSection title="Agreed" entries={payload.agreed} />
        <IssueSection title="Disputed" entries={payload.disputed} />
        <IssueSection title="Missing information" entries={payload.missing_information} />
        <IssueSection title="Unverified information" entries={payload.unverified_information} />

        <Section title="Requested outcomes">
          <ul className="space-y-2">
            {Object.entries(payload.requested_outcomes).map(([role, statement]) =>
              statement ? (
                <li key={role}>{statement}</li>
              ) : (
                <li key={role} className="text-ink-faint">
                  {role === 'PARTY_A' ? 'Party A' : 'Party B'} did not state a requested
                  outcome.
                </li>
              ),
            )}
          </ul>
        </Section>

        {payload.evidence_gaps.length > 0 && (
          <Section title="Evidence">
            <ul className="space-y-1">
              {payload.evidence_gaps.map((gap) => (
                <li key={gap.evidence_id}>{gap.statement}</li>
              ))}
            </ul>
          </Section>
        )}

        <Section title="Both accounts, in full">
          <div className="grid gap-8 sm:grid-cols-2">
            <ClaimColumn
              label="Party A states"
              accent="text-partyA"
              entries={payload.party_a_claims}
            />
            <ClaimColumn
              label="Party B states"
              accent="text-partyB"
              entries={payload.party_b_claims}
            />
          </div>
        </Section>

        <p className="border-t border-rule pt-6 font-sans text-sm text-ink-soft">
          {payload.human_boundary}
        </p>
      </div>
    </article>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section>
      <h3 className="mb-3 font-sans text-sm font-medium">{title}</h3>
      {children}
    </section>
  );
}

function IssueSection({ title, entries }: { title: string; entries: PacketIssueEntry[] }) {
  if (entries.length === 0) {
    return (
      <Section title={title}>
        <p className="text-ink-faint">Nothing recorded under this heading.</p>
      </Section>
    );
  }

  return (
    <Section title={title}>
      <ul className="space-y-4">
        {entries.map((entry) => {
          const valueA = formatValue(entry.party_a_value);
          const valueB = formatValue(entry.party_b_value);

          return (
            <li key={entry.issue_id} className="border-l-2 border-rule pl-4">
              <div className="flex flex-wrap items-baseline gap-3">
                <span className="font-medium">{entry.label}</span>
                <StateBadge status={entry.status} size="sm" />
              </div>

              <p className="mt-1">{entry.statement}</p>

              {(valueA || valueB) && (
                <p className="tabular mt-1.5 font-sans text-sm">
                  {valueA && <span className="text-partyA">Party A: {valueA}</span>}
                  {valueA && valueB && <span className="text-ink-faint"> · </span>}
                  {valueB && <span className="text-partyB">Party B: {valueB}</span>}
                </p>
              )}

              {entry.reason && (
                <p className="mt-1 font-sans text-micro text-ink-faint">{entry.reason}</p>
              )}
            </li>
          );
        })}
      </ul>
    </Section>
  );
}

function ClaimColumn({
  label,
  accent,
  entries,
}: {
  label: string;
  accent: string;
  entries: { claim_id: string; statement: string; verification: string }[];
}) {
  return (
    <div>
      <h4 className={`mb-2 font-sans text-sm font-medium ${accent}`}>{label}</h4>
      <ul className="space-y-3">
        {entries.map((entry) => (
          <li key={entry.claim_id}>
            <p>{entry.statement}</p>
            <p className="mt-0.5 font-sans text-micro text-ink-faint">{entry.verification}</p>
          </li>
        ))}
      </ul>
    </div>
  );
}
