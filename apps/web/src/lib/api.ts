import 'server-only';

import type {
  BenchmarkRun,
  CaseOverview,
  CasePacket,
  Claim,
  CriticalField,
  EvidenceReference,
  Issue,
  MediationCase,
  Recording,
  SameAudioComparison,
} from './types';
import { count, list, record, toCase, toClaim, toCriticalField, toEvidence, toIssue, toRecording } from './mappers';

/**
 * Server-only client for the Laravel System of Record.
 *
 * The token never reaches the browser: every read happens in a Server
 * Component, every write in a Server Action.
 *
 * Every response is mapped EXPLICITLY below. This file used to unwrap with
 * `json?.data ?? json`, which looked tidy and was wrong twice over: it silently
 * discarded sibling keys — Laravel returns `{data, evidence, meta}` for the
 * issue graph, so `evidence` vanished — and it hid every field-name difference
 * until a Server Component crashed on `undefined` and white-screened the route.
 * Laravel's resources are the contract; the mappers below are the only place
 * allowed to know both vocabularies.
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

  get remedy(): string {
    if (this.isUnreachable) {
      return `Nothing is listening at ${BASE_URL}. Start the API, or set LARAVEL_API_URL — the compose default only resolves inside the compose network.`;
    }

    if (this.isUnauthenticated) {
      return TOKEN
        ? 'The API rejected the token. Mint a fresh one with `php artisan wunzi:token --revoke`.'
        : 'No API token is set. Run `php artisan wunzi:token` and put the result in WUNZI_API_TOKEN.';
    }

    if (this.isUnavailable) {
      return 'The API is up but a service it depends on is not. Check the intelligence service and the queue worker.';
    }

    return this.message;
  }
}

type Envelope = Record<string, unknown>;

type FetchOptions = {
  method?: 'GET' | 'POST' | 'PATCH' | 'DELETE';
  body?: unknown;
  revalidate?: number | false;
  tags?: string[];
};

/** Returns the raw envelope. Unwrapping is each mapper's job, not this one's. */
async function call(path: string, options: FetchOptions = {}): Promise<Envelope> {
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
    throw new ApiError(messageFor(payload, response.status, path), response.status, path, payload);
  }

  if (response.status === 204) return {};

  return (await response.json()) as Envelope;
}

function messageFor(payload: unknown, status: number, path: string): string {
  if (payload && typeof payload === 'object' && 'message' in payload) {
    return String((payload as { message: unknown }).message);
  }
  return `Request to ${path} failed with ${status}.`;
}

// ── endpoints ──────────────────────────────────────────────────────────────

export const api = {
  async listCases(): Promise<MediationCase[]> {
    const envelope = await call('/cases');
    return list(envelope.data).map((raw) => toCase(raw));
  },

  async createCase(input: {
    category: string;
    title?: string;
    party_a_name: string;
    party_b_name: string;
  }): Promise<MediationCase> {
    const envelope = await call('/cases', { method: 'POST', body: input });
    return toCase(record(envelope.data));
  },

  async getCase(id: string): Promise<MediationCase> {
    const envelope = await call(`/cases/${id}`);
    return toCase(record(envelope.data), count(record(envelope.meta).pending_verifications));
  },

  /** `{case, progress, summary}` — Laravel's own shape, kept rather than reinvented. */
  async getOverview(id: string): Promise<CaseOverview> {
    const envelope = await call(`/cases/${id}/overview`);
    const summary = record(envelope.summary);
    const progress = record(envelope.progress);

    return {
      case: toCase(record(envelope.case), count(summary.fields_needing_verification)),
      progress: {
        party_a: Boolean(progress.party_a),
        party_b: Boolean(progress.party_b),
        verification: Boolean(progress.verification),
        issue_map: Boolean(progress.issue_map),
        packet: Boolean(progress.packet),
      },
      summary: {
        agreed: count(summary.agreed),
        disputed: count(summary.disputed),
        missing: count(summary.missing),
        unverified: count(summary.unverified),
        fields_needing_verification: count(summary.fields_needing_verification),
      },
    };
  },

  async listRecordings(caseId: string): Promise<Recording[]> {
    const envelope = await call(`/cases/${caseId}/recordings`);
    return list(envelope.data).map(toRecording);
  },

  async listClaims(caseId: string, partyRole?: string): Promise<Claim[]> {
    const envelope = await call(
      `/cases/${caseId}/claims${partyRole ? `?party_role=${partyRole}` : ''}`,
    );
    return list(envelope.data).map(toClaim);
  },

  async listCriticalFields(caseId: string): Promise<CriticalField[]> {
    const envelope = await call(`/cases/${caseId}/verifications`);
    return list(envelope.data).map(toCriticalField);
  },

  /**
   * Laravel groups issues by status and puts evidence beside `data`, not inside
   * it. Flattened here, ordered by the four states.
   */
  async listIssues(caseId: string): Promise<{ issues: Issue[]; evidence: EvidenceReference[] }> {
    const envelope = await call(`/cases/${caseId}/issues`);
    const grouped = record(envelope.data);

    const issues = (['DISPUTED', 'UNVERIFIED', 'MISSING', 'AGREED'] as const).flatMap((status) =>
      list(grouped[status]).map(toIssue),
    );

    return { issues, evidence: list(envelope.evidence).map(toEvidence) };
  },

  async buildIssueGraph(caseId: string): Promise<void> {
    await call(`/cases/${caseId}/build-issues`, { method: 'POST' });
  },

  async getPacket(caseId: string): Promise<CasePacket | null> {
    const envelope = await call(`/cases/${caseId}/packet`);
    const data = record(envelope.data);
    if (!data.id) return null;

    return {
      id: String(data.id),
      version: count(data.version),
      generated_at: String(data.generated_at ?? ''),
      payload: record(data.payload) as CasePacket['payload'],
    };
  },

  async createPacket(caseId: string): Promise<void> {
    await call(`/cases/${caseId}/create-packet`, { method: 'POST' });
  },

  // ── benchmark ────────────────────────────────────────────────────────────
  async listBenchmarkRuns(): Promise<BenchmarkRun[]> {
    const envelope = await call('/benchmark-runs');
    return list(envelope.data) as unknown as BenchmarkRun[];
  },

  async getBenchmarkRun(runId: string): Promise<BenchmarkRun> {
    const envelope = await call(`/benchmark-runs/${runId}`);
    return record(envelope.data) as unknown as BenchmarkRun;
  },

  async getSameAudioComparison(runId: string, clipId?: string): Promise<SameAudioComparison> {
    const envelope = await call(
      `/benchmark-runs/${runId}/same-audio${clipId ? `?clip_id=${clipId}` : ''}`,
    );
    const data = record(envelope.data);
    return (Object.keys(data).length ? data : envelope) as unknown as SameAudioComparison;
  },
};
