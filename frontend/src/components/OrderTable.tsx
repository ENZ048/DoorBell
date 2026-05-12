import { useMemo } from "react"
import { useStore } from "../store"
import { OrderRow } from "./OrderRow"

export function OrderTable() {
  const orders = useStore((s) => s.orders)
  const filterBucket = useStore((s) => s.filterBucket)

  const rows = useMemo(() => {
    const arr = Array.from(orders.values()).sort(
      (a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime(),
    )
    if (!filterBucket) return arr
    return arr.filter((o) => o.bucket === filterBucket)
  }, [orders, filterBucket])

  if (rows.length === 0) {
    return (
      <div className="rounded-lg border border-dashed border-neutral-300 bg-brand-primary p-12 text-center text-sm text-neutral-500">
        No orders yet. Upload a CSV to get started.
      </div>
    )
  }

  return (
    <div className="overflow-hidden rounded-lg border border-neutral-200 bg-brand-primary">
      <table className="w-full text-left">
        <thead className="bg-neutral-50 text-xs uppercase tracking-wide text-neutral-500">
          <tr>
            <th className="px-4 py-2">Order</th>
            <th className="px-4 py-2">Customer</th>
            <th className="px-4 py-2">Status</th>
            <th className="px-4 py-2">Outcome</th>
            <th className="px-4 py-2 text-right">Action</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((o) => (
            <OrderRow key={o._id} order={o} />
          ))}
        </tbody>
      </table>
    </div>
  )
}
