/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        bucket: {
          confirmed: "#10b981",
          address: "#f59e0b",
          reschedule: "#6366f1",
          cancel: "#ef4444",
          escalate: "#f97316",
        },
      },
    },
  },
  plugins: [],
}
