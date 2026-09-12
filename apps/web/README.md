# WUNZI — Mediator workspace

Next.js 15 (App Router) + TypeScript + Tailwind. Talks only to the Laravel
System of Record; it never reaches the intelligence service directly.

## Running

```bash
npm install
cp .env.example .env.local
npm run dev        # http://localhost:3000
npm run typecheck
npm run build
```

### Two things that must be set, or every screen reports a failure

**`LARAVEL_API_URL`.** The compose default is `http://api:8000`, a service name
that only resolves inside the compose network. Running `npm run dev` on a host it
does not resolve, and the workspace cannot reach the API at all. Use
`http://localhost:8000`.

**`WUNZI_API_TOKEN`.** Every `/api` route except `/health`, `/responsible-ai` and
`/auth/login` is behind `auth:sanctum`. Without a token the API answers 401 to
everything, including the case list.

```bash
cd apps/api
php artisan db:seed        # creates mediator@wunzi.demo
php artisan wunzi:token    # prints LARAVEL_API_URL and WUNZI_API_TOKEN to paste
```

There is no browser login flow. That is deliberate for now: the token stays on
the Next server and is never sent to a browser, and a mediation workspace should
not ship a half-built identity story. Adding real sign-in is the next piece of
work, not an oversight to paper over with a login form that stores a token in
`localStorage`.

## Screens

| Route | Purpose |
| --- | --- |
| `/` | The thesis: two accounts, one case, no invented middle |
| `/cases` | Case list |
| `/cases/new` | Four fields and nothing else |
| `/cases/[id]` | Overview, with verification pulled to the front when it is pending |
| `/cases/[id]/party-a`, `/party-b` | Voice capture → transcript → claims |
| `/cases/[id]/verify` | The speaker confirms or corrects their own words |
| `/cases/[id]/issues` | Agreed / Disputed / Missing / Unverified |
| `/cases/[id]/packet` | The mediator-ready document |
| `/benchmark`, `/benchmark/[run]` | Same audio, different speech model, different mediation state |
| `/responsible-ai` | What WUNZI refuses to do, and why |

## Design

The mark is two arcs converging on a spine without merging, and the interface
takes that literally. Party A is the blue arc and Party B the teal one on every
screen — if those two colours ever drift or swap, the UI starts lying about who
said what. Issues are drawn as one row split down the middle with the state in
the gutter, so two values sit side by side and the interface offers no third
number.

The four states are deliberately **not** a red/green scale. `DISPUTED` is not an
error — a dispute where two accounts differ is the system working — so it is
drawn as a split of the two party colours rather than as a warning. `MISSING` is
drawn as absence (dashed, unfilled). `UNVERIFIED` is the only state with a colour
of its own, because it is the only one that means stop and check.

## Boundaries kept in the client

- **The token never reaches the browser.** Reads happen in Server Components,
  writes in Server Actions, and `lib/api.ts` is marked `server-only` so a client
  import fails at build time rather than in production. Client-safe URL builders
  live separately in `lib/urls.ts`.
- **Language tags are shown only where the provider reported them.** Sahara
  returns per-segment language; Whisper reports one per request. That difference
  is displayed, not smoothed over — an invented language span would be a
  fabricated audit trail.
- **Benchmark numbers from placeholder fixtures are not rendered as results.**
  `SponsorDeltaCard` checks `publishable` and refuses the headline figure.
- **Verification questions are rendered verbatim.** The Critical Speech Guard
  writes them to be non-suggestive; a friendlier rewrite here would tell the
  speaker what to answer.
- **Fonts are linked, not bundled.** `next/font` fetches at build time, which
  breaks on an air-gapped machine. A demo that loses the network should render in
  a fallback typeface, not fail.
