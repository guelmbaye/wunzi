import { notFound } from 'next/navigation';

import { PartyIntake } from '@/components/PartyIntake';
import { api } from '@/lib/api';

export const metadata = { title: 'Party B' };

export default async function PartyBPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const [record, recordings, claims] = await Promise.all([
    api.getCase(id),
    api.listRecordings(id).catch(() => []),
    api.listClaims(id, 'PARTY_B').catch(() => []),
  ]);

  const party = record.parties.find((item) => item.role === 'PARTY_B');
  if (!party) notFound();

  return (
    <PartyIntake
      caseId={id}
      role="PARTY_B"
      partyId={party.id}
      partyName={party.display_name}
      initialRecording={recordings.find((item) => item.party_id === party.id) ?? null}
      initialClaims={claims}
      // Only in fixture deployments, and named rather than silently applied.
      fixtureKey={
        process.env.NEXT_PUBLIC_DEMO_MODE === 'fixture' ? 'WZ_DEMO_001_B' : null
      }
    />
  );
}
