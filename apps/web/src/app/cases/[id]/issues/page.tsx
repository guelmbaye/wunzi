import { IssueMap } from '@/components/IssueMap';
import { api } from '@/lib/api';

import { BuildIssueGraphButton } from './BuildIssueGraphButton';

export const metadata = { title: 'Issue map' };

export default async function IssuesPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const [record, graph] = await Promise.all([
    api.getCase(id),
    api.listIssues(id).catch(() => ({ issues: [], evidence: [] })),
  ]);

  const bothCaptured = record.parties.length === 2;

  return (
    <div className="space-y-8">
      <header className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h2 className="text-xl font-medium">Issue map</h2>
          <p className="mt-2 max-w-prose text-sm leading-relaxed text-ink-soft">
            Where the two accounts align, where they differ, where information is absent,
            and where nothing has been established yet. WUNZI does not resolve any of it.
          </p>
        </div>

        {bothCaptured && <BuildIssueGraphButton caseId={id} hasIssues={graph.issues.length > 0} />}
      </header>

      <IssueMap issues={graph.issues} evidence={graph.evidence} />
    </div>
  );
}
