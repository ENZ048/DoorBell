import { useEffect } from "react"
import { api } from "../api"
import { useStore } from "../store"
import { formatINR } from "../lib/format"

export function ImpactStrip() {
  const stats = useStore((s) => s.stats)
  const setStats = useStore((s) => s.setStats)
  const orders = useStore((s) => s.orders)

  useEffect(() => {
    void api.stats().then(setStats)
  }, [orders, setStats])

  if (!stats) return null
  return (
    <div className="rounded-lg border border-neutral-200 bg-brand-primary p-4 text-sm">
      <div className="font-medium text-neutral-700">Impact (today)</div>
      <div className="mt-1 flex flex-wrap gap-x-4 gap-y-1 text-neutral-700">
        <span>
          Called: <strong>{stats.called}</strong>
        </span>
        <span>
          Confirmed: <strong>{stats.confirmed_count}</strong>
        </span>
        <span>
          Issues caught early: <strong>{stats.issues_caught}</strong>
        </span>
      </div>
      <div className="mt-1 flex flex-wrap gap-x-4 text-neutral-700">
        <span>
          Est. RTO cost saved: <strong>{formatINR(stats.cost_saved)}</strong>
        </span>
        <span>
          Call spend: <strong>{formatINR(stats.call_spend)}</strong>
        </span>
        <span className={stats.net >= 0 ? "text-brand-secondary" : "text-red-700"}>
          Net: <strong>{(stats.net >= 0 ? "+" : "") + formatINR(stats.net)}</strong>
        </span>
      </div>
    </div>
  )
}
