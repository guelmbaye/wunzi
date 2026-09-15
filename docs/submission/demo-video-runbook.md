# Demo video runbook

Target: **5 minutes**. Screen recording with voice-over.

The order below is deliberate: **consequence before mechanism**. A judge who sees
150,000 sitting next to 100,000 in the first thirty seconds understands the
product; one who watches an architecture diagram first is still waiting to find
out what it does.

---

## Before you press record

### 1. Decide which mode you are demonstrating

This matters more than anything else in the setup, and it changes what you can
show.

| Mode | What you can film | What you need |
| --- | --- | --- |
| **`WUNZI_MODE=live`** | Speaking into the microphone and watching your own words come back | A working `SAHARA_API_KEY` |
| **`WUNZI_MODE=fixture`** | Everything except live speech; the intake replays a stored consented clip | Nothing |

**If you have a Sahara key, use live mode.** Speaking Kinyarwanda into the
microphone and watching the transcript appear is the single most convincing shot
available, and nothing else substitutes for it.

**In fixture mode, do not press the record button on camera.** A freshly recorded
file has no cached transcription, the job fails, and the recording is marked
`FAILED`. The intake screen offers a clearly labelled **"Use the stored
recording"** button instead — use that, and say on camera why it is there.

### 2. Produce the report you will show in Shot 7

The AfriSwitch numbers live in a file, not in the web interface — the tier-1
benchmark runs from the CLI and writes markdown. Generate the corrected version
before filming:

```powershell
Get-ChildItem benchmark\reports\afriswitch-kinyarwanda-*.json |
  Sort-Object LastWriteTime | Select-Object -Last 1

python -m app.benchmark.afriswitch_cli rescore `
  --input benchmark\reports\afriswitch-kinyarwanda-<timestamp>.json `
  --out benchmark\reports
```

`rescore` re-aggregates a saved run under the current rules — failed calls
excluded from the error rates — and makes **no API calls**. Sahara's credits are
spent; this is how the corrected figures are produced without another run.

Open the resulting `*-rescored-*.md` in an editor with a readable font. That is
the second screen of Shot 7.

### 3. Reset to a clean state

```bash
cd /var/www/wunzi
docker compose -f docker-compose.prod.yml exec app php artisan migrate:fresh --force
docker compose -f docker-compose.prod.yml exec app php artisan db:seed --force
docker compose -f docker-compose.prod.yml exec app php artisan wunzi:demo-case
docker compose -f docker-compose.prod.yml exec app php artisan wunzi:token
```

Paste the token into `WUNZI_API_TOKEN`, then `up -d --build web`.

`migrate:fresh` matters: neutral sentences are stored at ingestion time, not
computed at display time, so a case built before the latest deploy will show the
old text.

### 4. Prepare the browser

- **Close every other tab.** A visible unrelated tab is the most common thing
  that makes a demo look unrehearsed.
- Zoom to **110–125%** so text is legible after compression.
- Light mode, no extensions visible, no bookmarks bar.
- **Pre-load these in order**, then step back to tab 1:

```
1  https://wunzi.vylantic.com/
2  https://wunzi.vylantic.com/cases
3  https://wunzi.vylantic.com/cases/<ID>/party-a
4  https://wunzi.vylantic.com/cases/<ID>/party-b
5  https://wunzi.vylantic.com/cases/<ID>/verify
6  https://wunzi.vylantic.com/cases/<ID>/issues
7  https://wunzi.vylantic.com/cases/<ID>/packet
8  https://wunzi.vylantic.com/benchmark
```

Plus one editor window holding
`benchmark/reports/afriswitch-kinyarwanda-rescored-*.md`.

Get `<ID>` from `/cases` once, and keep it on a sticky note. Fumbling a URL on
camera costs a retake.

### 5. Check the recording setup

- **1080p minimum.** The issue map has small text; 720p loses the confidence
  intervals entirely.
- Test thirty seconds and play it back before committing to a full take.
- Narration in **English**, matching the interface. If you prefer French, add
  English subtitles — a judge should not be reading one language while looking
  at another.

### 6. One thing to rehearse

