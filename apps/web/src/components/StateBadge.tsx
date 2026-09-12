import clsx from 'clsx';

import { ISSUE_STATE, PARTY } from '@/lib/states';
import type { IssueStatus, PartyRole } from '@/lib/types';

/**
 * The state chip. Four states, four visual languages — never a red/green scale,
 * because DISPUTED is not a failure. A dispute in which the two accounts differ
 * is the system working.
 */
export function StateBadge({
  status,
  size = 'md',
}: {
  status: IssueStatus;
  size?: 'sm' | 'md';
}) {
  const state = ISSUE_STATE[status];

  return (
    <span
      className={clsx(
        'inline-flex items-center gap-1.5 rounded-full font-medium',
        state.chip,
        size === 'sm' ? 'px-2 py-0.5 text-micro' : 'px-2.5 py-1 text-xs',
      )}
    >
      <span
        aria-hidden
        className={clsx('h-2 w-2 shrink-0 rounded-[2px]', state.marker)}
      />
      {state.label}
    </span>
  );
}

/**
 * Party identity is a colour commitment, not decoration: Party A is the blue
 * arc of the mark and Party B the teal one, on every screen. The name is always
 * present too — colour alone would fail anyone who cannot distinguish them.
 */
export function PartyTag({
  role,
  name,
  className,
}: {
  role: PartyRole;
  name?: string;
  className?: string;
}) {
  const party = PARTY[role];

  return (
    <span className={clsx('inline-flex items-center gap-2 text-xs font-medium', className)}>
      <span aria-hidden className={clsx('h-3 w-1 rounded-full', party.bg)} />
      <span className={party.text}>{name ?? party.label}</span>
    </span>
  );
}

/** Small count pill used on the stepper and the issue map headings. */
export function Count({ value, tone = 'quiet' }: { value: number; tone?: 'quiet' | 'alert' }) {
  return (
    <span
      className={clsx(
        'tabular inline-flex h-5 min-w-5 items-center justify-center rounded-full px-1.5 text-micro font-semibold',
        tone === 'alert' ? 'bg-pending text-white' : 'bg-paper-sunken text-ink-soft',
      )}
    >
      {value}
    </span>
  );
}
