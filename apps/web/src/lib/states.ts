import type { CanonicalValue, CaseStatus, IssueStatus, PartyRole } from './types';

/**
 * The four states carry the product's entire ethic, so their presentation is
 * defined once, here.
 *
 * Deliberately NOT a red/green success-failure scale: DISPUTED is not an error.
 * A dispute where the two accounts differ is working exactly as intended, and
 * colouring it red would tell a mediator that disagreement is a fault.
 *
 *   AGREED      solid ink — settled, quiet
 *   DISPUTED    the two party colours split down the middle — both voices,
 *               unreconciled, with the system refusing to pick
 *   MISSING     dashed outline, no fill — absence drawn as absence
 *   UNVERIFIED  hatched ochre — the one state that means stop and check
 */
export const ISSUE_STATE = {
  AGREED: {
    label: 'Agreed',
    sentence: 'Both accounts align.',
    chip: 'bg-ink text-white',
    marker: 'bg-ink',
    panel: 'border-rule bg-paper-raised',
  },
  DISPUTED: {
    label: 'Disputed',
    sentence: 'The accounts differ.',
    chip: 'bg-paper-raised text-ink border border-ink/25',
    // Split fill: half Party A, half Party B. The system shows both and picks
    // neither.
    marker: 'bg-gradient-to-r from-partyA from-50% to-partyB to-50%',
    panel: 'border-ink/20 bg-paper-raised',
  },
  MISSING: {
    label: 'Missing',
    sentence: 'No information was provided.',
    chip: 'bg-transparent text-ink-soft border border-dashed border-rule-strong',
    marker: 'border border-dashed border-rule-strong bg-transparent',
    panel: 'border-dashed border-rule-strong bg-transparent',
  },
  UNVERIFIED: {
    label: 'Unverified',
    sentence: 'Not yet established.',
    chip: 'bg-pending-soft text-pending-ink border border-pending/30',
    marker: 'bg-hatch-pending border border-pending/40',
    panel: 'border-pending/35 bg-pending-soft/40',
  },
} as const satisfies Record<IssueStatus, unknown>;

export const ISSUE_ORDER: IssueStatus[] = ['DISPUTED', 'UNVERIFIED', 'MISSING', 'AGREED'];

export const PARTY = {
  PARTY_A: {
    label: 'Party A',
    text: 'text-partyA',
    bg: 'bg-partyA',
    soft: 'bg-partyA-soft',
    border: 'border-partyA',
    ring: 'ring-partyA',
  },
  PARTY_B: {
    label: 'Party B',
    text: 'text-partyB',
    bg: 'bg-partyB',
    soft: 'bg-partyB-soft',
    border: 'border-partyB',
    ring: 'ring-partyB',
  },
} as const satisfies Record<PartyRole, unknown>;

/** The five steps of the case, in order. Mirrors Laravel's CaseStatus enum. */
export const CASE_STEPS = [
  { key: 'party-a', label: 'Party A', reached: ['PARTY_A_CAPTURE'] },
  { key: 'party-b', label: 'Party B', reached: ['PARTY_B_CAPTURE'] },
  { key: 'verify', label: 'Verify', reached: ['VERIFICATION_REQUIRED'] },
  { key: 'issues', label: 'Issue map', reached: ['ISSUE_GRAPH_READY'] },
  { key: 'packet', label: 'Case', reached: ['MEDIATOR_REVIEW', 'READY'] },
] as const;

const STATUS_RANK: Record<CaseStatus, number> = {
  DRAFT: 0,
  PARTY_A_CAPTURE: 1,
  PARTY_B_CAPTURE: 2,
  VERIFICATION_REQUIRED: 3,
  ISSUE_GRAPH_READY: 4,
  MEDIATOR_REVIEW: 5,
  READY: 5,
};

export const CASE_STATUS_LABEL: Record<CaseStatus, string> = {
  DRAFT: 'Draft',
  PARTY_A_CAPTURE: 'Party A intake',
  PARTY_B_CAPTURE: 'Party B intake',
  VERIFICATION_REQUIRED: 'Needs verification',
  ISSUE_GRAPH_READY: 'Issue map ready',
  MEDIATOR_REVIEW: 'Mediator review',
  READY: 'Ready for mediator',
};

export type StepState = 'todo' | 'current' | 'done' | 'attention';

export function stepState(stepIndex: number, status: CaseStatus, pendingFields: number): StepState {
  const rank = STATUS_RANK[status];

  // Verification outranks progress: an unresolved critical field pulls the eye
  // back to step 3 no matter how far the case has otherwise travelled.
  if (stepIndex === 2 && pendingFields > 0) return 'attention';
  if (stepIndex + 1 < rank) return 'done';
  if (stepIndex + 1 === rank) return 'current';
  return 'todo';
}

// ── value rendering ─────────────────────────────────────────────────────────

/**
 * Amounts are shown exactly as canonicalised, never rounded and never
 * reconciled. 150,000 and 100,000 stay two numbers.
 */
export function formatValue(value: CanonicalValue | null | undefined): string | null {
  if (!value) return null;

  if (typeof value.amount_minor === 'number') {
    const amount = new Intl.NumberFormat('en-RW').format(value.amount_minor);
    return `${amount} ${value.currency ?? 'RWF'}`;
  }

  if (value.iso_date) return formatIsoDate(value.iso_date);

  if (value.day && value.month) {
    return new Intl.DateTimeFormat('en-GB', { day: 'numeric', month: 'long' }).format(
      new Date(2000, value.month - 1, value.day),
    );
  }

  if (value.scope) return sentenceCase(value.scope);
  if (value.evidence_type) return sentenceCase(value.evidence_type);

  return null;
}

export function formatIsoDate(iso: string): string {
  return new Intl.DateTimeFormat('en-GB', {
    day: 'numeric',
    month: 'long',
    year: 'numeric',
  }).format(new Date(iso));
}

export function formatRelative(iso: string): string {
  const seconds = Math.round((Date.now() - new Date(iso).getTime()) / 1000);
  const units: [Intl.RelativeTimeFormatUnit, number][] = [
    ['day', 86400],
    ['hour', 3600],
    ['minute', 60],
  ];

  const formatter = new Intl.RelativeTimeFormat('en', { numeric: 'auto' });

  for (const [unit, size] of units) {
    if (Math.abs(seconds) >= size) return formatter.format(-Math.round(seconds / size), unit);
  }

  return 'just now';
}

export function formatDuration(ms: number | null | undefined): string {
  if (!ms) return '0:00';
  const total = Math.round(ms / 1000);
  return `${Math.floor(total / 60)}:${String(total % 60).padStart(2, '0')}`;
}

export function sentenceCase(raw: string): string {
  const words = raw.replace(/_/g, ' ').trim();
  return words.charAt(0).toUpperCase() + words.slice(1);
}

/**
 * Language tags are shown because a switch mid-sentence is the point of the
 * product — but only when the provider actually reported one. A guessed
 * language on a transcript span would be a fabricated audit trail.
 */
export const LANGUAGE_LABEL: Record<string, string> = {
  rw: 'Kinyarwanda',
  en: 'English',
  fr: 'French',
};
