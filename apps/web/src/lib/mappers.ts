import type {
  Claim,
  CriticalField,
  EvidenceReference,
  Issue,
  MediationCase,
  PartyRole,
  Recording,
} from './types';
import { ISSUE_LABEL } from './states';

/**
 * Laravel → TypeScript mappers. Pure functions, no fetch, no token.
 *
 * They live apart from `api.ts` because `api.ts` is `server-only` and the party
 * intake screen polls the API from the browser while transcription runs. If the
 * client parsed the raw envelope itself, the two sides would drift the moment a
 * Laravel resource changed — which is exactly the failure this file exists to
 * end.
 */

// ── helpers ────────────────────────────────────────────────────────────────
// Laravel resources use `whenLoaded`, so any relation can be absent entirely.

export function list(value: unknown): Record<string, unknown>[] {
  return Array.isArray(value) ? (value as Record<string, unknown>[]) : [];
}

export function record(value: unknown): Record<string, unknown> {
  return value && typeof value === 'object' ? (value as Record<string, unknown>) : {};
}

export function count(value: unknown): number {
  return typeof value === 'number' ? value : 0;
}

// ── mappers ────────────────────────────────────────────────────────────────

export function toCase(raw: Record<string, unknown>, pending = 0): MediationCase {
  return {
    id: String(raw.id ?? ''),
    public_reference: String(raw.public_reference ?? ''),
    category: String(raw.category ?? 'rental_deposit'),
    title: (raw.title as string | null) ?? null,
    status: (raw.status as MediationCase['status']) ?? 'DRAFT',
    parties: list(raw.parties).map((party) => ({
      id: String(party.id ?? ''),
      role: (party.role as PartyRole) ?? 'PARTY_A',
      display_name: String(party.display_name ?? ''),
      consent_status: String(party.consent_status ?? ''),
    })),
    counts: {
      claims: count(raw.claims_count),
      issues: count(raw.issues_count),
      // Laravel puts this in `meta`: it is a query, not a column.
      pending_critical_fields: pending,
    },
    created_at: String(raw.created_at ?? ''),
    updated_at: String(raw.updated_at ?? raw.created_at ?? ''),
  };
}

export function toIssue(raw: Record<string, unknown>): Issue {
  const type = String(raw.canonical_type ?? '');

  return {
    id: String(raw.id ?? ''),
    canonical_type: type,
    // Laravel sends no display label; that belongs to the interface.
    label: ISSUE_LABEL[type] ?? type.replace(/_/g, ' '),
    status: (raw.status as Issue['status']) ?? 'UNVERIFIED',
    criticality: (raw.criticality as Issue['criticality']) ?? 'MEDIUM',
    summary: (raw.summary as string | null) ?? null,
    // Laravel names this `reason`; the column is `classification_reason`.
    classification_reason: (raw.reason as string | null) ?? null,
    party_a_value: (raw.party_a_value as Issue['party_a_value']) ?? null,
    party_b_value: (raw.party_b_value as Issue['party_b_value']) ?? null,
  };
}

export function toEvidence(raw: Record<string, unknown>): EvidenceReference {
  return {
    id: String(raw.id ?? ''),
    type: String(raw.type ?? ''),
    availability: (raw.availability as EvidenceReference['availability']) ?? 'MISSING',
    label: (raw.label as string | null) ?? null,
    description: (raw.description as string | null) ?? null,
  };
}

export function toClaim(raw: Record<string, unknown>): Claim {
  return {
    id: String(raw.id ?? ''),
    party_role: (raw.party_role as PartyRole) ?? 'PARTY_A',
    type: String(raw.type ?? ''),
    subject: (raw.subject as string | null) ?? null,
    predicate: String(raw.predicate ?? ''),
    canonical_value: (raw.canonical_value as Claim['canonical_value']) ?? null,
    polarity: (raw.polarity as Claim['polarity']) ?? 'POSITIVE',
    criticality: (raw.criticality as Claim['criticality']) ?? 'MEDIUM',
    verification_status: (raw.verification_status as Claim['verification_status']) ?? 'UNVERIFIED',
    reported_speech: Boolean(raw.reported_speech),
    is_superseded: Boolean(raw.is_superseded),
    // Built server-side so both services apply the same attribution rule.
    // The UI never assembles a neutral sentence itself.
    statement: String(raw.neutral_statement ?? ''),
    has_audio_source: Boolean(raw.has_audio_source),
  };
}

export function toCriticalField(raw: Record<string, unknown>): CriticalField {
  const claim = record(raw.claim);

  return {
    id: String(raw.id ?? ''),
    claim_id: String(raw.claim_id ?? ''),
    // Laravel nests the party inside the claim; the card needs it at the top.
    party_role: (claim.party_role as PartyRole) ?? 'PARTY_A',
    field_type: String(raw.field_type ?? ''),
    detected_value: (raw.detected_value as string | null) ?? null,
    normalized_value: (raw.normalized_value as string | null) ?? null,
    status: (raw.status as CriticalField['status']) ?? 'NEEDS_CONFIRMATION',
    risk_level: String(raw.risk_level ?? ''),
    guard_reason: Array.isArray(raw.guard_reason) ? (raw.guard_reason as string[]) : [],
    prompt_text: (raw.prompt_text as string | null) ?? null,
    claim_statement: String(claim.neutral_statement ?? ''),
    has_audio_source: Boolean(claim.has_audio_source),
  };
}

export function toRecording(raw: Record<string, unknown>): Recording {
  const runs = list(raw.transcript_runs);
  // The primary run is what the case is built on; the others exist for the
  // benchmark and must never be shown as the transcript.
  const primary = runs.find((run) => run.is_primary) ?? runs[0];

  return {
    id: String(raw.id ?? ''),
    party_id: String(raw.party_id ?? ''),
    duration_ms: (raw.duration_ms as number | null) ?? null,
    processing_status: (raw.processing_status as Recording['processing_status']) ?? 'PENDING',
    failure_reason: (raw.failure_reason as string | null) ?? null,
    consent_recorded: Boolean(raw.consent_recorded),
    transcript_run: primary
      ? {
          id: String(primary.id ?? ''),
          provider: String(primary.provider ?? 'sahara'),
          model: (primary.model as string | null) ?? null,
          source_mode: (primary.source_mode as 'live' | 'fixture') ?? 'live',
          fixture_origin: (primary.fixture_origin as string | null) ?? null,
          latency_ms: (primary.latency_ms as number | null) ?? null,
          // Laravel names this `transcript`; the column is `normalized_transcript`.
          normalized_transcript: String(primary.transcript ?? ''),
          segments: list(primary.segments).map((segment) => ({
            id: String(segment.id ?? ''),
            sequence: count(segment.sequence),
            start_ms: count(segment.start_ms),
            end_ms: count(segment.end_ms),
            text: String(segment.text ?? ''),
            // Laravel names this `language`. Null when the provider does not
            // expose it — never fabricated, because an invented language span
            // would be a falsified audit trail.
            language_code: (segment.language as string | null) ?? null,
            confidence: (segment.confidence as number | null) ?? null,
          })),
        }
      : null,
  };
}
