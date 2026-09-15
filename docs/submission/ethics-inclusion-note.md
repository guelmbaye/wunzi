# WUNZI — Ethics, Safety & Inclusion Note

> AI structures. Humans mediate.

WUNZI is built for community mediation — work in which two people's accounts of a
dispute are heard, and a human decides nothing until both have been understood.
The ethical requirements of that setting are not a layer on top of the product.
They determined its architecture.

---

## 1. Consent

**Recording cannot begin without it.** Consent is a gate in the interface and a
required field on the API request, stored on the recording itself rather than
inferred from workflow position. A recording submitted without `consent_recorded`
is refused by `StoreRecordingRequest`, not merely discouraged.

**What the person is told, before the microphone opens:** that the recording is
stored privately, used to build a case for a human mediator, not shared with the
other party without agreement, and withdrawable.

**Withdrawal is real and it is documented.** A speaker may withdraw, which removes
the clip and every annotation derived from it. Encrypted backups are retained for
seven days, so full erasure completes within seven days rather than instantly.
That is stated rather than glossed: a retention window nobody wrote down is a
promise quietly broken.

**Benchmark audio** is participant-recorded or acted from consented scripts. No
scraped courtroom material, no recordings of real disputes obtained without
permission. Reference transcripts are pseudonymised.

---

## 2. Privacy

Mediation audio is among the more sensitive categories of personal data: two
people describing a conflict they are party to, often about money they cannot
afford to lose.

| Control | Implementation |
| --- | --- |
| Storage | Private object storage, bucket set to `anonymous none`, no public URL configured |
| Access | Short-lived signed URLs, 10-minute TTL, generated per request |
| Transport | Audio never passes through the browser-facing layer as bytes; the intelligence service reads it directly from private storage |
| Tokens | The API token lives on the Next.js server and is never sent to a browser — `lib/api.ts` is marked `server-only`, so a client import fails the build rather than leaking in production |
| Backups | Database dumps plus **GPG-encrypted** audio; the private key does not live on the server |
| Audit | Every state change writes an `audit_events` row with actor, action and timestamp |

Signed URLs are fetched **on demand**, one claim at a time, rather than embedded
in list payloads. A page of forty claims carrying forty signed URLs would be
handing the browser thirty-nine live grants to private mediation audio that
nobody asked for.

The intelligence service is designed to be unreachable from the internet. Where
it is exposed for inspection, only `/health` is public — everything that spends
ASR quota sits behind an IP allowlist, and the shared token is regenerated
afterwards.

---

## 3. Safety — what the system refuses to do

| Refused | Why |
| --- | --- |
| Decide who is telling the truth | No speech system can. Claiming it would be the product's central lie. |
| Score credibility | A credibility score is an accusation with a decimal point on it. |
| Recommend liability or a settlement | The mediator's judgement and the parties' agreement to reach. |
| Give legal advice | WUNZI does not interpret law. |
| Resolve a case autonomously | Removing the human removes the accountability. |

These are **enforced in code, in two services independently**. `NeutralityFilter`
(Laravel) and `neutrality.py` (FastAPI) implement the same rule separately:
FastAPI blocks before returning, Laravel blocks before persisting. The duplication
is deliberate — a single guard is a single point of failure, and adjudicative
prose reaching a mediator is the failure mode with the highest cost.

A matching pair of validators enforces provenance: every sentence in a case
packet must trace to a claim, an issue, or system metadata. A generated fact with
no source is rejected before the packet is assembled.

---

## 4. Preserving disagreement

Most summarisation systems reconcile. WUNZI does the opposite: when two accounts
differ, **the difference is the output**.

- **Two amounts are never averaged.** 150,000 and 100,000 produce a `DISPUTED`
  issue, not 125,000.
- **Reported speech stays reported.** "Party A states that Party B promised a
  refund" never becomes "Party B promised a refund".
- **Negation is a first-class property.** A dropped "not" reverses an issue from
  `AGREED` to `DISPUTED`. Where polarity cannot be resolved it is marked
  `UNCLEAR` rather than guessed — uncertainty is not promoted into a dispute the
  parties never had.
- **"Mentioned, not provided" never becomes "does not exist."**

---

## 5. Uncertainty stays visible

`UNVERIFIED` is a first-class state, not an error condition. A system that always
produces a confident answer is more dangerous in mediation than one that says a
thing was not established.

The Critical Speech Guard decides, per claim, what a mediator is allowed to see
unflagged:

| Decision | Meaning |
| --- | --- |
| `ACCEPT_FOR_CASE` | heard reliably enough to enter the case unmarked |
| `NEEDS_CONFIRMATION` | the speaker is asked to confirm their own words |
| `REJECT_AS_UNRESOLVED` | enters the case explicitly marked unresolved |

A case **cannot be finalised** while any critical field remains unconfirmed. That
gate lives in the state machine rather than a controller, so no route bypasses it.

The **Silent Resolution Rate** — a wrong value entering a case with no flag on it
— has a target of zero and is reported even when it is not zero.

---

## 6. Verification belongs to the speaker

