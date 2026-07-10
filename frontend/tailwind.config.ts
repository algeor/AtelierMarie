import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx}",
    "./components/**/*.{js,ts,jsx,tsx}",
    "./lib/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        "warm-ivory": "#FFFDF7",
        cream: "#FFF8F0",
        "champagne-beige": "#F5E6D3",
        "dusty-pink": "#E8C4B8",
        "soft-brown": "#7D6352",
        charcoal: "#2D2D2D",
        "muted-gold": "#C4A265",
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
        "brand-gradient": "linear-gradient(135deg, #FFFDF7 0%, #E8C4B8 100%)",
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
