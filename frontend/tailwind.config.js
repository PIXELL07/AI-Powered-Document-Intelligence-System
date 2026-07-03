/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        paper: "#F6F3EC",
        surface: "#FFFFFF",
        ink: "#1C1F26",
        inkfaint: "#6B7280",
        ledger: "#1F3A5F",
        ledgerlight: "#3E5C80",
        critical: "#AA2B22",
        warn: "#9A6B12",
        info: "#3B6E8F",
        ok: "#2F6F4F",
        hairline: "#DDD6C8",
      },
      fontFamily: {
        display: ["'Source Serif 4'", "Georgia", "serif"],
        body: ["Inter", "system-ui", "sans-serif"],
        mono: ["'IBM Plex Mono'", "monospace"],
      },
    },
  },
  plugins: [],
};
