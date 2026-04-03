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
        // Night City palette
        cyber: {
          black:  "#070a0e",
          dark:   "#0d1117",
          card:   "#0f1923",
          border: "#162030",
          dim:    "#1e3050",
          yellow: "#ffe600",
          "yellow-dim": "rgba(255,230,0,0.12)",
          cyan:   "#00d4ff",
          "cyan-dim": "rgba(0,212,255,0.12)",
          pink:   "#ff003c",
          "pink-dim": "rgba(255,0,60,0.12)",
          green:  "#39ff14",
          orange: "#ff6b35",
          text:   "#dde8f0",
          muted:  "#5c7fa8",
          faint:  "#2a4060",
        },
        // keep brand alias for any leftover references
        brand: {
          50:  "#0f1923",
          100: "#162030",
          200: "#243650",
          300: "#2a4060",
          400: "#5c7fa8",
          500: "#00d4ff",
          600: "#00d4ff",
          700: "#ffe600",
          800: "#ffe600",
          900: "#fff176",
        },
      },
      fontFamily: {
        sans:    ["'Exo 2'", "ui-sans-serif", "system-ui", "sans-serif"],
        display: ["Rajdhani", "'Exo 2'", "sans-serif"],
        mono:    ["'Share Tech Mono'", "'JetBrains Mono'", "ui-monospace", "monospace"],
      },
      boxShadow: {
        "cyber-yellow": "0 0 12px rgba(255,230,0,0.35), 0 0 40px rgba(255,230,0,0.1)",
        "cyber-cyan":   "0 0 12px rgba(0,212,255,0.35), 0 0 40px rgba(0,212,255,0.1)",
        "cyber-pink":   "0 0 12px rgba(255,0,60,0.35),  0 0 40px rgba(255,0,60,0.1)",
        "cyber-green":  "0 0 12px rgba(57,255,20,0.35), 0 0 40px rgba(57,255,20,0.1)",
        "neon-border":  "inset 0 0 0 1px rgba(0,212,255,0.3), 0 0 20px rgba(0,212,255,0.08)",
      },
      backgroundImage: {
        "grid-cyber": `
          linear-gradient(rgba(0,212,255,0.04) 1px, transparent 1px),
          linear-gradient(90deg, rgba(0,212,255,0.04) 1px, transparent 1px)
        `,
        "scanlines": `repeating-linear-gradient(
          0deg,
          transparent,
          transparent 2px,
          rgba(0,212,255,0.018) 2px,
          rgba(0,212,255,0.018) 4px
        )`,
        "noise-overlay": `url("data:image/svg+xml,%3Csvg viewBox='0 0 200 200' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.85' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)' opacity='0.06'/%3E%3C/svg%3E")`,
      },
      backgroundSize: {
        "grid-40": "40px 40px",
      },
      keyframes: {
        glitch: {
          "0%,100%": { transform: "translate(0,0)", opacity: "1" },
          "10%": { transform: "translate(-2px,1px)", opacity: "0.9" },
          "20%": { transform: "translate(2px,-1px)", opacity: "0.95" },
          "30%": { transform: "translate(0,0)", opacity: "1" },
        },
        "glitch-h": {
          "0%,100%": { clipPath: "inset(0 0 100% 0)" },
          "20%": { clipPath: "inset(20% 0 60% 0)" },
          "40%": { clipPath: "inset(50% 0 30% 0)" },
          "60%": { clipPath: "inset(70% 0 10% 0)" },
          "80%": { clipPath: "inset(5% 0 85% 0)" },
        },
        "cyber-pulse": {
          "0%,100%": { opacity: "1" },
          "50%":      { opacity: "0.5" },
        },
        "scan-line": {
          "0%":   { transform: "translateY(-100%)" },
          "100%": { transform: "translateY(100vh)" },
        },
        flicker: {
          "0%,94%,100%": { opacity: "1" },
          "95%": { opacity: "0.7" },
          "97%": { opacity: "1" },
          "98%": { opacity: "0.5" },
          "99%": { opacity: "1" },
        },
        "slide-in-left": {
          "0%":   { transform: "translateX(-8px)", opacity: "0" },
          "100%": { transform: "translateX(0)",    opacity: "1" },
        },
        "data-stream": {
          "0%":   { backgroundPosition: "0% 0%" },
          "100%": { backgroundPosition: "0% 100%" },
        },
      },
      animation: {
        "glitch":        "glitch 4s infinite",
        "cyber-pulse":   "cyber-pulse 2s ease-in-out infinite",
        "scan-line":     "scan-line 3s linear infinite",
        "flicker":       "flicker 6s infinite",
        "slide-in":      "slide-in-left 0.2s ease-out",
      },
    },
  },
  plugins: [],
};

export default config;
