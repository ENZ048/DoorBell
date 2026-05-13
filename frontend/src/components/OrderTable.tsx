import { useMemo, useState } from "react"
import { CheckCheck, Inbox, Loader2, PhoneCall, Upload, X } from "lucide-react"
import { api } from "../api"
import { useStore } from "../store"
import { PRIMARY_ACTION } from "../lib/format"
import type { Bucket, Order } from "../types"
import { OrderRow } from "./OrderRow"

interface Props {
  onUploadClick?: () => void
}

export function OrderTable({ onUploadClick }: Props) {
  const orders = useStore((s) => s.orders)
  const filterBucket = useStore((s) => s.filterBucket)
  const upsertOrder = useStore((s) => s.upsertOrder)

  const [bulkConfirming, setBulkConfirming] = useState(false)
  const [bulkBusy, setBulkBusy] = useState(false)
  const [callAllConfirming, setCallAllConfirming] = useState(false)
  const [callAllBusy, setCallAllBusy] = useState(false)

  const allRows = useMemo(
    () =>
      Array.from(orders.values()).sort(
        (a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime(),
      ),
    [orders],
  )
  const rows = filterBucket ? allRows.filter((o) => o.bucket === filterBucket) : allRows

  // Bulk-action is only offered when a specific bucket is in view and there are
  // unactioned orders. Acting on "All" would mean mixing N different actions —
  // surprising. Keep it scoped + safe.
  const bulkBucket = filterBucket as Bucket | null
  const bulkTargets = useMemo<Order[]>(
    () =>
      bulkBucket
        ? rows.filter((o) => o.bucket === bulkBucket && o.action_state == null)
        : [],
    [rows, bulkBucket],
  )

  // "Call all" — global, ignores bucket filter. Targets every pending order
  // in the queue regardless of what's currently displayed.
  const pendingTargets = useMemo<Order[]>(
    () => allRows.filter((o) => o.call_status === "pending"),
    [allRows],
  )

  async function runBulk() {
    if (!bulkBucket || bulkTargets.length === 0) return
    setBulkBusy(true)
    setBulkConfirming(false)
    const actionKey = PRIMARY_ACTION[bulkBucket].action
    try {
      const settled = await Promise.allSettled(
        bulkTargets.map((o) => api.recordAction(o._id, actionKey)),
      )
      for (const r of settled) {
        if (r.status === "fulfilled") {
          upsertOrder(r.value.order)
        }
      }
    } finally {
      setBulkBusy(false)
    }
  }

  async function runCallAll() {
    if (pendingTargets.length === 0) return
    setCallAllBusy(true)
    setCallAllConfirming(false)
    try {
      const ids = pendingTargets.map((o) => o._id)
      // Optimistic: flip each row to "dialing" immediately so the user sees
      // motion before the backend semaphore drains.
      for (const id of ids) {
        upsertOrder({ _id: id, call_status: "dialing" } as Partial<Order> & { _id: string })
      }
      await api.triggerBatch(ids)
      // The webhook + SSE stream will deliver the real state transitions.
    } finally {
      setCallAllBusy(false)
    }
  }

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
          Upload a CSV of today's out-for-delivery orders to start placing confirmation calls.
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
          Outcomes will appear here as Doorbell finishes calls.
        </p>
      </div>
    )
  }

  return (
    <div className="overflow-hidden rounded-xl border border-ink-200/80 bg-white shadow-card">
      <div className="flex items-center justify-between gap-3 border-b border-ink-150 px-4 py-2.5">
        <div className="flex items-baseline gap-2">
          <h2 className="text-[13.5px] font-semibold text-ink-900">Orders</h2>
          <span className="text-2xs text-ink-500 tnum">
            {rows.length} of {allRows.length}
          </span>
        </div>

        <div className="flex items-center gap-1.5">
          {/* Call all — global; visible whenever pending orders exist */}
          {pendingTargets.length > 0 && (
            <div className="flex items-center gap-1.5 animate-fade-in">
              {callAllConfirming ? (
                <>
                  <span className="text-2xs text-ink-600">
                    Dial{" "}
                    <span className="font-medium tnum text-ink-900">
                      {pendingTargets.length}
                    </span>{" "}
                    pending order{pendingTargets.length === 1 ? "" : "s"}?
                  </span>
                  <button
                    onClick={runCallAll}
                    disabled={callAllBusy}
                    className="inline-flex h-7 items-center gap-1 rounded-md bg-ink-900 px-2.5 text-2xs font-medium text-white shadow-card transition-all hover:bg-ink-800 disabled:opacity-60"
                  >
                    {callAllBusy && <Loader2 size={11} className="animate-spin" strokeWidth={2} />}
                    Confirm
                  </button>
                  <button
                    onClick={() => setCallAllConfirming(false)}
                    disabled={callAllBusy}
                    className="inline-flex h-7 w-7 items-center justify-center rounded-md text-ink-500 hover:bg-ink-100 hover:text-ink-900 disabled:opacity-60"
                    aria-label="Cancel"
                  >
                    <X size={13} strokeWidth={2} />
                  </button>
                </>
              ) : (
                <button
                  onClick={() => setCallAllConfirming(true)}
                  disabled={callAllBusy}
                  className="inline-flex h-7 items-center gap-1.5 rounded-md border border-ink-200 bg-white px-2.5 text-2xs font-medium text-ink-700 transition-all hover:border-ink-300 hover:bg-ink-50 disabled:opacity-60"
                >
                  <PhoneCall size={12} strokeWidth={2} />
                  Call all pending
                  <span className="tnum rounded bg-ink-100 px-1 text-[10px] text-ink-600">
                    {pendingTargets.length}
                  </span>
                </button>
              )}
            </div>
          )}

          {/* Spacer when both buttons are visible */}
          {pendingTargets.length > 0 && bulkBucket && bulkTargets.length > 0 && (
            <span className="h-4 w-px bg-ink-200" />
          )}

          {/* Bulk action — only when a single bucket is filtered AND there are unactioned rows */}
          {bulkBucket && bulkTargets.length > 0 && (
          <div className="flex items-center gap-1.5 animate-fade-in">
            {bulkConfirming ? (
              <>
                <span className="text-2xs text-ink-600">
                  Apply{" "}
                  <span className="font-medium text-ink-900">
                    {PRIMARY_ACTION[bulkBucket].label}
                  </span>{" "}
                  to{" "}
                  <span className="font-medium tnum text-ink-900">
                    {bulkTargets.length}
                  </span>{" "}
                  order{bulkTargets.length === 1 ? "" : "s"}?
                </span>
                <button
                  onClick={runBulk}
                  disabled={bulkBusy}
                  className="inline-flex h-7 items-center gap-1 rounded-md bg-brand-secondary px-2.5 text-2xs font-medium text-white shadow-card transition-all hover:bg-brand-secondary-dark disabled:opacity-60"
                >
                  {bulkBusy && <Loader2 size={11} className="animate-spin" strokeWidth={2} />}
                  Confirm
                </button>
                <button
                  onClick={() => setBulkConfirming(false)}
                  disabled={bulkBusy}
                  className="inline-flex h-7 w-7 items-center justify-center rounded-md text-ink-500 hover:bg-ink-100 hover:text-ink-900 disabled:opacity-60"
                  aria-label="Cancel"
                >
                  <X size={13} strokeWidth={2} />
                </button>
              </>
            ) : (
              <button
                onClick={() => setBulkConfirming(true)}
                disabled={bulkBusy}
                className="inline-flex h-7 items-center gap-1.5 rounded-md border border-ink-200 bg-white px-2.5 text-2xs font-medium text-ink-700 transition-all hover:border-brand-secondary/40 hover:bg-brand-secondary-mist/60 hover:text-brand-secondary-dark disabled:opacity-60"
              >
                <CheckCheck size={12} strokeWidth={2} />
                {PRIMARY_ACTION[bulkBucket].label} all
                <span className="tnum rounded bg-ink-100 px-1 text-[10px] text-ink-600">
                  {bulkTargets.length}
                </span>
              </button>
            )}
          </div>
          )}
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
