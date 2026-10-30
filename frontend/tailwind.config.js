import animate from "tailwindcss-animate";

/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        paper: {
          DEFAULT: "#F7F5F1",
          deep: "#EFEAE2",
          card: "#FFFFFF",
        },
        ink: {
          DEFAULT: "#16191C",
          muted: "#5A5F66",
          faint: "#8A8F96",
          invert: "#FAFAF8",
        },
        pine: {
          DEFAULT: "#0F4C45",
          deep: "#0B3A34",
          wash: "#E7F0EE",
        },
        line: "#E4DED3",
        flag: {
          good: "#1F7A4D",
          warn: "#B4700B",
          bad: "#B42318",
          info: "#1D4ED8",
        },
      },
      fontFamily: {
        sans: [
          "ui-sans-serif",
          "system-ui",
          "-apple-system",
          "Segoe UI",
          "Roboto",
          "Helvetica Neue",
          "Arial",
          "sans-serif",
        ],
        mono: ["ui-monospace", "SFMono-Regular", "JetBrains Mono", "Menlo", "Consolas", "monospace"],
      },
      boxShadow: {
        card: "0 1px 0 0 rgba(22, 25, 28, 0.04)",
        lift: "0 18px 40px -28px rgba(15, 76, 69, 0.45)",
      },
      keyframes: {
        "fade-up": {
          "0%": { opacity: "0", transform: "translateY(6px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
        "rule-in": {
          "0%": { transform: "scaleX(0)" },
          "100%": { transform: "scaleX(1)" },
        },
      },
      animation: {
        "fade-up": "fade-up 220ms ease-out both",
        "rule-in": "rule-in 260ms ease-out both",
      },
    },
  },
  plugins: [animate],
};
