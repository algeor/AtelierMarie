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
        heading: ["var(--font-heading)", "serif"],
        body: ["var(--font-body)", "sans-serif"],
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
    },
  },
  plugins: [],
};

export default config;