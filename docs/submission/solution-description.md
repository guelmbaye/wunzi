# WUNZI — Solution Description

**Switch-Aware Mediation Case Intelligence**
Category: **Legal & Public Services** · Demo locale: Rwanda · Kinyarwanda ⇄ English ⇄ French

> Hear every side. Structure what matters.
> AI structures. Humans mediate.

---

## 1. The problem

Rwanda resolves most civil disputes outside its courts. The **Abunzi** — community
mediation committees — are a mandatory first step before a civil matter below
3 million RWF (about US$2,700) may proceed to court. The system is large and
growing:

| | |
| --- | --- |
| Mediators nationwide | **over 38,000** |
| Committees | 2,150 at cell level, 416 at sector level |
| Cases received, FY ending June 2017 | **51,016** (89.1% civil) |
| Growth in caseload over three years | **+30.9%** |
| Reduction in civil matters reaching courts | **85%** |

Mediators are **elected volunteers of 7–12 people per committee, at least 30%
women** — respected community members, not lawyers, not typists, and not trained
in record-keeping.

Three things about that work are hard, and they compound:

**Everything is spoken, in mixed languages.** A tenant describes a deposit
dispute in Kinyarwanda, names the amount in Kinyarwanda numerals, switches to
English for *deposit* and *contract*, and drops into French for the part they
learned from a form. A mediator hears this twice, from two people, and has to
hold both versions in their head.

**The two accounts genuinely differ, and that difference is the case.** One party
says 150,000 RWF; the other says 100,000. One says a full refund was promised;
the other denies promising anything. A mediation does not begin by deciding who
is right — it begins by establishing precisely where the accounts diverge.

**A single misheard number changes the outcome.** 150,000 heard as 50,000 is not
a transcription typo. It is a different dispute.

Existing speech tools fail this work in a specific way. They are built to produce
one clean, fluent transcript. Faced with code-switched speech they often
**translate rather than transcribe** — returning polished English for a
Kinyarwanda utterance. The output reads well and is the wrong artefact: it is no
longer the speaker's own words, so nothing built on it can be traced back to what
anyone actually said.

Summarisation tools fail worse. They reconcile. Handed two accounts that differ,
they produce a smooth middle — and a mediation built on an invented middle has
already gone wrong before the parties sit down.

---

## 2. Target users

**Primary: community mediators.** Abunzi committee members and equivalent
community mediators elsewhere in the region. Non-specialists, volunteers,
handling a caseload that grew 30.9% in three years, working entirely from spoken
accounts in mixed languages.

**Secondary: the disputing parties.** They are not passive subjects. WUNZI asks
them to confirm their own words when a critical value could not be heard
reliably — the only person permitted to correct a claim is the person who made
it.

**Population.** Rwanda alone: 51,000+ cases a year through a system that is the
mandatory route for most civil disputes. The same structure — community
mediation as a first-instance step, conducted orally in code-switched speech —
recurs across the region.

**A limit stated up front:** WUNZI has not been tested with Abunzi committees.
The fit is argued from the structure of the work, not demonstrated in the field.
A pilot with real mediators is the next step and would change parts of this
design.

---

## 3. The solution

```
Voice → ASR → Claims → Attribution → Verification → Issue Graph → Mediation Case
```

Each party records their account separately, in whatever mix of languages they
naturally speak. WUNZI extracts what each person **stated** — never what
happened — and produces a structured case in which every issue sits in exactly
one of four states:

| State | Meaning |
| --- | --- |
| `AGREED` | Both accounts align |
| `DISPUTED` | The accounts differ — two values shown, never averaged |
| `MISSING` | One account says nothing about it |
| `UNVERIFIED` | Not established; a critical value is still unconfirmed |

None of the four is a verdict. The mediator walks into the room knowing exactly
where the disagreement is, and decides nothing they did not decide before.

### What makes it switch-aware

**Claims are never broken at a language boundary.** A thought that crosses
languages is still one thought. Spans are split at clause boundaries — including
contrast conjunctions, where polarity turns — not where the speaker changed
language.

**Numerals are canonicalised across all three languages.** `150,000`,
`one hundred fifty thousand`, `cent cinquante mille` and
`ibihumbi ijana na mirongo itanu` all reduce to 150000 before comparison.

**Negation is a first-class property.** A dropped "not" reverses an issue from
`AGREED` to `DISPUTED`. Where polarity cannot be resolved, WUNZI marks it
`UNCLEAR` rather than guessing — uncertainty is not promoted into a dispute the
parties never had.

**Reported speech stays reported.** "Party A states that Party B promised a
refund" never becomes "Party B promised a refund".

### The Critical Speech Guard

When a consequential value — an amount, a date, a negation, an attribution —
cannot be heard reliably enough, WUNZI does not guess and does not silently
proceed. It **interrupts and asks the speaker**, with a question written to be
non-suggestive:

> "I heard the amount as 150,000 RWF. Is that correct?"

not

> "You said 150,000, right? That seems about right for a deposit."

The second version tells the speaker what to answer. "Not sure" is a first-class
response: forcing a yes/no would manufacture certainty that does not exist, which
is the failure the guard exists to prevent.

A case cannot be finalised while a critical value remains unconfirmed. That gate
lives in the state machine, not in a controller, so no route can bypass it.

---

## 4. Is it agentic?

Yes, in the sense that matters — and deliberately not in one that would make it
worse.

WUNZI takes autonomous multi-step action: it transcribes, extracts atomic claims,
resolves attribution, assesses whether each claim is consequential enough to
require confirmation, **decides on its own to interrupt a workflow and question a
human**, waits, incorporates the answer, compares two accounts, and assembles a
document. Nobody drives those steps.

