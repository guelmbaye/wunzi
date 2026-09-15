import { notFound } from 'next/navigation';

import { PartyIntake } from '@/components/PartyIntake';
import { api } from '@/lib/api';

export const metadata = { title: 'Party A' };

export default async function PartyAPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const [record, recordings, claims] = await Promise.all([
    api.getCase(id),
    api.listRecordings(id).catch(() => []),
    api.listClaims(id, 'PARTY_A').catch(() => []),
  ]);

  const party = record.parties.find((item) => item.role === 'PARTY_A');
  if (!party) notFound();

  return (
    <PartyIntake
      caseId={id}
      role="PARTY_A"
      partyId={party.id}
      partyName={party.display_name}
      initialRecording={recordings.find((item) => item.party_id === party.id) ?? null}
      initialClaims={claims}
      // Only in fixture deployments, and named rather than silently applied.
      fixtureKey={
        process.env.NEXT_PUBLIC_DEMO_MODE === 'fixture' ? 'WZ_DEMO_001_A' : null
      }
    />
  );
}
