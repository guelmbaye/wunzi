import type { Config } from 'tailwindcss';

/**
 * Tokens come from the WUNZI mark: two arcs converging on a spine without
 * merging. Party A is always the blue arc, Party B always the teal one, on
 * every screen, forever. If those two colours ever drift or swap, the whole
 * interface starts lying about who said what.
 */
const config: Config = {
  content: ['./src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        ink: {
          DEFAULT: '#152131', // the mark's spine
          soft: '#3A4759',
          faint: '#6B7887',
        },
        paper: {
          DEFAULT: '#FBFAF8',
          raised: '#FFFFFF',
          sunken: '#F2F1ED',
        },
        rule: {
          DEFAULT: '#E2E0DA',
          strong: '#CBC8C0',
        },
        // Party identity. Never reused for anything else.
        partyA: { DEFAULT: '#1555AF', soft: '#E7EEF9', ink: '#0E3C7D' },
        partyB: { DEFAULT: '#1B8F84', soft: '#E4F2F0', ink: '#12655D' },
        // Only UNVERIFIED gets a colour of its own — it is the one state that
        // means "stop and check". AGREED uses ink, DISPUTED splits the two
        // party colours, MISSING is drawn as absence.
        pending: { DEFAULT: '#8A6A1F', soft: '#F6F0DF', ink: '#6A5117' },
      },
      fontFamily: {
        // Public Sans was drawn for government services — the exact vernacular
        // of a mediation tool — and covers the diacritics Kinyarwanda and
        // French need. Newsreader is reserved for the case packet, because a
        // case packet is a document and should look like one.
        sans: ['var(--font-public-sans)', 'system-ui', 'sans-serif'],
        document: ['var(--font-newsreader)', 'Georgia', 'serif'],
      },
      fontSize: {
        micro: ['0.6875rem', { lineHeight: '1rem', letterSpacing: '0.02em' }],
        amount: ['1.375rem', { lineHeight: '1.75rem', letterSpacing: '-0.01em' }],
        display: ['clamp(2rem, 5vw, 3.25rem)', { lineHeight: '1.05', letterSpacing: '-0.03em' }],
      },
      maxWidth: {
        prose: '68ch',
      },
      borderRadius: {
        // The mark's corners are softly rounded squares, not pills.
        card: '10px',
      },
      backgroundImage: {
        'hatch-pending':
          'repeating-linear-gradient(135deg, transparent 0 5px, rgba(138,106,31,0.10) 5px 10px)',
      },
      keyframes: {
        'proof-step': {
          '0%': { opacity: '0', transform: 'translateY(6px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
      },
      animation: {
        // One orchestrated sequence in the whole product: the sponsor proof.
        'proof-step': 'proof-step 320ms ease-out both',
      },
    },
  },
  plugins: [],
};

export default config;
