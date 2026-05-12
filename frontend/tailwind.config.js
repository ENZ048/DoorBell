/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        brand: {
          primary: "#ffffff",
          secondary: "#11b993",
        },
        bucket: {
          confirmed: "#10b981",
          address: "#f59e0b",
          reschedule: "#6366f1",
          cancel: "#ef4444",
          escalate: "#f97316",
        },
      },
      fontFamily: {
        sans: ['"Geist Sans"', "-apple-system", "BlinkMacSystemFont", "Segoe UI", "Roboto", "sans-serif"],
      },
    },
  },
  plugins: [],
}
