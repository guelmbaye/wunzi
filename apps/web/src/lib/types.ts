/**
 * Mirrors the Laravel API resources. Kept hand-written rather than generated so
 * a shape change shows up as a type error here instead of as `undefined` on a
 * mediator's screen.
 */

export type PartyRole = 'PARTY_A' | 'PARTY_B';

export type CaseStatus =
  | 'DRAFT'
  | 'PARTY_A_CAPTURE'
  | 'PARTY_B_CAPTURE'
  | 'VERIFICATION_REQUIRED'
  | 'ISSUE_GRAPH_READY'
  | 'MEDIATOR_REVIEW'
  | 'READY';

export type IssueStatus = 'AGREED' | 'DISPUTED' | 'MISSING' | 'UNVERIFIED';

export type VerificationStatus =
  | 'UNVERIFIED'
  | 'CONFIRMED_BY_SPEAKER'
  | 'CORRECTED_BY_SPEAKER'
  | 'UNRESOLVED';

export type CriticalFieldStatus = 'NEEDS_CONFIRMATION' | 'CONFIRMED' | 'CORRECTED' | 'UNRESOLVED';

export type ProcessingStatus =
  | 'PENDING'
  | 'TRANSCRIBING'
  | 'TRANSCRIBED'
  | 'EXTRACTING'
  | 'CLAIMS_READY'
  | 'FAILED';

export type AsrProvider = 'sahara' | 'whisper' | 'model_b' | 'model_c';

export interface Party {
  id: string;
  role: PartyRole;
  display_name: string;
  consent_status: string;
  recordings_count?: number;
}

export interface MediationCase {
  id: string;
  public_reference: string;
  category: string;
  title: string | null;
  status: CaseStatus;
  parties: Party[];
  counts: {
    claims: number;
    issues: number;
    /** Comes from Laravel's `meta`, not the resource: it is a query, not a column. */
    pending_critical_fields: number;
  };
  created_at: string;
  updated_at: string;
}

/** Laravel's own overview shape. Richer than a claim dump, so kept as-is. */
export interface CaseOverview {
  case: MediationCase;
  progress: {
    party_a: boolean;
    party_b: boolean;
    verification: boolean;
    issue_map: boolean;
    packet: boolean;
  };
  summary: {
    agreed: number;
    disputed: number;
    missing: number;
    unverified: number;
    fields_needing_verification: number;
  };
}

export interface TranscriptSegment {
  id: string;
  sequence: number;
  start_ms: number;
  end_ms: number;
  text: string;
  /** Null when the provider does not expose it. Never fabricated. */
  language_code: string | null;
  confidence: number | null;
}

export interface TranscriptRun {
  id: string;
  provider: string;
  model: string | null;
  source_mode: 'live' | 'fixture';
  fixture_origin: string | null;
  latency_ms: number | null;
  normalized_transcript: string;
  segments: TranscriptSegment[];
}

export interface Recording {
  id: string;
  party_id: string;
  duration_ms: number | null;
  processing_status: ProcessingStatus;
  failure_reason: string | null;
  consent_recorded: boolean;
  /** The primary run only. Benchmark runs exist but are never the transcript. */
  transcript_run: TranscriptRun | null;
}

export interface CanonicalValue {
  amount_minor?: number;
  currency?: string;
  iso_date?: string | null;
  day?: number | null;
  month?: number | null;
  year?: number | null;
  scope?: string;
  evidence_type?: string;
  surface?: string;
}

export interface Claim {
  id: string;
  party_role: PartyRole;
  type: string;
  subject: string | null;
  predicate: string;
  canonical_value: CanonicalValue | null;
  polarity: 'POSITIVE' | 'NEGATIVE' | 'UNCLEAR';
  criticality: 'HIGH' | 'MEDIUM' | 'LOW';
  verification_status: VerificationStatus;
  /** True when the speaker is quoting the other party, never flattened away. */
  reported_speech: boolean;
  is_superseded: boolean;
  /** Neutral rendering built server-side: "Party A states that…" */
  statement: string;
  /**
   * Whether the claim can be traced back to audio. The span itself is fetched
   * on demand from /claims/{id}/audio-source — a list of forty claims should
   * not carry forty signed URLs that expire in ten minutes.
   */
  has_audio_source: boolean;
}

