import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        cyber: {
          black:       "#F8F7F3",
          dark:        "#F0EEE9",
          card:        "#FFFFFF",
          border:      "#E4E2DA",
          dim:         "#CCCAC2",
          yellow:      "#1C1B18",
          "yellow-dim":"rgba(28,27,24,0.05)",
          cyan:        "#C3A97C",
          "cyan-dim":  "rgba(195,169,124,0.10)",
          pink:        "#BA4040",
          "pink-dim":  "rgba(186,64,64,0.06)",
          green:       "#3B7C58",
          orange:      "#C07A38",
          text:        "#1C1B18",
          muted:       "#706D66",
          faint:       "#B4B1AA",
        },
        brand: {
          50:  "#FFFFFF",
          100: "#F0EEE9",
          200: "#E4E2DA",
          300: "#B4B1AA",
          400: "#706D66",
          500: "#C3A97C",
          600: "#C3A97C",
          700: "#1C1B18",
          800: "#1C1B18",
          900: "#0D0C0A",
        },
      },
      fontFamily: {
        sans:    ["'Manrope'",          "ui-sans-serif",  "system-ui", "sans-serif"],
        display: ["'Playfair Display'", "Georgia",        "serif"],
        mono:    ["'JetBrains Mono'",   "ui-monospace",   "monospace"],
      },
      boxShadow: {
        "cyber-yellow": "0 4px 20px rgba(28,27,24,0.10), 0 1px 4px rgba(28,27,24,0.06)",
        "cyber-cyan":   "0 4px 20px rgba(195,169,124,0.18), 0 1px 4px rgba(28,27,24,0.05)",
        "cyber-pink":   "0 4px 20px rgba(186,64,64,0.10), 0 1px 4px rgba(186,64,64,0.06)",
        "cyber-green":  "0 4px 20px rgba(59,124,88,0.10), 0 1px 4px rgba(59,124,88,0.06)",
        "neon-border":  "inset 0 0 0 1px rgba(195,169,124,0.25), 0 2px 12px rgba(28,27,24,0.06)",
        "card-hover":   "0 8px 30px rgba(28,27,24,0.09), 0 2px 8px rgba(28,27,24,0.05)",
      },
      backgroundImage: {
        "grid-cyber": `
          linear-gradient(rgba(28,27,24,0.03) 1px, transparent 1px),
          linear-gradient(90deg, rgba(28,27,24,0.03) 1px, transparent 1px)
        `,
      },
      backgroundSize: {
        "grid-40": "40px 40px",
      },
      keyframes: {
        "cyber-pulse": {
          "0%,100%": { opacity: "1" },
          "50%":      { opacity: "0.45" },
        },
        "fade-up": {
          "0%":   { opacity: "0", transform: "translateY(10px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
        "slide-in-left": {
          "0%":   { transform: "translateX(-8px)", opacity: "0" },
          "100%": { transform: "translateX(0)",    opacity: "1" },
        },
      },
      animation: {
        "cyber-pulse": "cyber-pulse 2s ease-in-out infinite",
        "fade-up":     "fade-up 0.4s ease-out both",
        "slide-in":    "slide-in-left 0.2s ease-out",
      },
    },
  },
  plugins: [],
};

export default config;
