import { useState } from "react"
import { api } from "../api"
import { useStore } from "../store"
import { BUCKET_COLOR, BUCKET_DOT, BUCKET_LABELS, PRIMARY_ACTION } from "../lib/format"
import type { Bucket, Order } from "../types"

interface Props {
  order: Order
}

export function OrderRow({ order }: Props) {
  const setDrawerOrderId = useStore((s) => s.setDrawerOrderId)
  const upsertOrder = useStore((s) => s.upsertOrder)
  const [busy, setBusy] = useState(false)

  async function onTrigger(e: React.MouseEvent) {
    e.stopPropagation()
    setBusy(true)
    try {
      const res = await api.triggerCall(order._id)
      upsertOrder({ _id: order._id, ...res } as Partial<Order> & { _id: string })
    } finally {
      setBusy(false)
    }
  }

  async function onPrimaryAction(e: React.MouseEvent) {
    e.stopPropagation()
    if (!order.bucket) return
    const a = PRIMARY_ACTION[order.bucket as Bucket]
    setBusy(true)
    try {
      const res = await api.recordAction(order._id, a.action)
      upsertOrder(res.order)
    } finally {
      setBusy(false)
    }
  }

  const bucket = order.bucket as Bucket | null

  return (
    <tr
      onClick={() => setDrawerOrderId(order._id)}
      className="cursor-pointer border-b border-neutral-100 transition-colors hover:bg-neutral-50"
    >
      <td className="px-4 py-3 text-sm">{order.order_id}</td>
      <td className="px-4 py-3 text-sm">{order.customer_name}</td>
      <td className="px-4 py-3 text-sm">
        {order.call_status === "dialing" && <span>⟳ Dialing…</span>}
        {order.call_status === "completed" && <span>✓ Completed</span>}
        {order.call_status === "pending" && <span className="text-neutral-500">— Pending</span>}
        {order.call_status === "failed" && <span className="text-red-600">✗ Failed</span>}
        {order.call_status === "no_answer" && <span className="text-neutral-500">No answer</span>}
      </td>
      <td className="px-4 py-3 text-sm">
        {bucket ? (
          <span
            className={`inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-xs font-medium ${BUCKET_COLOR[bucket]}`}
          >
            <span className={`h-1.5 w-1.5 rounded-full ${BUCKET_DOT[bucket]}`} />
            {BUCKET_LABELS[bucket]}
          </span>
        ) : (
          <span className="text-neutral-400">—</span>
        )}
      </td>
      <td className="px-4 py-3 text-right text-sm">
        {order.call_status === "pending" && (
          <button
            disabled={busy}
            onClick={onTrigger}
            className="rounded-md border border-neutral-300 px-2 py-1 text-xs hover:bg-neutral-100 disabled:opacity-50"
          >
            Trigger call
          </button>
        )}
        {bucket && order.action_state == null && (
          <button
            disabled={busy}
            onClick={onPrimaryAction}
            className="rounded-md bg-brand-secondary px-2 py-1 text-xs font-medium text-white hover:bg-brand-secondary/90 disabled:opacity-50"
          >
            {PRIMARY_ACTION[bucket].label}
          </button>
        )}
        {order.action_state && (
          <span className="text-xs text-neutral-500">✓ {order.action_state}</span>
        )}
      </td>
    </tr>
  )
}
