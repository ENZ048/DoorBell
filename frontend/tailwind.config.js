/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        brand: {
          primary: "#ffffff",
          secondary: "#11b993",
          "secondary-dark": "#0a8e6f",
          "secondary-soft": "#d6f4eb",
          "secondary-mist": "#f1faf6",
        },
        ink: {
          950: "#0a0a0a",
          900: "#171717",
          800: "#262626",
          700: "#3f3f46",
          600: "#52525b",
          500: "#71717a",
          400: "#a1a1aa",
          300: "#d4d4d8",
          200: "#e4e4e7",
          150: "#ececef",
          100: "#f4f4f5",
          50:  "#fafafa",
        },
        bucket: {
          confirmed:  "#11b993",
          address:    "#d97706",
          reschedule: "#4f46e5",
          cancel:     "#dc2626",
          escalate:   "#ea580c",
        },
      },
      fontFamily: {
        sans: ['"Geist Sans"', "-apple-system", "BlinkMacSystemFont", "Segoe UI", "Roboto", "sans-serif"],
        mono: ['"Geist Mono"', "ui-monospace", "SFMono-Regular", "Menlo", "monospace"],
      },
      fontSize: {
        "2xs": ["0.6875rem", { lineHeight: "1rem" }],
      },
      letterSpacing: {
        tightest: "-0.04em",
      },
      boxShadow: {
        card:       "0 1px 2px 0 rgba(15, 23, 42, 0.04), 0 1px 1px 0 rgba(15, 23, 42, 0.02)",
        elevated:   "0 4px 24px -8px rgba(15, 23, 42, 0.08), 0 1px 2px 0 rgba(15, 23, 42, 0.04)",
        drawer:     "-12px 0 32px -16px rgba(15, 23, 42, 0.12), -2px 0 4px -2px rgba(15, 23, 42, 0.04)",
        "ring-brand": "0 0 0 3px rgba(17, 185, 147, 0.18)",
      },
      keyframes: {
        "fade-in": {
          "0%": { opacity: 0 },
          "100%": { opacity: 1 },
        },
        "slide-in-right": {
          "0%": { transform: "translateX(8%)", opacity: 0 },
          "100%": { transform: "translateX(0)", opacity: 1 },
        },
        "slide-in-up": {
          "0%": { transform: "translateY(8px)", opacity: 0 },
          "100%": { transform: "translateY(0)", opacity: 1 },
        },
        "pulse-dot": {
          "0%, 100%": { opacity: 1, transform: "scale(1)" },
          "50%":      { opacity: 0.45, transform: "scale(0.85)" },
        },
        flash: {
          "0%":   { backgroundColor: "rgba(17, 185, 147, 0.18)" },
          "100%": { backgroundColor: "rgba(17, 185, 147, 0)" },
        },
      },
      animation: {
        "fade-in":        "fade-in 200ms ease-out both",
        "slide-in-right": "slide-in-right 240ms cubic-bezier(0.16, 1, 0.3, 1) both",
        "slide-in-up":    "slide-in-up 240ms cubic-bezier(0.16, 1, 0.3, 1) both",
        "pulse-dot":      "pulse-dot 1.6s ease-in-out infinite",
        flash:            "flash 1200ms ease-out both",
      },
    },
  },
  plugins: [],
}
