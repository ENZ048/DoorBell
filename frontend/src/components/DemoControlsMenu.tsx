import { useState } from "react"
import { api } from "../api"
import { useStore } from "../store"
import { BUCKET_LABELS } from "../lib/format"
import type { Bucket, Order } from "../types"

interface Props {
  open: boolean
  onClose: () => void
}

const BUCKETS: Bucket[] = ["confirmed", "address_updated", "rescheduled", "cancel_intent", "escalate"]

export function DemoControlsMenu({ open, onClose }: Props) {
  const orders = useStore((s) => s.orders)
  const clearOrders = useStore((s) => s.clearOrders)
  const [adminToken, setAdminToken] = useState(() => localStorage.getItem("adminToken") ?? "")
  const [targetId, setTargetId] = useState("")
  const [bucket, setBucket] = useState<Bucket>("address_updated")
  const [updatedAddress, setUpdatedAddress] = useState("")
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  if (!open) return null

  function saveToken(t: string) {
    setAdminToken(t)
    localStorage.setItem("adminToken", t)
  }

  async function onSimulate() {
    if (!targetId || !adminToken) {
      setError("Pick an order and provide admin token")
      return
    }
    setBusy(true)
    setError(null)
    try {
      await api.simulateOutcome(targetId, bucket, adminToken, {
        updated_address: updatedAddress || undefined,
      })
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Simulate failed")
    } finally {
      setBusy(false)
    }
  }

  async function onTriggerAll() {
    setBusy(true)
    try {
      const ids = Array.from(orders.values())
        .filter((o) => o.call_status === "pending")
        .map((o) => o._id)
      if (ids.length === 0) return
      await api.triggerBatch(ids)
    } finally {
      setBusy(false)
    }
  }

  async function onReset() {
    if (!adminToken) {
      setError("Provide admin token")
      return
    }
    setBusy(true)
    try {
      await api.reset(adminToken)
      clearOrders()
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Reset failed")
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="absolute right-6 top-16 z-40 w-[360px] rounded-md border border-neutral-200 bg-brand-primary p-4 shadow-xl">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold">Demo controls</h3>
        <button onClick={onClose} className="text-neutral-500">×</button>
      </div>
      <div className="mt-3 space-y-2 text-sm">
        <label className="block">
          Admin token
          <input
            type="password"
            value={adminToken}
            onChange={(e) => saveToken(e.target.value)}
            className="mt-1 w-full rounded border border-neutral-300 px-2 py-1 text-sm"
          />
        </label>
        <div className="border-t border-neutral-100 pt-3">
          <div className="text-xs font-medium uppercase text-neutral-500">Simulate outcome</div>
          <select
            value={targetId}
            onChange={(e) => setTargetId(e.target.value)}
            className="mt-1 w-full rounded border border-neutral-300 px-2 py-1 text-sm"
          >
            <option value="">— Pick order —</option>
            {Array.from(orders.values() as Iterable<Order>).map((o) => (
              <option key={o._id} value={o._id}>
                {o.order_id} — {o.customer_name}
              </option>
            ))}
          </select>
          <select
            value={bucket}
            onChange={(e) => setBucket(e.target.value as Bucket)}
            className="mt-1 w-full rounded border border-neutral-300 px-2 py-1 text-sm"
          >
            {BUCKETS.map((b) => (
              <option key={b} value={b}>{BUCKET_LABELS[b]}</option>
            ))}
          </select>
          {bucket === "address_updated" && (
            <input
              value={updatedAddress}
              onChange={(e) => setUpdatedAddress(e.target.value)}
              placeholder="New address (verbatim)"
              className="mt-1 w-full rounded border border-neutral-300 px-2 py-1 text-sm"
            />
          )}
          <button
            disabled={busy}
            onClick={onSimulate}
            className="mt-2 w-full rounded bg-brand-secondary px-2 py-1 text-sm text-white hover:bg-brand-secondary/90 disabled:opacity-50"
          >
            Simulate
          </button>
        </div>
        <div className="border-t border-neutral-100 pt-3 flex gap-2">
          <button
            disabled={busy}
            onClick={onTriggerAll}
            className="flex-1 rounded border border-neutral-300 px-2 py-1 text-xs hover:bg-neutral-50"
          >
            Trigger all pending
          </button>
          <button
            disabled={busy}
            onClick={onReset}
            className="flex-1 rounded border border-red-300 px-2 py-1 text-xs text-red-700 hover:bg-red-50"
          >
            Reset all
          </button>
        </div>
        {error && <div className="text-xs text-red-700">{error}</div>}
      </div>
    </div>
  )
}
