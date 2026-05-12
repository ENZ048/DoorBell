import { useMemo } from "react"
import { Inbox, Upload } from "lucide-react"
import { useStore } from "../store"
import { OrderRow } from "./OrderRow"

interface Props {
  onUploadClick?: () => void
}

export function OrderTable({ onUploadClick }: Props) {
  const orders = useStore((s) => s.orders)
  const filterBucket = useStore((s) => s.filterBucket)

  const allRows = useMemo(
    () =>
      Array.from(orders.values()).sort(
        (a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime(),
      ),
    [orders],
  )
  const rows = filterBucket ? allRows.filter((o) => o.bucket === filterBucket) : allRows

  if (allRows.length === 0) {
    return (
      <div className="rounded-xl border border-dashed border-ink-200 bg-white p-16 text-center shadow-card">
        <div className="mx-auto inline-flex h-11 w-11 items-center justify-center rounded-lg bg-ink-50 text-ink-500">
          <Inbox size={20} strokeWidth={1.5} />
        </div>
        <h3 className="mt-4 text-[15px] font-semibold text-ink-900">
          No orders in the queue
        </h3>
        <p className="mt-1 text-[13px] text-ink-500">
          Upload a CSV of today's out-for-delivery orders to start placing Riya calls.
        </p>
        {onUploadClick && (
          <button
            onClick={onUploadClick}
            className="mt-4 inline-flex h-8 items-center gap-1.5 rounded-md bg-ink-900 px-3 text-[13px] font-medium text-white shadow-card transition-all hover:bg-ink-800"
          >
            <Upload size={14} strokeWidth={2} />
            Upload CSV
          </button>
        )}
      </div>
    )
  }

  if (rows.length === 0) {
    return (
      <div className="rounded-xl border border-ink-200/80 bg-white p-10 text-center shadow-card">
        <h3 className="text-[14px] font-medium text-ink-900">
          No orders in this bucket yet
        </h3>
        <p className="mt-1 text-[12.5px] text-ink-500">
          Outcomes will appear here as Riya finishes calls.
        </p>
      </div>
    )
  }

  return (
    <div className="overflow-hidden rounded-xl border border-ink-200/80 bg-white shadow-card">
      <div className="flex items-center justify-between border-b border-ink-150 px-4 py-2.5">
        <div className="flex items-baseline gap-2">
          <h2 className="text-[13.5px] font-semibold text-ink-900">Orders</h2>
          <span className="text-2xs text-ink-500 tnum">
            {rows.length} of {allRows.length}
          </span>
        </div>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-left">
          <thead className="bg-ink-50/60 text-2xs uppercase tracking-[0.08em] text-ink-500">
            <tr>
              <th className="px-4 py-2.5 font-medium">Order</th>
              <th className="px-4 py-2.5 font-medium">Customer</th>
              <th className="px-4 py-2.5 font-medium">Slot</th>
              <th className="px-4 py-2.5 font-medium">Payment</th>
              <th className="px-4 py-2.5 font-medium">Status</th>
              <th className="px-4 py-2.5 font-medium">Outcome</th>
              <th className="px-4 py-2.5 text-right font-medium">Action</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((o) => (
              <OrderRow key={o._id} order={o} />
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
