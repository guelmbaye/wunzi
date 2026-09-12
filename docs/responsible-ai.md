# Responsible AI — WUNZI

> AI structures. Humans mediate.

## What WUNZI does

Captures each party's account in their own words, extracts attributed claims,
flags what it could not hear reliably, and shows a mediator where two accounts
agree, differ, or say nothing at all.

## What WUNZI will not do

| Refused | Why |
| --- | --- |
| Decide who is telling the truth | Not a capability any speech system has. Claiming it would be the product's central lie. |
| Score credibility | A credibility score is an accusation with a decimal point. |
| Recommend liability or a settlement | That is the mediator's judgement and the parties' agreement. |
| Give legal advice | WUNZI does not interpret law. |
| Resolve a case autonomously | Removing the human removes the accountability. |

These are enforced in code, not policy documents. `NeutralityFilter` (Laravel)
and `neutrality.py` (FastAPI) reject adjudicative language before it can reach a
mediator, in both services independently.

## Preserved disagreement

Most summarisation systems reconcile. WUNZI does the opposite: when two accounts
differ, the difference is the output.

- Two amounts are never averaged. 150,000 and 100,000 produce `DISPUTED`, not 125,000.
- Reported speech stays reported. "Party A states that Party B promised a refund"
  never becomes "Party B promised a refund".
- Negation is preserved as a first-class property. A lost "not" flips an issue
  from `AGREED` to `DISPUTED`, so polarity that cannot be resolved is marked
  `UNCLEAR` rather than guessed.
- "Mentioned, not provided" never becomes "does not exist".

## Visible uncertainty

`UNVERIFIED` is a first-class state, not an error. A system that always produces
a confident answer is more dangerous in mediation than one that says "this was
not established". The Critical Speech Guard exists to keep uncertainty visible:

| Decision | Meaning |
| --- | --- |
| `ACCEPT_FOR_CASE` | heard reliably enough to enter the case unflagged |
| `NEEDS_CONFIRMATION` | the speaker is asked to confirm their own words |
| `REJECT_AS_UNRESOLVED` | enters the case explicitly marked as unresolved |

The **Silent Resolution Rate** — a wrong value entering a case with no flag —
has a target of zero. It is reported even when it is not zero.

## Verification belongs to the speaker

Only the person who spoke may confirm or correct their own words. A mediator can
annotate, but cannot rewrite a party's claim. Every correction produces a
`verification_event` with actor, timestamp, before and after; the original is
superseded, never deleted.

Clarification questions are non-suggestive by construction:

> "I heard the amount as 150,000 RWF. Is that correct?"

not

> "You said 150,000, right? That seems about right for a deposit."

The second version tells the speaker what to say.

## Consent

Recording requires explicit consent, stored as a field on the recording rather
than assumed by workflow position. Audio lives in private storage reached only
through short-lived signed URLs. Benchmark audio is participant-recorded or acted
from consented scripts — no scraped courtroom material. A speaker may withdraw,
which removes the clip and every annotation derived from it.

## Language

Kinyarwanda, English and French are treated as equal. A speaker who switches
mid-sentence is not making an error; the system must follow. Claim boundaries are
never drawn at a language switch, because a thought that crosses languages is
still one thought.

UI language, speech language and the canonical issue ontology are three separate
things. The ontology is language-independent, so a Kinyarwanda claim and a French
claim about the same amount compare directly.

## Known limits

See [limitations.md](limitations.md). Every one of them is stated in the demo, not
discovered by a judge.
