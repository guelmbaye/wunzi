/**
 * URL builders that are safe to import from client components.
 *
 * Kept apart from `api.ts`, which is marked `server-only` because it carries the
 * bearer token. A client component that reached into that module would drag the
 * token into the browser bundle, so the split is enforced by the module
 * boundary rather than by remembering.
 *
 * These paths point at the Next rewrite (`/api/laravel/*`), not at Laravel
 * directly: the browser never learns the API's address.
 */

export function audioSourceUrl(
  recordingId: string,
  startMs: number,
  endMs: number,
): string {
  const params = new URLSearchParams({
    start_ms: String(startMs),
    end_ms: String(endMs),
  });

  return `/api/laravel/recordings/${recordingId}/stream?${params}`;
}

/** Upload target for one party's account. Recordings belong to a party. */
export function partyRecordingsUrl(partyId: string): string {
  return `/api/laravel/parties/${partyId}/recordings`;
}

export function recordingsUrl(caseId: string): string {
  return `/api/laravel/cases/${caseId}/recordings`;
}

export function claimsUrl(caseId: string, partyRole?: string): string {
  return `/api/laravel/cases/${caseId}/claims${partyRole ? `?party_role=${partyRole}` : ''}`;
}

export function verificationUrl(fieldId: string): string {
  return `/api/laravel/verifications/${fieldId}/resolve`;
}
