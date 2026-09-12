'use client';

import clsx from 'clsx';
import Link from 'next/link';
import { usePathname } from 'next/navigation';

import { CASE_STEPS, stepState } from '@/lib/states';
import type { CaseStatus } from '@/lib/types';

import { Count } from './StateBadge';

/**
 * The five steps of a case, drawn as one continuous rule — the same spine the
 * WUNZI mark is built around.
 *
 * Verification can pull the eye backwards: if a critical field is still
 * unconfirmed, step 3 is marked for attention even when the case has already
 * reached the issue map. Progress does not outrank an unresolved value.
 */
export function CaseStatusStepper({
  caseId,
  status,
  pendingFields,
}: {
  caseId: string;
  status: CaseStatus;
  pendingFields: number;
}) {
  const pathname = usePathname();

  return (
    <nav aria-label="Case progress" className="border-b border-rule bg-paper-raised">
      <ol className="mx-auto flex w-full max-w-6xl items-stretch px-5">
        {CASE_STEPS.map((step, index) => {
          const href = `/cases/${caseId}/${step.key}`;
          const active = pathname === href;
          const state = stepState(index, status, pendingFields);

          return (
            <li key={step.key} className="flex-1">
              <Link
                href={href}
                aria-current={active ? 'step' : undefined}
                className={clsx(
                  'group flex h-full flex-col gap-2 border-b-2 py-3 pr-4 transition-colors',
                  active
                    ? 'border-ink'
                    : state === 'attention'
                      ? 'border-pending/50'
                      : 'border-transparent hover:border-rule-strong',
                )}
              >
                <span className="flex items-center gap-2">
                  <StepMark index={index} state={state} />
                  <span
                    className={clsx(
                      'text-sm',
                      active || state === 'attention'
                        ? 'font-medium text-ink'
                        : state === 'done'
                          ? 'text-ink-soft'
                          : 'text-ink-faint',
                    )}
                  >
                    {step.label}
                  </span>
                  {step.key === 'verify' && pendingFields > 0 && (
                    <Count value={pendingFields} tone="alert" />
                  )}
                </span>
              </Link>
            </li>
          );
        })}
      </ol>
    </nav>
  );
}

function StepMark({ index, state }: { index: number; state: string }) {
  const base = 'flex h-5 w-5 shrink-0 items-center justify-center rounded-[5px] text-micro';

  if (state === 'done') {
    return (
      <span className={clsx(base, 'bg-ink text-paper')} aria-hidden>
        ✓
      </span>
    );
  }

  if (state === 'attention') {
    return (
      <span className={clsx(base, 'bg-pending text-white')} aria-hidden>
        !
      </span>
    );
  }

  if (state === 'current') {
    return (
      <span className={clsx(base, 'tabular border border-ink bg-paper text-ink')} aria-hidden>
        {index + 1}
      </span>
    );
  }

  return (
    <span
      className={clsx(base, 'tabular border border-dashed border-rule-strong text-ink-faint')}
      aria-hidden
    >
      {index + 1}
    </span>
  );
}
