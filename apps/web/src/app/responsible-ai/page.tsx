export const metadata = { title: 'Responsible AI' };

const REFUSED = [
  {
    claim: 'Decide who is telling the truth',
    why: 'No speech system can do this. Claiming it would be the product’s central lie.',
  },
  {
    claim: 'Score credibility',
    why: 'A credibility score is an accusation with a decimal point on it.',
  },
  {
    claim: 'Recommend liability or a settlement',
    why: 'That is the mediator’s judgement and the parties’ agreement to reach.',
  },
  { claim: 'Give legal advice', why: 'WUNZI does not interpret law.' },
  {
    claim: 'Resolve a case on its own',
    why: 'Removing the human removes the accountability.',
  },
];

export default function ResponsibleAiPage() {
  return (
    <div className="mx-auto w-full max-w-6xl px-5 py-10">
      <header className="max-w-prose">
        <h1 className="text-display font-medium">AI structures. Humans mediate.</h1>
        <p className="mt-5 text-lg leading-relaxed text-ink-soft">
          WUNZI captures each party’s account in their own words, extracts what they stated,
          flags what it could not hear reliably, and shows a mediator where the two accounts
          agree, differ, or say nothing at all.
        </p>
      </header>

      <section className="mt-14">
        <h2 className="text-sm font-medium">What WUNZI will not do</h2>
        <ul className="mt-4 divide-y divide-rule border-y border-rule">
          {REFUSED.map((item) => (
            <li key={item.claim} className="grid gap-2 py-4 sm:grid-cols-[22rem_1fr] sm:gap-8">
              <p className="font-medium">{item.claim}</p>
              <p className="text-sm leading-relaxed text-ink-soft">{item.why}</p>
            </li>
          ))}
        </ul>
        <p className="mt-4 max-w-prose text-sm leading-relaxed text-ink-soft">
          These are enforced in code, in both services independently. Generated language that
          assigns fault, ranks credibility or recommends an outcome is rejected before it can
          reach a mediator — once by the intelligence service before it returns, and again by
          the system of record before it is stored.
        </p>
      </section>

      <section className="mt-14 grid gap-10 sm:grid-cols-3">
        <Block title="Disagreement is preserved">
          Two amounts are never averaged. 150,000 and 100,000 produce a disputed issue, not
          125,000. Reported speech stays reported: “Party A states that Party B promised a
          refund” never becomes “Party B promised a refund”.
        </Block>

        <Block title="Uncertainty is a visible state">
          A system that always sounds confident is more dangerous in mediation than one that
          says a thing was not established. When a critical amount, date or negation cannot
          be heard reliably, WUNZI asks the speaker and marks the issue unverified until
          they answer.
        </Block>

        <Block title="Verification belongs to the speaker">
          Only the person who spoke may confirm or correct their own words. Corrections are
          recorded alongside the original — nothing is deleted, and both readings keep their
          place in the record.
        </Block>
      </section>

      <section className="mt-14 max-w-prose">
        <h2 className="text-sm font-medium">Language</h2>
        <p className="mt-3 text-sm leading-relaxed text-ink-soft">
          Kinyarwanda, English and French are treated as equal. Someone who switches
          mid-sentence is not making a mistake, and WUNZI never breaks a claim at a language
          boundary — a thought that crosses languages is still one thought.
        </p>
      </section>

      <section className="mt-14 max-w-prose">
        <h2 className="text-sm font-medium">Limits</h2>
        <ul className="mt-3 space-y-2 text-sm leading-relaxed text-ink-soft">
          <li>Rental deposit disputes only, with two parties, built around Rwandan practice.</li>
          <li>
            Evaluated on fifteen disputes. Confidence intervals are reported because the set
            is small enough that a point estimate alone would overstate what is known.
          </li>
          <li>
            Kinyarwanda numerals and first-person verb forms are handled by an explicit
            lexicon rather than a general parser. Phrasing outside it will be missed — a miss
            is safer than a guess.
          </li>
          <li>
            Consent is recorded per recording and can be withdrawn, which removes the audio
            and everything derived from it.
          </li>
        </ul>
      </section>
    </div>
  );
}

function Block({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div>
      <h3 className="font-medium">{title}</h3>
      <p className="mt-2 text-sm leading-relaxed text-ink-soft">{children}</p>
    </div>
  );
}
