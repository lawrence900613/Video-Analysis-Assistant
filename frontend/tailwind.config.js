/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        ink: {
          900: "#101827",
          950: "#08111f",
        },
        brand: {
          50: "#edf7ff",
          100: "#d7efff",
          200: "#b8e3ff",
          300: "#85d0ff",
          400: "#4cb2ff",
          500: "#176bff",
          600: "#0f55db",
          700: "#1245b0",
        },
        accent: {
          100: "#ffe4f0",
          200: "#ffc4df",
          300: "#ff93c3",
          400: "#fb6baa",
          500: "#ff2f87",
          600: "#df136b",
        },
        neon: {
          100: "#dbfbff",
          200: "#b7f5ff",
          300: "#8aecff",
          400: "#65e6ff",
          500: "#35d5ff",
          600: "#0ab7df",
        },
      },
      fontFamily: {
        sans: [
          "system-ui",
          "-apple-system",
          "Segoe UI",
          "PingFang SC",
          "Microsoft YaHei",
          "sans-serif",
        ],
      },
      keyframes: {
        "fade-up": {
          "0%": { opacity: "0", transform: "translateY(12px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
        "fade-scale": {
          "0%": { opacity: "0", transform: "translateY(16px) scale(0.98)" },
          "100%": { opacity: "1", transform: "translateY(0) scale(1)" },
        },
        float: {
          "0%,100%": { transform: "translateY(0)" },
          "50%": { transform: "translateY(-8px)" },
        },
        "slow-pulse": {
          "0%,100%": { opacity: "0.72", transform: "scale(1)" },
          "50%": { opacity: "1", transform: "scale(1.04)" },
        },
        "progress-indeterminate": {
          "0%": { transform: "translateX(-100%)" },
          "100%": { transform: "translateX(400%)" },
        },
        "typing-dot": {
          "0%, 80%, 100%": { opacity: "0.25", transform: "scale(0.85)" },
          "40%": { opacity: "1", transform: "scale(1)" },
        },
        "stream-glow": {
          "0%, 100%": { opacity: "0.6" },
          "50%": { opacity: "1" },
        },
      },
      animation: {
        "fade-up": "fade-up 0.5s ease-out both",
        "fade-scale": "fade-scale 0.65s cubic-bezier(0.16, 1, 0.3, 1) both",
        float: "float 6s ease-in-out infinite",
        "slow-pulse": "slow-pulse 5s ease-in-out infinite",
        "progress-indeterminate": "progress-indeterminate 1.4s ease-in-out infinite",
        "typing-dot": "typing-dot 1.2s ease-in-out infinite",
        "stream-glow": "stream-glow 2.5s ease-in-out infinite",
      },
      boxShadow: {
        soft: "0 20px 60px -32px rgba(8, 17, 31, 0.35)",
        glow: "0 28px 90px -42px rgba(23, 107, 255, 0.55)",
      },
    },
  },
  plugins: [],
};
