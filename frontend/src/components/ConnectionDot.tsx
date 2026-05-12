import { useStore } from "../store"

export function ConnectionDot() {
  const state = useStore((s) => s.connState)

  const meta =
    state === "connected"
      ? { ring: "ring-brand-secondary/40", dot: "bg-brand-secondary", text: "Live",         pulse: true }
      : state === "reconnecting"
      ? { ring: "ring-amber-300/60",       dot: "bg-amber-500",       text: "Reconnecting", pulse: true }
      : { ring: "ring-ink-200",            dot: "bg-ink-400",         text: "Offline",      pulse: false }

  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full bg-white px-2 py-1 text-2xs font-medium text-ink-700 ring-1 ring-inset ${meta.ring}`}
      title={`SSE: ${state}`}
    >
      <span className="relative inline-flex h-1.5 w-1.5">
        {meta.pulse && (
          <span className={`absolute inline-flex h-full w-full rounded-full opacity-60 ${meta.dot} animate-pulse-dot`} />
        )}
        <span className={`relative inline-flex h-1.5 w-1.5 rounded-full ${meta.dot}`} />
      </span>
      <span className="tracking-wide">{meta.text}</span>
    </span>
  )
}
