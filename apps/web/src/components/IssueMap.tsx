import clsx from 'clsx';

import { ISSUE_ORDER, ISSUE_STATE, PARTY, formatValue, sentenceCase } from '@/lib/states';
import type { EvidenceReference, Issue } from '@/lib/types';

import { Count, StateBadge } from './StateBadge';

/**
 * The Issue Map.
 *
 * Not a node-link graph: a mediator needs to read this in ten seconds, and a
 * dense graph is a puzzle. Not four equal columns either — that hides the thing
 * that matters. Instead every issue is one row split down the middle, Party A
 * on the left in blue and Party B on the right in teal, with the state sitting
 * in the gutter between them.
 *
 * Where the accounts agree the row reads as one statement. Where they differ,
 * two values sit side by side and the interface offers no third number.
 */
export function IssueMap({
  issues,
  evidence,
}: {
  issues: Issue[];
  evidence: EvidenceReference[];
}) {
  const grouped = ISSUE_ORDER.map((status) => ({
    status,
    items: issues.filter((issue) => issue.status === status),
  })).filter((group) => group.items.length > 0);

  if (issues.length === 0) {
    return (
      <p className="card p-6 text-sm text-ink-soft">
        The issue map is built once both accounts have been captured.
      </p>
    );
  }

  return (
    <div className="space-y-10">
      {grouped.map((group) => (
        <section key={group.status}>
          <div className="mb-3 flex items-center gap-3">
            <h2 className="text-sm font-medium">{ISSUE_STATE[group.status].label}</h2>
            <Count value={group.items.length} />
            <p className="text-sm text-ink-faint">{ISSUE_STATE[group.status].sentence}</p>
          </div>

          <div className="space-y-2">
            {group.items.map((issue) => (
              <IssueRow key={issue.id} issue={issue} />
            ))}
          </div>
        </section>
      ))}

      {evidence.length > 0 && <EvidenceList evidence={evidence} />}
    </div>
  );
}

function IssueRow({ issue }: { issue: Issue }) {
  const state = ISSUE_STATE[issue.status];
  const valueA = formatValue(issue.party_a_value);
  const valueB = formatValue(issue.party_b_value);
  const twoSided = issue.status === 'DISPUTED' || (Boolean(valueA) && Boolean(valueB));

  return (
    <article className={clsx('rounded-card border', state.panel)}>
      <div className="flex flex-wrap items-center justify-between gap-3 px-5 pt-4">
        <h3 className="font-medium">{issue.label || sentenceCase(issue.canonical_type)}</h3>
        <StateBadge status={issue.status} size="sm" />
      </div>

      {twoSided ? (
        <div className="spine mt-3 grid grid-cols-2 gap-px px-5 pb-4">
          <Side
            role="PARTY_A"
            value={valueA}
            statement={issue.party_a_statement}
            align="left"
          />
          <Side
            role="PARTY_B"
            value={valueB}
            statement={issue.party_b_statement}
            align="right"
          />
        </div>
      ) : (
        <div className="px-5 pb-4 pt-2">
          <p className="text-sm leading-relaxed text-ink-soft">
            {issue.summary ?? state.sentence}
          </p>
        </div>
      )}

      {issue.classification_reason && (
        <p className="border-t border-rule/70 px-5 py-2 text-micro text-ink-faint">
          {issue.classification_reason}
        </p>
      )}
    </article>
  );
}

function Side({
  role,
  value,
  statement,
  align,
}: {
  role: keyof typeof PARTY;
  value: string | null;
  statement: string | null;
  align: 'left' | 'right';
}) {
  const party = PARTY[role];

  return (
    <div className={clsx('px-4 py-1', align === 'right' ? 'text-right' : 'text-left')}>
      <p className={clsx('text-micro font-medium', party.text)}>{party.label}</p>

      {value ? (
        <p className="tabular mt-1 text-amount">{value}</p>
      ) : (
        <p className="mt-1 text-sm text-ink-faint">No information</p>
      )}

      {statement && (
        <p className="mt-1.5 text-micro leading-relaxed text-ink-soft">{statement}</p>
      )}
    </div>
  );
}

function EvidenceList({ evidence }: { evidence: EvidenceReference[] }) {
  return (
    <section>
      <h2 className="mb-3 text-sm font-medium">Evidence</h2>

      <ul className="space-y-2">
        {evidence.map((item) => (
          <li
            key={item.id}
            className="flex flex-wrap items-baseline justify-between gap-3 rounded-card border border-dashed border-rule-strong px-5 py-3"
          >
            <span className="text-sm">{sentenceCase(item.type)}</span>
            <span className="text-micro text-ink-soft">
              {/* "Mentioned, not provided" is not "does not exist", and the
                  wording keeps that difference. */}
              {item.availability === 'MENTIONED_NOT_PROVIDED'
                ? 'Mentioned, not provided'
                : item.availability === 'AVAILABLE'
                  ? 'Provided'
                  : 'Not provided'}
            </span>
          </li>
        ))}
      </ul>
    </section>
  );
}

/** Compact counts used on the case overview. */
export function IssueSummary({ issues }: { issues: Issue[] }) {
  const counts = ISSUE_ORDER.map((status) => ({
    status,
    count: issues.filter((issue) => issue.status === status).length,
  }));

  return (
    <dl className="grid grid-cols-2 gap-3 sm:grid-cols-4">
      {counts.map(({ status, count }) => (
        <div key={status} className={clsx('rounded-card border p-4', ISSUE_STATE[status].panel)}>
          <dt className="text-micro text-ink-soft">{ISSUE_STATE[status].label}</dt>
          <dd className="tabular mt-1 text-2xl">{count}</dd>
        </div>
      ))}
    </dl>
  );
}
