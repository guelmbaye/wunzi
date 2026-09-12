import Link from 'next/link';

/**
 * The hero is the product's thesis rendered literally: two accounts of one
 * dispute, side by side, unreconciled. Not a headline over a gradient — the
 * thing the software actually does, shown at the size of a headline.
 */
export default function HomePage() {
  return (
    <div className="mx-auto w-full max-w-6xl px-5">
      <section className="border-b border-rule py-16 sm:py-24">
        <h1 className="max-w-[18ch] text-display font-medium">
          Two accounts. One case. No invented middle.
        </h1>

        <p className="mt-6 max-w-prose text-lg leading-relaxed text-ink-soft">
          People describe the same dispute in different ways, in the languages they
          naturally mix. WUNZI captures both accounts, structures what was said, and hands
          a mediator a case that preserves the disagreement instead of resolving it.
        </p>

        <div className="mt-8 flex flex-wrap gap-3">
          <Link href="/cases" className="btn-primary">
            Open cases
          </Link>
          <Link href="/benchmark" className="btn-secondary">
            See why the speech model matters
          </Link>
        </div>
      </section>

      {/* The signature moment: the same issue, two values, no third number. */}
      <section className="py-14">
        <div className="card mx-auto max-w-3xl overflow-hidden">
          <div className="flex items-center justify-between border-b border-rule px-6 py-3">
            <h2 className="text-sm font-medium">Deposit amount</h2>
            <span className="inline-flex items-center gap-1.5 rounded-full border border-ink/25 px-2.5 py-1 text-xs font-medium">
              <span
                aria-hidden
                className="h-2 w-2 rounded-[2px] bg-gradient-to-r from-partyA from-50% to-partyB to-50%"
              />
              Disputed
            </span>
          </div>

          <div className="spine grid grid-cols-2 px-6 py-7">
            <div>
              <p className="text-micro font-medium text-partyA">Party A</p>
              <p className="tabular mt-1 text-3xl">150,000 RWF</p>
              <p className="mt-2 max-w-[22ch] text-sm leading-relaxed text-ink-soft">
                Party A states the deposit paid was 150,000 RWF.
              </p>
            </div>

            <div className="text-right">
              <p className="text-micro font-medium text-partyB">Party B</p>
              <p className="tabular mt-1 text-3xl">100,000 RWF</p>
              <p className="ml-auto mt-2 max-w-[22ch] text-sm leading-relaxed text-ink-soft">
                Party B states the deposit received was 100,000 RWF.
              </p>
            </div>
          </div>

          <p className="border-t border-rule px-6 py-3 text-micro text-ink-faint">
            WUNZI does not average these, and does not decide between them.
          </p>
        </div>
      </section>

      <section className="grid gap-10 border-t border-rule py-14 sm:grid-cols-3">
        <Principle title="Attribution survives">
          A claim never loses the person who made it. &ldquo;Party A states that Party B
          promised a refund&rdquo; never becomes &ldquo;Party B promised a refund&rdquo;.
        </Principle>

        <Principle title="Uncertainty stays visible">
          When a critical amount, date or negation cannot be heard reliably, WUNZI asks the
          speaker rather than guessing — and marks the issue unverified until they answer.
        </Principle>

        <Principle title="The mediator decides">
          WUNZI structures. It does not judge truth, score credibility, assign fault or
          propose a settlement. Those are the mediator&rsquo;s work and the parties&rsquo;
          agreement.
        </Principle>
      </section>
    </div>
  );
}

function Principle({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div>
      <h3 className="font-medium">{title}</h3>
      <p className="mt-2 text-sm leading-relaxed text-ink-soft">{children}</p>
    </div>
  );
}