export interface CriticalField {
  id: string;
  claim_id: string;
  party_role: PartyRole;
  field_type: string;
  detected_value: string | null;
  normalized_value: string | null;
  status: CriticalFieldStatus;
  risk_level: string;
  guard_reason: string[];
  /** Non-suggestive by construction. Rendered verbatim, never rewritten here. */
  prompt_text: string | null;
  claim_statement: string;
  has_audio_source: boolean;
}

export interface Issue {
  id: string;
  canonical_type: string;
  /** Display label, derived client-side: Laravel sends the canonical type only. */
  label: string;
  status: IssueStatus;
  criticality: 'HIGH' | 'MEDIUM' | 'LOW';
  summary: string | null;
  /** Laravel names this `reason`; the column is `classification_reason`. */
  classification_reason: string | null;
  party_a_value: CanonicalValue | null;
  party_b_value: CanonicalValue | null;
}

export interface EvidenceReference {
  id: string;
  type: string;
  availability: 'AVAILABLE' | 'MENTIONED_NOT_PROVIDED' | 'MISSING' | 'DISPUTED';
  /** Laravel phrases this: "mentioned, not provided" is never "does not exist". */
  label: string | null;
  description: string | null;
}

export interface PacketIssueEntry {
  issue_id: string;
  type: string;
  label: string;
  status: IssueStatus;
  statement: string;
  reason: string | null;
  party_a_value: CanonicalValue | null;
  party_b_value: CanonicalValue | null;
}

export interface PacketClaimEntry {
  claim_id: string;
  type: string;
  statement: string;
  value: CanonicalValue | null;
  verification: string;
  reported_speech: boolean;
  audio_source_available: boolean;
}

export interface CasePacket {
  id: string;
  version: number;
  generated_at: string;
  payload: {
    case_reference: string;
    category: string;
    status_label: string;
    parties: { role: PartyRole; display_name: string }[];
    agreed: PacketIssueEntry[];
    disputed: PacketIssueEntry[];
    missing_information: PacketIssueEntry[];
    unverified_information: PacketIssueEntry[];
    party_a_claims: PacketClaimEntry[];
    party_b_claims: PacketClaimEntry[];
    requested_outcomes: Record<string, string | null>;
    evidence_gaps: { evidence_id: string; type: string; statement: string }[];
    human_boundary: string;
  };
}

export interface BenchmarkMetric {
  provider: AsrProvider;
  metric: string;
  value: number;
  ci_low: number | null;
  ci_high: number | null;
  scope: string;
  sample_count: number | null;
}

export interface BenchmarkRun {
  id: string;
  dataset_version: string;
  split: string;
  providers: AsrProvider[];
  status: string;
  guard_enabled: boolean;
  sponsor_outcome_delta: number | null;
  best_competitor: AsrProvider | null;
  sponsor_verdict: string | null;
  git_commit: string | null;
  /** False when any clip was scored from a placeholder fixture. */
  results: {
    publishable?: boolean;
    publishability_note?: string | null;
    integrity?: string | null;
  } | null;
  metrics: BenchmarkMetric[];
  completed_at: string | null;
}

/** One row of the same-audio comparison — the sponsor proof screen. */
export interface SameAudioRow {
  element: string;
  label: string;
  expected: string | null;
  by_provider: Record<string, { value: string | null; correct: boolean | null }>;
}

export interface SameAudioComparison {
  clip_id: string;
  scenario_id: string;
  providers: AsrProvider[];
  rows: SameAudioRow[];
  publishable: boolean;
  integrity_note: string;
}