The finding in Shot 7b: Sahara keeps the matrix language but drops most of the
English insertions, and word error rate does not show it. That is the argument
the whole submission rests on, and it is the one passage worth saying out loud a
few times before recording.

The caveat that goes with it — one model measured, not four — is one sentence.
Say it plainly and move on. A judge who discovers a gap themselves reads it as a
gap; a team that names it first reads as one you can trust with the numbers it
does publish.

---

## Shot 1 — The dispute · 0:00–0:35

**Screen:** `https://wunzi.vylantic.com/` — scroll slowly to the disputed-amount
card and stop there. Leave it on screen while you talk.

**Say:**

> Two people describe the same rental deposit dispute. One says the deposit was
> 150,000 Rwandan francs. The other says 100,000. They both speak Kinyarwanda,
> English and French, often inside one sentence.
>
> Most systems would summarise this into a single clean account. WUNZI does the
> opposite. The difference between the two accounts *is* the case, and the job is
> to structure it without deciding it.

**Point at:** the two amounts, side by side, and the line underneath —
*"WUNZI does not average these, and does not decide between them."*

---

## Shot 2 — Who this is for · 0:35–1:00

**Screen:** stay on the home page, or cut to a single title card if you have one.

**Say:**

> This is built for community mediation. In Rwanda, the Abunzi — elected
> volunteer mediation committees — are a mandatory step before most civil
> disputes can reach a court. Over thirty-eight thousand mediators, fifty-one
> thousand cases in a year, growing thirty percent over three years.
>
> They are not lawyers and not typists. Everything they work from is spoken, in
> mixed languages. That is the problem WUNZI addresses.

Keep this short. It is context, not the demo.

---

## Shot 3 — Party A speaks · 1:00–1:50

**Screen:** tab 3, `/cases/<ID>/party-a`.

**In live mode:** press record, speak the Party A account aloud, stop, send for
transcription. Let the processing state show — do not cut it. Then the transcript
appears.

**In fixture mode:** show the consent gate first, then:

> This deployment replays stored provider output rather than calling a live
> speech API, so I am using the stored consented clip rather than recording now.

Click **"Use the stored recording for Party A"**.

**Once the transcript is on screen**, scroll to the segment list and point at the
language tags:

> Kinyarwanda, then English, then back again — inside one account. That is the
> speech this product exists for.
>
> WUNZI marks a switch only where the provider reported one, and shows nothing
> where it did not. Intron's file endpoint returns a flat transcript with no
> per-segment language, so on a live call there are no tags here — and none get
> invented, because a language tag WUNZI made up would be a falsified audit
> trail. What you are seeing is the stored run, which carries them.

Do not overstate this on camera. The claim is that WUNZI never fabricates
metadata, not that every provider supplies it.

Scroll to the claim cards:

> Each card records one thing Party A said. Note the phrasing: *"Party A states
> that Party B promised a full refund."* Not *"Party B promised a refund."* The
> attribution never gets dropped, because the moment it does, one person's
> account becomes the record.

**Point at:** the "Quoting the other party" badge on the refund claim.

---

## Shot 4 — Party B speaks · 1:50–2:25

**Screen:** tab 4, `/cases/<ID>/party-b`. Load the account the same way.

**Say:**

> The second account. Party B gives a different amount — 100,000 — and denies
> promising a refund.
>
> That denial is the hard part. It is spoken in Kinyarwanda, in the sentence
> immediately after an English one. If a speech model loses that negation, the
> issue flips from disputed to agreed, and a mediator walks into the room
> believing a promise was made that nobody made.

**Point at:** the `Ntabwo namusezeranyije…` segment, then the **Refund denial**
claim card showing the negative polarity.

---

## Shot 5 — The system stops and asks · 2:25–3:05

**Screen:** tab 5, `/cases/<ID>/verify`.

**Say:**

> Here is where WUNZI is agentic in the way that matters. It did not just
> transcribe and move on. It decided, on its own, that two values were not heard
> reliably enough to enter a case unmarked — and it stopped the workflow to ask
> the person who said them.
>
> Read the question: *"I heard a statement about who is responsible for the
> damage. Could you repeat that part?"* It does not say *"you said Party B did
> it, right?"* The phrasing is deliberately non-suggestive, and the interface
> renders it verbatim — a friendlier rewrite here would tell the speaker what to
> answer.

