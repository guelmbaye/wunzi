'use server';

import { revalidatePath } from 'next/cache';
import { redirect } from 'next/navigation';

import { ApiError, api } from '@/lib/api';

export type ActionState = { error: string | null };

/**
 * Writes go through Server Actions so the API token stays on the server.
 *
 * When the System of Record refuses a transition — an unresolved critical field
 * blocking case creation, a recording without consent — that refusal is the
 * answer, not an error to route around. It is surfaced verbatim.
 */
export async function createCase(
  _previous: ActionState,
  formData: FormData,
): Promise<ActionState> {
  const partyA = String(formData.get('party_a_name') ?? '').trim();
  const partyB = String(formData.get('party_b_name') ?? '').trim();

  if (!partyA || !partyB) {
    return { error: 'Both parties need a name or label before the case can start.' };
  }

  let created;
  try {
    created = await api.createCase({
      category: String(formData.get('category') ?? 'rental_deposit'),
      title: String(formData.get('title') ?? '').trim() || undefined,
      party_a_name: partyA,
      party_b_name: partyB,
    });
  } catch (cause) {
    return { error: describe(cause) };
  }

  revalidatePath('/cases');
  redirect(`/cases/${created.id}/party-a`);
}

export async function buildIssueGraph(caseId: string): Promise<ActionState> {
  try {
    await api.buildIssueGraph(caseId);
  } catch (cause) {
    return { error: describe(cause) };
  }

  revalidatePath(`/cases/${caseId}`, 'layout');
  return { error: null };
}

export async function createPacket(
  _previous: ActionState,
  formData: FormData,
): Promise<ActionState> {
  const caseId = String(formData.get('case_id') ?? '');

  try {
    await api.createPacket(caseId);
  } catch (cause) {
    return { error: describe(cause) };
  }

  revalidatePath(`/cases/${caseId}`, 'layout');
  redirect(`/cases/${caseId}/packet`);
}

function describe(cause: unknown): string {
  if (cause instanceof ApiError) {
    if (cause.isUnavailable) {
      return 'The intelligence service is not responding. Nothing was changed — try again shortly.';
    }
    return cause.message;
  }

  return 'Something went wrong and nothing was saved.';
}
