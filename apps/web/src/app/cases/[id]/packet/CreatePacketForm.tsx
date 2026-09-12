'use client';

import { useActionState } from 'react';

import { createPacket } from '@/app/actions';

/**
 * Creating the case is an operational act, not another AI generation. The
 * button says what happens, and the confirmation lists what was actually
 * checked rather than congratulating the user.
 */
export function CreatePacketForm({ caseId }: { caseId: string }) {
  const [state, action, pending] = useActionState(createPacket, { error: null });

  return (
    <form action={action}>
      <input type="hidden" name="case_id" value={caseId} />

      <ul className="mb-5 space-y-1.5 text-sm text-ink-soft">
        <li>Claims preserved with their attribution</li>
        <li>Critical values checked with the speakers</li>
        <li>Issue map attached</li>
        <li>Every sentence traceable to a recording</li>
      </ul>

      {state.error && (
        <p className="mb-4 rounded-card border border-pending/40 bg-pending-soft px-3 py-2 text-sm text-pending-ink">
          {state.error}
        </p>
      )}

      <button type="submit" disabled={pending} className="btn-primary">
        {pending ? 'Creating…' : 'Create mediation case'}
      </button>
    </form>
  );
}
