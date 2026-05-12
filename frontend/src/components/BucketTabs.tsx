import { useMemo } from "react"
import { useStore } from "../store"
import { BUCKET_DOT, BUCKET_LABELS } from "../lib/format"
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

  return (
    <div className="flex flex-wrap items-center gap-1 rounded-lg border border-ink-200/80 bg-white p-1 shadow-card">
      <TabButton
        active={filterBucket === null}
        onClick={() => setFilterBucket(null)}
        label="All"
        count={counts.all}
      />
      <span className="mx-1 h-4 w-px bg-ink-200" />
      {BUCKETS.map((b) => (
        <TabButton
          key={b}
          active={filterBucket === b}
          onClick={() => setFilterBucket(b)}
          label={BUCKET_LABELS[b]}
          count={counts[b] ?? 0}
          dotClass={BUCKET_DOT[b]}
        />
      ))}
    </div>
  )
}

interface TabButtonProps {
  active: boolean
  onClick: () => void
  label: string
  count: number
  dotClass?: string
}

function TabButton({ active, onClick, label, count, dotClass }: TabButtonProps) {
  return (
    <button
      onClick={onClick}
      className={
        "inline-flex h-7 items-center gap-1.5 rounded-md px-2.5 text-[12.5px] font-medium transition-colors " +
        (active
          ? "bg-ink-900 text-white"
          : "text-ink-600 hover:bg-ink-100 hover:text-ink-900")
      }
    >
      {dotClass && (
        <span className={`inline-block h-1.5 w-1.5 rounded-full ${dotClass}`} />
      )}
      <span>{label}</span>
      <span
        className={
          "tnum rounded px-1 text-2xs font-medium " +
          (active ? "bg-white/15 text-white/90" : "bg-ink-100 text-ink-500")
        }
      >
        {count}
      </span>
    </button>
  )
}
