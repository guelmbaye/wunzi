import 'server-only';

import type {
  BenchmarkRun,
  CasePacket,
  Claim,
  CriticalField,
  EvidenceReference,
  Issue,
  MediationCase,
  Recording,
  SameAudioComparison,
} from './types';

/**
 * Server-only client for the Laravel System of Record.
 *
 * The token never reaches the browser: every read happens in a Server
 * Component, and every write goes through a Server Action. A mediation case
 * contains two people's accounts of a dispute, so shipping a bearer token to
 * the client to save a hop is not a trade worth making.
 */

/*
 * `api` is the docker compose service name, which only resolves inside the
 * compose network. Running `npm run dev` on a host, it does not — so the
 * default is localhost and compose overrides it explicitly.
 */
const BASE_URL = process.env.LARAVEL_API_URL ?? 'http://localhost:8000';
const TOKEN = process.env.WUNZI_API_TOKEN ?? '';

export class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
    readonly path: string,
    readonly body?: unknown,
  ) {
    super(message);
    this.name = 'ApiError';
  }

  /** The System of Record refused a transition; that refusal is the answer. */
  get isRuleViolation(): boolean {
    return this.status === 422;
  }

  get isUnavailable(): boolean {
    return this.status === 503 || this.status === 502;
  }

  /** status 0 means the request never reached Laravel at all. */
  get isUnreachable(): boolean {
    return this.status === 0;
  }

  get isUnauthenticated(): boolean {
    return this.status === 401 || this.status === 403;
  }

  /**
   * What a developer should actually do about it.
   *
   * A screen that says only "the service is not responding" is useless: it
   * cannot distinguish a stopped API from a wrong hostname from a missing
   * token, and those need three different fixes.
   */
  get remedy(): string {
    if (this.isUnreachable) {
      return `Nothing is listening at ${BASE_URL}. Start the API (\`php artisan serve --port=8000\`) or set LARAVEL_API_URL in apps/web/.env.local — the default only resolves inside docker compose.`;
    }

    if (this.isUnauthenticated) {
      return TOKEN
        ? 'The API rejected the token. Mint a fresh one with `php artisan wunzi:token`.'
        : 'No API token is set. Run `php artisan wunzi:token` and put the result in WUNZI_API_TOKEN in apps/web/.env.local.';
    }

    if (this.isUnavailable) {
      return 'The API is up but a service it depends on is not. Check the intelligence service and the queue worker.';
    }

    return this.message;
  }
}

type FetchOptions = {
  method?: 'GET' | 'POST' | 'PATCH' | 'DELETE';
  body?: unknown;
  /** Live case state is never cached; benchmark results are immutable. */
  revalidate?: number | false;
  tags?: string[];
};

async function call<T>(path: string, options: FetchOptions = {}): Promise<T> {
  const { method = 'GET', body, revalidate = 0, tags } = options;

  let response: Response;

  try {
    response = await fetch(`${BASE_URL}/api${path}`, {
      method,
      headers: {
        Accept: 'application/json',
        ...(body ? { 'Content-Type': 'application/json' } : {}),
        ...(TOKEN ? { Authorization: `Bearer ${TOKEN}` } : {}),
      },
      body: body ? JSON.stringify(body) : undefined,
      next: revalidate === false ? undefined : { revalidate, tags },
      cache: revalidate === 0 ? 'no-store' : undefined,
    });
  } catch (cause) {
    // fetch throws rather than returning a response when the host does not
    // resolve or refuses the connection. Without this, the failure arrives as a
    // bare TypeError and every screen reports the same unhelpful thing.
    throw new ApiError(
      `Could not reach the API at ${BASE_URL}: ${cause instanceof Error ? cause.message : 'connection failed'}`,
      0,
      path,
    );
  }

  if (!response.ok) {
    let payload: unknown;
    try {
      payload = await response.json();
    } catch {
      payload = await response.text();
    }

    throw new ApiError(
      messageFor(payload, response.status, path),
      response.status,
      path,
      payload,
    );
  }

  if (response.status === 204) return undefined as T;

  const json = (await response.json()) as { data?: T } & T;
  return (json?.data ?? json) as T;
}

function messageFor(payload: unknown, status: number, path: string): string {
  if (payload && typeof payload === 'object' && 'message' in payload) {
    return String((payload as { message: unknown }).message);
  }
  return `Request to ${path} failed with ${status}.`;
}

// ── cases ──────────────────────────────────────────────────────────────────
export const api = {
  listCases: () => call<MediationCase[]>('/cases'),

  createCase: (input: {
    category: string;
    title?: string;
    party_a_name: string;
    party_b_name: string;
  }) => call<MediationCase>('/cases', { method: 'POST', body: input }),

  getCase: (id: string) => call<MediationCase>(`/cases/${id}`),

  getOverview: (id: string) =>
    call<{
      case: MediationCase;
      recordings: Recording[];
      claims: Claim[];
      pending_critical_fields: number;
    }>(`/cases/${id}/overview`),

  // ── capture ──────────────────────────────────────────────────────────────
  listRecordings: (caseId: string) => call<Recording[]>(`/cases/${caseId}/recordings`),

  listClaims: (caseId: string, partyRole?: string) =>
    call<Claim[]>(`/cases/${caseId}/claims${partyRole ? `?party_role=${partyRole}` : ''}`),

  // ── verification ─────────────────────────────────────────────────────────
  listCriticalFields: (caseId: string) =>
    call<CriticalField[]>(`/cases/${caseId}/verifications`),

  resolveCriticalField: (
    fieldId: string,
    input: { resolution: 'CONFIRMED' | 'CORRECTED' | 'UNRESOLVED'; corrected_value?: string },
  ) =>
    call<CriticalField>(`/verifications/${fieldId}/resolve`, {
      method: 'POST',
      body: input,
    }),

  // ── issue graph ──────────────────────────────────────────────────────────
  listIssues: (caseId: string) =>
    call<{ issues: Issue[]; evidence: EvidenceReference[] }>(`/cases/${caseId}/issues`),

  buildIssueGraph: (caseId: string) =>
    call<{ queued: boolean }>(`/cases/${caseId}/build-issues`, { method: 'POST' }),

  // ── packet ───────────────────────────────────────────────────────────────
  getPacket: (caseId: string) => call<CasePacket | null>(`/cases/${caseId}/packet`),

  createPacket: (caseId: string) =>
    call<CasePacket>(`/cases/${caseId}/create-packet`, { method: 'POST' }),

  // ── benchmark ────────────────────────────────────────────────────────────
  listBenchmarkRuns: () => call<BenchmarkRun[]>('/benchmark-runs', { revalidate: 30 }),

  getBenchmarkRun: (runId: string) =>
    call<BenchmarkRun>(`/benchmark-runs/${runId}`, { revalidate: 30 }),

  getSameAudioComparison: (runId: string, clipId?: string) =>
    call<SameAudioComparison>(
      `/benchmark-runs/${runId}/same-audio${clipId ? `?clip_id=${clipId}` : ''}`,
      { revalidate: 30 },
    ),

  /** Boundaries the API declares about itself, rendered on /responsible-ai. */
  getResponsibleAi: () =>
    call<{
      boundaries: Record<string, boolean>;
      approved_framings: string[];
      blocked_language: string[];
    }>('/responsible-ai', { revalidate: 3600 }),
};