The decision to stop and ask is the interesting one. An agent that only acts is
easy; an agent that recognises the limit of what it reliably heard, and hands
control back with a specific question, is doing the harder thing.

What WUNZI deliberately is **not** is autonomous in judgement. There is no
multi-agent debate, no "truth agent", no arbiter. That is not a missing feature.
In mediation, autonomy of judgement is precisely the capability that must not
exist: a system that decided who was right would be making an unappealable
determination about two people's livelihoods on the basis of a speech model's
confidence score. Adding agents to look more agentic would break the product's
thesis and its ethics at the same time.

---

## 5. Key technical decisions

**Three services, one direction of authority.**
Next.js → Laravel 11 (System of Record) → PostgreSQL 16, with FastAPI holding the
intelligence layer. Laravel owns state; FastAPI owns language; **neither owns the
outcome**. FastAPI never writes to the database — it receives structured input,
returns structured output, and Laravel decides whether that output may change a
case.

**A pluggable ASR adapter contract.** Every provider implements one interface.
No code downstream of the adapter branches on provider identity except benchmark
labelling. Swapping Sahara for Whisper changes one environment variable — which
is what makes the benchmark a measurement rather than a story.

**Provider metadata is never synthesised.** Sahara reports language per segment;
Whisper reports one language per request. That difference is shown in the
interface, not smoothed over. An invented language span would be a falsified
audit trail, and the Critical Speech Guard reads those confidence fields.

**A failed provider is a recorded failure.** WUNZI never silently falls back to a
different speech model. Substitution would corrupt the benchmark and make a case's
provenance false.

**A deterministic engine by default.** Claim extraction runs on rules and
lexicons, not an LLM. It is inspectable and consistent, and a judge can see
exactly why each claim was produced. The trade is recall on unusual phrasing, and
it is the right trade for a legal record. Where semantic comparison cannot decide,
the answer is `UNCERTAIN`, which surfaces as `UNVERIFIED` — a valid, visible
state.

**Two independent guards, in two services.** `NeutralityFilter` (Laravel) and
`neutrality.py` (FastAPI) implement the same rule separately; so do the
hallucination validators. FastAPI blocks before returning, Laravel blocks before
persisting. The duplication is deliberate: a single guard is a single point of
failure, and adjudicative prose reaching a mediator is the failure mode with the
highest cost.

**Full provenance, enforced.** Every sentence in a case packet traces back
through claim → transcript segment → audio → timestamp. A statement without
provenance is rejected before the packet is assembled. From any line a mediator
reads, they can play the audio that produced it.

**A phrase table, not a conjugator.** Neutral sentences are rendered from an
explicit table of positive/negative forms. Negation is where a mediation turns,
and "is responsible" negates to "is not responsible", not to "did not is
responsible". Eleven reviewed lines beat a clever conjugator nobody can verify.

**Deliberately absent:** no graph database (the issue graph is small and
relational), no RAG over legal corpora (WUNZI does not interpret law), no
multi-agent orchestration. Each omission removes a way for the system to appear
more capable than it is.

---

## 6. How it was evaluated

Two tiers, described in full in `docs/benchmark-methodology.md` and reported in
`docs/submission/benchmark-report.md`.

**Tier 1 — AfriSwitch (external).** `intronhealth/AfriSwitch`, Kinyarwanda config:
5.00 hours, 1,577 utterances, CMI 16.95, 4.51 switch points per utterance.
Human-transcribed, published, with English spans annotated. Standard WER and CER
plus three code-switch measures WER cannot express — including **Matrix Language
Collapse Rate**, which detects a model translating instead of transcribing.

**Tier 2 — mediation outcome.** The question neither AfriSwitch nor Intron's
AfriHealth MultiBench asks: *did the transcription difference change what a
mediator would be handed?* Measured as **CMSR** (Correct Mediation State Rate),
all-or-nothing per case — a mediator handed one wrong `DISPUTED` among six correct
issues still walks into the room carrying a conflict that does not exist.

Everything downstream of transcription is frozen for the duration of a run. Only
the ASR provider changes.

---

## 7. What WUNZI will not do

| Refused | Why |
| --- | --- |
| Decide who is telling the truth | No speech system can. Claiming it would be the product's central lie. |
| Score credibility | A credibility score is an accusation with a decimal point on it. |
| Recommend liability or a settlement | The mediator's judgement and the parties' agreement to reach. |
| Give legal advice | WUNZI does not interpret law. |
| Resolve a case autonomously | Removing the human removes the accountability. |

These are enforced in code, in both services independently — not stated in a
policy document and hoped for.

---

## 8. Honest limits

- **Scope:** rental deposit disputes, two parties, built around Rwandan practice.
  Several resolution rules — including the pronoun convention that maps a
  third-person referent to "the other party" — hold only because there are
  exactly two accounts.
- **No field testing.** The fit with Abunzi committees is argued from the
  structure of their work, not demonstrated with real mediators.
- **Kinyarwanda coverage is lexicon-based**, not a general morphological parser.
  Phrasing outside the rental-deposit vocabulary will be missed. A miss is safer
  than a guess, and it is still a miss.
- **The evaluation set is small** — 15 mediation scenarios. Confidence intervals
  are reported precisely because a point estimate alone would overstate what is
  known.
- **Benchmark fixtures shipped in this repository are placeholders.** They are
  marked `is_placeholder: true`; the runner sets `publishable: false`, the report
  prints a banner, and the interface refuses to render the headline figure. See
  the benchmark report for what this means for the numbers.

Full list: `docs/limitations.md`.
