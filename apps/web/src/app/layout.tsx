import type { Metadata } from 'next';
import Image from 'next/image';
import Link from 'next/link';

import './globals.css';

/*
 * Fonts are linked rather than bundled through `next/font`.
 *
 * `next/font` downloads the files at build time, which makes the build fail on
 * an air-gapped or firewalled machine — and this product is meant to be
 * demonstrable when the network drops. Linking with a real system fallback
 * stack means an offline demo renders in a slightly different typeface instead
 * of not rendering at all.
 *
 * Public Sans was drawn for government services, the exact vernacular of a
 * mediation tool, and covers the diacritics Kinyarwanda and French need.
 * Newsreader is reserved for the case packet, because a case packet is a
 * document and should read like one.
 */
const FONT_HREF =
  'https://fonts.googleapis.com/css2?family=Public+Sans:wght@400;500;600&family=Newsreader:wght@400;500&display=swap';

export const metadata: Metadata = {
  title: {
    default: 'WUNZI — Switch-Aware Mediation Case Intelligence',
    template: '%s · WUNZI',
  },
  description:
    'Capture both accounts of a dispute in the languages people actually mix, then hand a mediator a structured case that preserves the disagreement instead of resolving it.',
  icons: { icon: '/wunzi-icon.png' },
};

const NAV = [
  { href: '/cases', label: 'Cases' },
  { href: '/benchmark', label: 'Benchmark' },
  { href: '/responsible-ai', label: 'Responsible AI' },
];

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link rel="stylesheet" href={FONT_HREF} />
      </head>
      <body className="flex min-h-screen flex-col">
        <a
          href="#main"
          className="sr-only focus:not-sr-only focus:absolute focus:left-4 focus:top-4 focus:z-50 focus:rounded-card focus:bg-ink focus:px-4 focus:py-2 focus:text-paper"
        >
          Skip to content
        </a>

        <header className="border-b border-rule bg-paper-raised">
          <div className="mx-auto flex h-16 w-full max-w-6xl items-center gap-8 px-5">
            <Link href="/" className="flex items-center" aria-label="WUNZI home">
              <Image
                src="/wunzi-logo.png"
                alt="WUNZI"
                width={392}
                height={133}
                priority
                className="h-7 w-auto"
              />
            </Link>

            <nav className="flex items-center gap-1 text-sm" aria-label="Main">
              {NAV.map((item) => (
                <Link
                  key={item.href}
                  href={item.href}
                  className="rounded-card px-3 py-2 text-ink-soft transition-colors hover:bg-paper-sunken hover:text-ink"
                >
                  {item.label}
                </Link>
              ))}
            </nav>
          </div>
        </header>

        <main id="main" className="flex-1">
          {children}
        </main>

        <footer className="mt-16 border-t border-rule">
          <div className="mx-auto w-full max-w-6xl px-5 py-8 text-sm text-ink-faint">
            <p className="max-w-prose">
              WUNZI structures what was said. A human mediator remains responsible for
              interpretation, dialogue and resolution.
            </p>
          </div>
        </footer>
      </body>
    </html>
  );
}
