import type { Config } from 'tailwindcss';

const config: Config = {
  content: ['./app/**/*.{ts,tsx}', './components/**/*.{ts,tsx}'],
  theme: {
    extend: {
      fontFamily: {
        kopub: ['var(--font-kopub)', 'sans-serif'],
      },
      colors: {
        // Clay semantic tokens (mapped to palette values below)
        'clay-accent': '#7c3aed',   // = violet-600 (VAIV brand)
        'clay-border': '#dad4c8',   // = oat.DEFAULT
        'clay-surface': '#faf9f7',  // = cream
        'clay-text': '#55534e',     // = warmCharcoal
        'clay-bg': '#faf9f7',
        'clay-muted': '#9f9b93',
        // Clay base — see DESIGN.md §2
        cream: '#faf9f7',
        clayBlack: '#000000',
        oat: {
          DEFAULT: '#dad4c8',
          light: '#eee9df',
        },
        warmSilver: '#9f9b93',
        warmCharcoal: '#55534e',
        // Swatch palette
        matcha: {
          300: '#84e7a5',
          600: '#078a52',
          800: '#02492a',
        },
        slushie: {
          500: '#3bd3fd',
          800: '#0089ad',
        },
        lemon: {
          400: '#f8cc65',
          500: '#fbbd41',
          700: '#d08a11',
          800: '#9d6a09',
        },
        ube: {
          300: '#c1b0ff',
          800: '#43089f',
          900: '#32037d',
        },
        pomegranate: {
          400: '#fc7981',
        },
        blueberry: {
          800: '#01418d',
        },
      },
      borderRadius: {
        card: '12px',
        feature: '24px',
        section: '40px',
      },
      boxShadow: {
        'clay': '0px 1px 1px rgba(0,0,0,0.1), 0px -1px 1px rgba(0,0,0,0.04) inset, 0px -0.5px 1px rgba(0,0,0,0.05)',
        'clay-0': 'none',
        'clay-1': '0 1px 3px rgba(0,0,0,0.06)',
        'clay-2': '0 4px 12px rgba(0,0,0,0.08)',
        'clay-focus': '0 0 0 2px rgba(124,58,237,0.2)',
      },
    },
  },
  plugins: [],
};

export default config;