**Point at:** the three buttons.

> And **"Not sure" is a real answer.** Forcing a yes or no would manufacture
> certainty that does not exist, which is exactly the failure this screen exists
> to prevent.

Expand **"Why this is being checked"** to show the guard's reasons. Then:

> Only the speaker can confirm or correct their own words. A mediator can read a
> case; they cannot rewrite what a party said.

**Optional, if the take is running short:** click "Yes, that is correct" on one
field so the pending count drops in the stepper above. It is a satisfying beat.

---

## Shot 6 — The issue map · 3:05–3:55

**Screen:** tab 6, `/cases/<ID>/issues`. This is the payoff screen — give it
time and do not scroll fast.

**Say:**

> Four states, and none of them is a verdict. Agreed, disputed, missing,
> unverified.

Stop on **Deposit amount**:

> 150,000 on the left, 100,000 on the right. No third number appears anywhere on
> this screen. WUNZI does not average them and does not choose between them.
>
> The colours are not decoration. Party A is blue and Party B is teal on every
> screen in the product. Disputed is drawn as a split of those two colours —
> both voices, unreconciled — rather than as a red error, because a dispute where
> two accounts differ is the system working correctly.

Scroll to **Missing**:

> Missing is different from disputed. *"Repair evidence — mentioned, not
> provided."* Party B referred to an invoice. Nobody produced it. WUNZI records
> that it was mentioned and not provided, and never turns that into "it does not
> exist."

**Point at:** the dashed borders on the missing items — absence drawn as absence.

---

## Shot 7 — The benchmark · 3:55–4:45

**This shot changed.** It was written when the only numbers available came from
placeholder fixtures. Sahara has since been measured on the real AfriSwitch
Kinyarwanda corpus, so the caveat that used to fill this shot is now one
sentence, and the shot leads with a result.

**Two screens, in this order.**

### 7a — the mechanism, in the product · 3:55–4:15

**Screen:** tab 8, `/benchmark`, then open the most recent run.

This is the tier-2 case: the same demo dispute, run through four speech models
with everything downstream frozen.

> Same audio. Same claim engine, same guard, same issue rules. Only the speech
> model changes.
>
> The question is not which model transcribes more words correctly. It is whether
> a mediator reading the resulting case would have understood the same thing.

Point at the bottom row of the same-audio table:

> The last row is the mediation state — what the mediator would actually have
> been handed.

Then, without dwelling on it:

> These particular clips are stored fixtures, so this screen shows the mechanism
> rather than a measurement — and the software says so itself. The measured
> numbers are here.

### 7b — the measurement · 4:15–4:45

**Screen:** the rescored AfriSwitch report, open in an editor or rendered
markdown. `benchmark/reports/afriswitch-kinyarwanda-rescored-*.md`.

Scroll to the **Overall** table and the **code-mixing profile**.

> This is Sahara on AfriSwitch — Intron's own code-switching corpus, 200
> Kinyarwanda utterances, human-transcribed, stratified by how densely the
> speaker mixes languages. We did not choose which utterances are hard.
>
> Word error rate is 0.36. Intron publishes 0.26 for Sahara on their clinical
> Kinyarwanda set. Ours is conversational code-switched speech, which is harder,
> so that gap is what you would expect — and the benchmark prints the comparison
> on every run, because a harness that lands an order of magnitude away is broken
> before it is interesting.

Then the finding — this is the part worth slowing down for:

> Two things WER cannot tell you, and this benchmark does.
>
> Sahara does not translate. Matrix language collapse is essentially zero, and
> span fidelity is 0.84 — the Kinyarwanda survives. That matters more than it
> sounds: a model that returns fluent English for a Kinyarwanda account has
> produced useful prose and the wrong artefact, because it is no longer what the
> speaker said.
>
> But it reproduces only about 40% of the English insertions, and that holds at
> every level of mixing. Word error rate rises with mixing intensity — 0.33 to
> 0.45 — while switch preservation stays flat and low. A model can hold its error
> rate and still stop reproducing how the person actually spoke.