Only the person who spoke may confirm or correct their own words. A mediator can
read a case and annotate it; they cannot rewrite a party's claim.

Every correction writes a `verification_event` with actor, timestamp, before and
after. The original is **superseded, never deleted** — both readings keep their
place in the record, because a correction is itself a fact about what happened in
the intake.

Clarification questions are non-suggestive by construction:

> "I heard the amount as 150,000 RWF. Is that correct?"

not

> "You said 150,000, right? That seems about right for a deposit."

The second version tells the speaker what to answer. The interface renders the
question **verbatim** from the guard — a friendlier rewrite in the UI would
reintroduce exactly the leading that the phrasing was designed to avoid.

**"Not sure" is a first-class answer.** Forcing a choice between yes and no would
manufacture certainty that does not exist, which is the failure this screen
exists to prevent.

---

## 7. Language equality and bias awareness

**Kinyarwanda, English and French are treated as equal.** Someone who switches
mid-sentence is not making a mistake. Most speech products quietly punish
switching, so people self-censor into one language and lose the detail that
matters. WUNZI tells speakers plainly that mixing is expected, and never breaks a
claim at a language boundary — a thought that crosses languages is still one
thought.

UI language, speech language and the canonical issue ontology are three separate
things. The ontology is language-independent, so a Kinyarwanda claim and a French
claim about the same amount compare directly.

**Numerals are canonicalised across all three languages** before comparison, so a
speaker is not disadvantaged for saying `ibihumbi ijana na mirongo itanu` rather
than `150,000`.

### Known bias risks, named

- **Model bias against low-resource languages is measured, not assumed away.** The
  benchmark reports per-language and per-code-mixing-intensity results rather than
  one average that would hide where a model fails.
- **Translation instead of transcription** is a bias with a specific victim: it
  erases the matrix language and returns the dominant one. WUNZI measures it
  directly as **Matrix Language Collapse Rate**, and the metric keys on English
  function-word density rather than matrix orthography — so it does not itself
  penalise languages without settled spelling conventions.
- **Orthographic instability inflates WER** in low-resource languages. That is why
  WER is reported for comparability and never as the headline.
- **The Kinyarwanda lexicon is explicit and MVP-scoped**, not a general parser.
  Phrasing outside it will be missed. A miss is safer than a guess — guessing a
  subject invents an accusation — but it is still a miss, and it will not be
  distributed evenly across speakers.
- **Annotation is a judgement.** Ground-truth issue states were set by two
  annotators with a third-pass adjudication; items still contested are excluded
  rather than forced.

---

## 8. Dignity

The people using WUNZI are in a dispute about money they may not be able to lose.
Several design choices follow from taking that seriously rather than from a
guideline:

- **No credibility signal anywhere in the interface.** No confidence percentages
  shown as though they described a person, no "reliability" ordering, no visual
  ranking of one account above the other.
- **Party A and Party B are visually equal.** Two colours drawn from the product
  mark, identical weight, identical column width. `DISPUTED` is rendered as a
  **split of the two party colours** rather than as a red warning — a dispute in
  which two accounts differ is the system working, and colouring it as an error
  would tell a mediator that disagreement is a fault.
- **Names or pseudonyms are the party's choice.** The case creation form says so.
- **The boundary is printed on the case packet itself**, not buried in terms:
  *"WUNZI prepared this case. The mediator remains responsible for
  interpretation, dialogue and resolution."*
- **Failures are explained, not hidden.** When transcription fails, the interface
  says the recording is kept and that WUNZI does not substitute another speech
  model — because that would change what the case is built on without saying so.

---

## 9. Accessibility of the target group

The intended users are **elected volunteers, at least 30% women by law**, not
lawyers and not typists. Two consequences:

- **Recording is the primary input**, not typing. A microphone that will not open
  never ends the intake — file upload is always available as a fallback.
- **The interface is readable, not clever.** Typeface chosen for diacritic
  coverage across all three languages and drawn for public-service use; issue
  states distinguished by shape and label as well as colour, so colour alone
  never carries meaning.

---

## 10. Limits we are not hiding

- **No field testing with real mediators.** The fit with Abunzi committees is
  argued from the structure of their work, not demonstrated. A pilot would change
  parts of this design and should happen before any real dispute touches it.
- **No real-world deployment.** Nothing in this submission has handled an actual
  case.
- **Benchmark fixtures in this repository are placeholders**, marked as such in
  the data, the runner, the report and the interface. No number produced from
  them describes any speech model.
- **Scope is narrow**: rental deposit disputes, two parties, Rwandan practice.
  Several rules hold only because there are exactly two accounts.
- **Backup retention delays erasure** by up to seven days after a withdrawal.
- **The system has not been adversarially tested** for a party deliberately
  gaming the intake.

Full list: `docs/limitations.md`. Enforcement details: `docs/responsible-ai.md`.

---

## 11. The line

WUNZI produces a structured case. It does not mediate. Everything after the case
packet — interpretation, dialogue, resolution, enforcement — is human work, and
the system is only useful to the extent that a mediator is present to do it.

That is not a disclaimer. It is the product.
