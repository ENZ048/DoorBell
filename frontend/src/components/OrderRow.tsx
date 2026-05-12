import { useState } from "react"
import {
  ArrowRight,
  CheckCircle2,
  Loader2,
  Minus,
  PhoneCall,
  PhoneOff,
} from "lucide-react"
import { api } from "../api"
import { useStore } from "../store"
import {
  ACTION_STATE_LABEL,
  BUCKET_DOT,
  BUCKET_LABELS,
  BUCKET_PILL,
  PRIMARY_ACTION,
  formatINR,
  formatRelativeTime,
} from "../lib/format"
import type { Bucket, Order } from "../types"

interface Props {
  order: Order
}

export function OrderRow({ order }: Props) {
  const setDrawerOrderId = useStore((s) => s.setDrawerOrderId)
  const upsertOrder = useStore((s) => s.upsertOrder)
  const drawerOrderId = useStore((s) => s.drawerOrderId)
  const [busy, setBusy] = useState(false)

  const isActive = drawerOrderId === order._id

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
      className={
        "group cursor-pointer border-t border-ink-100 transition-colors first:border-t-0 " +
        (isActive ? "bg-brand-secondary-mist/60" : "hover:bg-ink-50/70")
      }
    >
      {/* Order ID + relative time */}
      <td className="px-4 py-3.5 align-middle">
        <div className="flex flex-col gap-0.5">
          <span className="font-mono text-[12.5px] font-medium text-ink-900">
            {order.order_id}
          </span>
          <span className="text-2xs text-ink-500 tnum">
            {formatRelativeTime(order.created_at)}
          </span>
        </div>
      </td>

      {/* Customer */}
      <td className="px-4 py-3.5 align-middle">
        <div className="flex flex-col gap-0.5">
          <span className="text-[13.5px] font-medium text-ink-900">
            {order.customer_name}
          </span>
          <span className="font-mono text-2xs text-ink-500">{order.customer_phone}</span>
        </div>
      </td>

      {/* Slot */}
      <td className="px-4 py-3.5 align-middle">
        <span className="text-[13px] text-ink-700">{order.delivery_slot_label}</span>
      </td>

      {/* Payment */}
      <td className="px-4 py-3.5 align-middle">
        <div className="flex items-center gap-2">
          <span
            className={
              "inline-flex h-5 items-center rounded-md px-1.5 text-2xs font-medium ring-1 ring-inset " +
              (order.payment_type === "COD"
                ? "bg-amber-50 text-amber-800 ring-amber-200/70"
                : "bg-ink-50 text-ink-700 ring-ink-200")
            }
          >
            {order.payment_type}
          </span>
          <span className="text-[13px] font-medium text-ink-900 tnum">
            {formatINR(order.amount)}
          </span>
        </div>
      </td>

      {/* Status */}
      <td className="px-4 py-3.5 align-middle">
        <StatusIndicator status={order.call_status} />
      </td>

      {/* Outcome bucket */}
      <td className="px-4 py-3.5 align-middle">
        {bucket ? (
          <span
            className={`inline-flex items-center gap-1.5 rounded-full px-2 py-0.5 text-2xs font-medium ${BUCKET_PILL[bucket]}`}
          >
            <span className={`h-1.5 w-1.5 rounded-full ${BUCKET_DOT[bucket]}`} />
            {BUCKET_LABELS[bucket]}
          </span>
        ) : (
          <span className="text-2xs text-ink-400">—</span>
        )}
      </td>

      {/* Action */}
      <td className="px-4 py-3.5 align-middle">
        <div className="flex items-center justify-end gap-1">
          {order.call_status === "pending" && (
            <button
              disabled={busy}
              onClick={onTrigger}
              className="inline-flex h-7 items-center gap-1 rounded-md border border-ink-200 bg-white px-2 text-2xs font-medium text-ink-700 transition-all hover:border-ink-300 hover:bg-ink-50 disabled:cursor-wait disabled:opacity-60"
            >
              {busy ? (
                <Loader2 size={12} className="animate-spin" strokeWidth={2} />
              ) : (
                <PhoneCall size={12} strokeWidth={2} />
              )}
              <span>Call</span>
            </button>
          )}
          {bucket && order.action_state == null && (
            <button
              disabled={busy}
              onClick={onPrimaryAction}
              className="inline-flex h-7 items-center gap-1 rounded-md bg-brand-secondary px-2.5 text-2xs font-medium text-white shadow-card transition-all hover:bg-brand-secondary-dark disabled:cursor-wait disabled:opacity-60"
            >
              {busy ? (
                <Loader2 size={12} className="animate-spin" strokeWidth={2} />
              ) : null}
              <span>{PRIMARY_ACTION[bucket].label}</span>
            </button>
          )}
          {order.action_state && (
            <span className="inline-flex items-center gap-1 text-2xs text-ink-500">
              <CheckCircle2 size={12} strokeWidth={2} className="text-brand-secondary" />
              {ACTION_STATE_LABEL[order.action_state] ?? order.action_state}
            </span>
          )}
          <ArrowRight
            size={14}
            strokeWidth={1.75}
            className="ml-1 text-ink-300 opacity-0 transition-opacity group-hover:opacity-100"
          />
        </div>
      </td>
    </tr>
  )
}

function StatusIndicator({ status }: { status: Order["call_status"] }) {
  switch (status) {
    case "dialing":
      return (
        <span className="inline-flex items-center gap-1.5 text-[12.5px] font-medium text-indigo-700">
          <Loader2 size={12} strokeWidth={2.5} className="animate-spin" />
          Dialing
        </span>
      )
    case "completed":
      return (
        <span className="inline-flex items-center gap-1.5 text-[12.5px] font-medium text-ink-700">
          <CheckCircle2 size={12} strokeWidth={2.5} className="text-brand-secondary" />
          Completed
        </span>
      )
    case "pending":
      return (
        <span className="inline-flex items-center gap-1.5 text-[12.5px] text-ink-500">
          <Minus size={12} strokeWidth={2.5} />
          Pending
        </span>
      )
    case "failed":
      return (
        <span className="inline-flex items-center gap-1.5 text-[12.5px] font-medium text-red-700">
          <PhoneOff size={12} strokeWidth={2.5} />
          Failed
        </span>
      )
    case "no_answer":
      return (
        <span className="inline-flex items-center gap-1.5 text-[12.5px] text-ink-500">
          <PhoneOff size={12} strokeWidth={2.5} />
          No answer
        </span>
      )
    default:
      return <span className="text-[12.5px] text-ink-500">{status}</span>
  }
}