**One sentence of caveat, not a paragraph:**

> One model is measured here, not four. Sahara's credits ran out before the
> comparison could be completed, and the report says which layer is measured and
> which is not.

*If the Whisper run completed before filming, drop that sentence and say instead:
"Sahara and Whisper on identical audio, same stratified sample, same harness."*

### What not to do in this shot

- **Do not cite the ten-utterance run.** An early sample suggested switch
  preservation collapsed on heavy mixing. At 200 it did not — 0.34, 0.41, 0.43,
  flat. It was noise, and a judge who recalculates would find it.
- **Do not round 0.36 down** or drop the confidence interval when you show the
  table on screen.

---

## Shot 8 — The boundary · 4:40–5:00

**Screen:** tab 7, `/cases/<ID>/packet`, scrolled to the bottom line.

**Say:**

> This is the document the mediator receives. Every sentence in it traces back
> through a claim, to a transcript segment, to the audio and the timestamp that
> produced it. Nothing appears here that nobody said.
>
> And the last line is printed on the case itself, not buried in terms:

Read it from the screen:

> *"WUNZI prepared this case. The mediator remains responsible for
> interpretation, dialogue and resolution."*

Close on:

> WUNZI structures. It does not decide who is telling the truth, score
> credibility, assign fault, or propose a settlement. Those refusals are enforced
> in code, in two services independently — not written in a policy document and
> hoped for.
>
> AI structures. Humans mediate.

---

## Timing summary

| Shot | Content | Duration | Running |
| --- | --- | --- | --- |
| 1 | The dispute | 0:35 | 0:35 |
| 2 | Who this is for | 0:25 | 1:00 |
| 3 | Party A + code-switching | 0:50 | 1:50 |
| 4 | Party B + the negation | 0:35 | 2:25 |
| 5 | The guard interrupts | 0:40 | 3:05 |
| 6 | The issue map | 0:50 | 3:55 |
| 7a | Benchmark mechanism, in the product | 0:20 | 4:15 |
| 7b | The measured AfriSwitch result | 0:30 | 4:45 |
| 8 | The boundary | 0:20 | 5:05 |

Shots 2 and 8 are the compressible ones if you overrun. **Do not cut Shot 5** —
the guard deciding to interrupt is the strongest single argument that the system
is agentic in a way that helps rather than one that overreaches.

---

## What judges are scoring, and where it appears

| Criterion | Weight | Shot |
| --- | --- | --- |
| Code-Switching Benchmark Quality | 30% | **7b**, plus the written report |
| Product Quality & Fit ("is it agentic?") | 25% | **5**, then 3 and 6 |
| Real-World Impact | 20% | 2, with the Abunzi figures |
| Technical Execution | 15% | 3 (processing states), 7 (frozen pipeline) |
| Ethics, Safety & Inclusion | 10% | 5 (consent, speaker-only verification), 8 (the boundary) |

---

## Mistakes worth avoiding

- **Do not narrate the architecture.** No service diagram, no "Laravel talks to
  FastAPI". A judge who wants that reads the docs. Five minutes of video should
  be five minutes of the product working.
- **Do not speed up the processing state.** Watching the transcript arrive is
  evidence that it is real. Cutting it invites the suspicion that it was not.
- **Do not cite the ten-utterance run.** It showed a pattern that did not
  survive at 200. Shot 7 says why.
- **Do not click anything that 404s or errors.** Walk the exact path above once
  before recording.
- **Do not read these lines word for word.** They are the argument, not a script.
  A take that sounds read is worse than one that stumbles slightly.

---

## Publishing

- Upload to YouTube as **unlisted** (or public).
- Title: `WUNZI — Switch-Aware Mediation Case Intelligence | Sahara CodeSwitch Africa Challenge`
- In the description, put the repository link, the category
  (Legal & Public Services), the languages, and one line naming what was measured
  and what was not — so it is visible to anyone who skips to the benchmark
  section.
- **Check the link in a private window before submitting.** An unlisted video set
  to private by accident is an unrecoverable mistake with one submission per
  token.
