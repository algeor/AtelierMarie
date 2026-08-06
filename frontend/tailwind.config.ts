import type { Config } from "tailwindcss";

const rgbVar = (name: string) => `rgb(var(${name}) / <alpha-value>)`;

const paletteColors = {
  "soft-blush": rgbVar("--palette-soft-blush"),
  "coral-dream": rgbVar("--palette-coral-dream"),
  "muted-rose": rgbVar("--palette-muted-rose"),
  "vintage-mauve": rgbVar("--palette-vintage-mauve"),
  "dusty-terra": rgbVar("--palette-dusty-terra"),
  "warm-clay": rgbVar("--palette-warm-clay"),
  "soft-off-white": rgbVar("--palette-soft-off-white"),
  "warm-cream": rgbVar("--palette-warm-cream"),
  "sand-taupe": rgbVar("--palette-sand-taupe"),
  sage: rgbVar("--palette-sage"),
  "dark-brown": rgbVar("--palette-dark-brown"),
  "deep-green-black": rgbVar("--palette-deep-green-black"),
};

const semanticColors = {
  page: rgbVar("--color-page"),
  surface: rgbVar("--color-surface"),
  "surface-elevated": rgbVar("--color-surface-elevated"),
  text: rgbVar("--color-text"),
  muted: rgbVar("--color-muted"),
  border: rgbVar("--color-border"),
  primary: rgbVar("--color-primary"),
  "primary-hover": rgbVar("--color-primary-hover"),
  "primary-foreground": rgbVar("--color-primary-foreground"),
  secondary: rgbVar("--color-secondary"),
  "secondary-foreground": rgbVar("--color-secondary-foreground"),
  accent: rgbVar("--color-accent"),
  "accent-soft": rgbVar("--color-accent-soft"),
  "accent-foreground": rgbVar("--color-accent-foreground"),
  focus: rgbVar("--color-focus"),
  success: rgbVar("--color-success"),
  warning: rgbVar("--color-warning"),
  error: rgbVar("--color-error"),
  disabled: rgbVar("--color-disabled"),
  admin: {
    page: rgbVar("--color-admin-page"),
    surface: rgbVar("--color-admin-surface"),
    "surface-muted": rgbVar("--color-admin-surface-muted"),
    text: rgbVar("--color-admin-text"),
    muted: rgbVar("--color-admin-muted"),
    border: rgbVar("--color-admin-border"),
    primary: rgbVar("--color-admin-primary"),
    "primary-foreground": rgbVar("--color-admin-primary-foreground"),
    accent: rgbVar("--color-admin-accent"),
    focus: rgbVar("--color-admin-focus"),
  },
};

const legacyCompatibilityColors = {
  "warm-ivory": rgbVar("--color-page"),
  cream: rgbVar("--color-surface"),
  "champagne-beige": rgbVar("--color-border"),
  "dusty-pink": rgbVar("--color-accent-soft"),
  "soft-brown": rgbVar("--color-muted"),
  charcoal: rgbVar("--color-text"),
  "muted-gold": rgbVar("--color-primary"),
};

const config: Config = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx}",
    "./components/**/*.{js,ts,jsx,tsx}",
    "./lib/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        ...paletteColors,
        ...semanticColors,
        ...legacyCompatibilityColors,
      },
      fontFamily: {
        heading: ["var(--font-playfair)", "serif"],
        body: ["var(--font-inter)", "sans-serif"],
        sans: ["var(--font-inter)", "sans-serif"],
        serif: ["var(--font-playfair)", "serif"],
      },
      borderRadius: {
        brand: "8px",
        pill: "9999px",
      },
      transitionDuration: {
        fast: "150ms",
        normal: "300ms",
      },
      transitionTimingFunction: {
        brand: "cubic-bezier(0.4, 0, 0.2, 1)",
      },
      backgroundImage: {
        "brand-gradient": "linear-gradient(135deg, rgb(var(--color-page) / 1) 0%, rgb(var(--color-accent-soft) / 1) 100%)",
      },
      keyframes: {
        "badge-bounce": {
          "0%, 100%": { transform: "scale(1)" },
          "50%": { transform: "scale(1.3)" },
        },
        checkmark: {
          "0%": { transform: "scale(0)", opacity: "0" },
          "50%": { transform: "scale(1.2)", opacity: "1" },
          "100%": { transform: "scale(1)", opacity: "1" },
        },
      },
      animation: {
        "badge-bounce": "badge-bounce 300ms ease-in-out",
        checkmark: "checkmark 400ms ease-out forwards",
      },
    },
  },
  plugins: [],
};

export default config;
