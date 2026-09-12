'use client';

import Link from 'next/link';
import { useActionState } from 'react';

import { createCase } from '@/app/actions';

/** Four fields. Anything more is a form standing between a person and their story. */
export default function NewCasePage() {
  const [state, action, pending] = useActionState(createCase, { error: null });

  return (
    <div className="mx-auto w-full max-w-2xl px-5 py-10">
      <Link href="/cases" className="text-sm text-ink-soft hover:text-ink">
        Cases
      </Link>

      <h1 className="mt-3 text-3xl font-medium">New case</h1>
      <p className="mt-2 max-w-prose text-sm leading-relaxed text-ink-soft">
        Use labels or pseudonyms if the parties prefer. Names are only used to address
        people in the case; they are never used to judge an account.
      </p>

      <form action={action} className="mt-8 space-y-6">
        <div>
          <label htmlFor="category" className="label">
            Dispute type
          </label>
          <select id="category" name="category" className="field" defaultValue="rental_deposit">
            <option value="rental_deposit">Rental deposit dispute</option>
          </select>
          <p className="mt-1.5 text-micro text-ink-faint">
            Rental deposit is the only type WUNZI is trained and evaluated on.
          </p>
        </div>

        <div>
          <label htmlFor="title" className="label">
            Case name <span className="font-normal text-ink-faint">(optional)</span>
          </label>
          <input id="title" name="title" className="field" placeholder="Kigali, Nyarugenge" />
        </div>

        <div className="grid gap-5 sm:grid-cols-2">
          <div>
            <label htmlFor="party_a_name" className="label">
              <span className="mr-2 inline-block h-2.5 w-1 translate-y-px rounded-full bg-partyA" />
              Party A
            </label>
            <input
              id="party_a_name"
              name="party_a_name"
              required
              className="field"
              placeholder="Tenant"
            />
          </div>

          <div>
            <label htmlFor="party_b_name" className="label">
              <span className="mr-2 inline-block h-2.5 w-1 translate-y-px rounded-full bg-partyB" />
              Party B
            </label>
            <input
              id="party_b_name"
              name="party_b_name"
              required
              className="field"
              placeholder="Landlord"
            />
          </div>
        </div>

        {state.error && (
          <p className="rounded-card border border-pending/40 bg-pending-soft px-3 py-2 text-sm text-pending-ink">
            {state.error}
          </p>
        )}

        <button type="submit" disabled={pending} className="btn-primary">
          {pending ? 'Creating…' : 'Start Party A intake'}
        </button>
      </form>
    </div>
  );
}
