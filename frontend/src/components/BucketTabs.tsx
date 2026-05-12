import { useMemo } from "react"
import { useStore } from "../store"
import { BUCKET_LABELS } from "../lib/format"
import type { Bucket } from "../types"

const BUCKETS: Bucket[] = ["confirmed", "address_updated", "rescheduled", "cancel_intent", "escalate"]

export function BucketTabs() {
  const orders = useStore((s) => s.orders)
  const filterBucket = useStore((s) => s.filterBucket)
  const setFilterBucket = useStore((s) => s.setFilterBucket)

  const counts = useMemo(() => {
    const c: Record<string, number> = { all: 0 }
    for (const b of BUCKETS) c[b] = 0
    for (const o of orders.values()) {
      c.all += 1
      if (o.bucket) c[o.bucket] = (c[o.bucket] ?? 0) + 1
    }
    return c
  }, [orders])

  function Tab({ id, label }: { id: string | null; label: string }) {
    const isActive = filterBucket === id || (id === null && filterBucket === null)
    return (
      <button
        onClick={() => setFilterBucket(id)}
        className={
          "rounded-full border px-3 py-1 text-xs font-medium transition " +
          (isActive
            ? "border-brand-secondary bg-brand-secondary text-white"
            : "border-neutral-300 bg-brand-primary text-neutral-700 hover:bg-neutral-50")
        }
      >
        {label} {id === null ? counts.all : (counts[id] ?? 0)}
      </button>
    )
  }

  return (
    <div className="flex flex-wrap gap-2">
      <Tab id={null} label="All" />
      {BUCKETS.map((b) => (
        <Tab key={b} id={b} label={BUCKET_LABELS[b]} />
      ))}
    </div>
  )
}
