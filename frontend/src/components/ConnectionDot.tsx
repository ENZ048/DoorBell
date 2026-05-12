import { useStore } from "../store"

export function ConnectionDot() {
  const state = useStore((s) => s.connState)
  const dot =
    state === "connected"
      ? "bg-brand-secondary"
      : state === "reconnecting"
      ? "bg-amber-500"
      : "bg-neutral-400"
  const label =
    state === "connected"
      ? "live • connected via SSE"
      : state === "reconnecting"
      ? "reconnecting…"
      : "disconnected"
  return (
    <div className="flex items-center gap-2 text-xs text-neutral-500">
      <span className={`inline-block h-2 w-2 rounded-full ${dot}`} />
      <span>{label}</span>
    </div>
  )
}
