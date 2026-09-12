'use client';

import { useRouter } from 'next/navigation';
import { useState, useTransition } from 'react';

import { buildIssueGraph } from '@/app/actions';

export function BuildIssueGraphButton({
  caseId,
  hasIssues,
}: {
  caseId: string;
  hasIssues: boolean;
}) {
  const router = useRouter();
  const [pending, startTransition] = useTransition();
  const [error, setError] = useState<string | null>(null);

  return (
    <div className="text-right">
      <button
        type="button"
        disabled={pending}
        className="btn-secondary"
        onClick={() =>
          startTransition(async () => {
            const result = await buildIssueGraph(caseId);
            setError(result.error);
            if (!result.error) router.refresh();
          })
        }
      >
        {pending ? 'Building…' : hasIssues ? 'Rebuild from current claims' : 'Build issue map'}
      </button>

      {error && <p className="mt-2 max-w-xs text-sm text-pending-ink">{error}</p>}
    </div>
  );
}
