import { useState } from "react"
import { AlertTriangle, KeyRound, Loader2, RefreshCw, Sparkles, X, Zap } from "lucide-react"
import { api } from "../api"
import { useStore } from "../store"
import { BUCKET_DOT, BUCKET_LABELS } from "../lib/format"
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
      setError("Pick an order and provide an admin token")
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
      setError("Provide an admin token first")
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
    <>
      <div
        className="fixed inset-0 z-30 animate-fade-in"
        onClick={onClose}
        aria-hidden="true"
      />
      <div className="absolute right-6 top-[60px] z-40 w-[380px] rounded-xl border border-ink-200 bg-white p-4 shadow-elevated animate-slide-in-up">
        <div className="flex items-start justify-between">
          <div>
            <div className="flex items-center gap-1.5 text-2xs font-medium uppercase tracking-[0.08em] text-brand-secondary-dark">
              <Sparkles size={11} strokeWidth={2.25} />
              Demo controls
            </div>
            <p className="mt-0.5 text-[12.5px] text-ink-500">
              Admin-only helpers for the recording. Not shipped to seller-facing users.
            </p>
          </div>
          <button
            onClick={onClose}
            className="inline-flex h-7 w-7 items-center justify-center rounded-md text-ink-500 hover:bg-ink-100 hover:text-ink-900"
            aria-label="Close"
          >
            <X size={14} strokeWidth={2} />
          </button>
        </div>

        <div className="mt-3 space-y-3">
          <Field label="Admin token" icon={<KeyRound size={11} strokeWidth={2} />}>
            <input
              type="password"
              value={adminToken}
              onChange={(e) => saveToken(e.target.value)}
              placeholder="X-Admin-Token"
              className="block w-full rounded-md border border-ink-200 bg-white px-2.5 py-1.5 text-[13px] text-ink-900 placeholder:text-ink-400 focus:border-brand-secondary focus:outline-none focus:ring-2 focus:ring-brand-secondary/15"
            />
          </Field>

          <div className="rounded-lg border border-ink-150 bg-ink-50/60 p-3">
            <div className="text-2xs font-medium uppercase tracking-[0.08em] text-ink-500">
              Simulate outcome
            </div>
            <div className="mt-2 space-y-2">
              <select
                value={targetId}
                onChange={(e) => setTargetId(e.target.value)}
                className="block w-full rounded-md border border-ink-200 bg-white px-2 py-1.5 text-[13px] text-ink-900 focus:border-brand-secondary focus:outline-none focus:ring-2 focus:ring-brand-secondary/15"
              >
                <option value="">— Pick order —</option>
                {Array.from(orders.values() as Iterable<Order>).map((o) => (
                  <option key={o._id} value={o._id}>
                    {o.order_id} — {o.customer_name}
                  </option>
                ))}
              </select>
              <div className="flex flex-wrap gap-1.5">
                {BUCKETS.map((b) => {
                  const active = bucket === b
                  return (
                    <button
                      key={b}
                      onClick={() => setBucket(b)}
                      className={
                        "inline-flex items-center gap-1.5 rounded-md border px-2 py-1 text-2xs font-medium transition-all " +
                        (active
                          ? "border-ink-900 bg-ink-900 text-white"
                          : "border-ink-200 bg-white text-ink-700 hover:border-ink-300")
                      }
                    >
                      <span className={`h-1.5 w-1.5 rounded-full ${BUCKET_DOT[b]}`} />
                      {BUCKET_LABELS[b]}
                    </button>
                  )
                })}
              </div>
              {bucket === "address_updated" && (
                <input
                  value={updatedAddress}
                  onChange={(e) => setUpdatedAddress(e.target.value)}
                  placeholder="New address (verbatim)"
                  className="block w-full rounded-md border border-ink-200 bg-white px-2.5 py-1.5 text-[13px] text-ink-900 placeholder:text-ink-400 focus:border-brand-secondary focus:outline-none focus:ring-2 focus:ring-brand-secondary/15"
                />
              )}
              <button
                disabled={busy}
                onClick={onSimulate}
                className="inline-flex h-8 w-full items-center justify-center gap-1.5 rounded-md bg-ink-900 text-[12.5px] font-medium text-white transition-all hover:bg-ink-800 disabled:opacity-60"
              >
                {busy ? (
                  <Loader2 size={12} className="animate-spin" strokeWidth={2} />
                ) : (
                  <Sparkles size={12} strokeWidth={2} />
                )}
                Inject outcome
              </button>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-2">
            <button
              disabled={busy}
              onClick={onTriggerAll}
              className="inline-flex h-8 items-center justify-center gap-1.5 rounded-md border border-ink-200 bg-white px-2 text-2xs font-medium text-ink-700 transition-all hover:border-ink-300 hover:bg-ink-50 disabled:opacity-60"
            >
              <Zap size={11} strokeWidth={2} />
              Trigger all pending
            </button>
            <button
              disabled={busy}
              onClick={onReset}
              className="inline-flex h-8 items-center justify-center gap-1.5 rounded-md border border-red-200 bg-white px-2 text-2xs font-medium text-red-700 transition-all hover:bg-red-50 disabled:opacity-60"
            >
              <RefreshCw size={11} strokeWidth={2} />
              Reset all
            </button>
          </div>

          {error && (
            <div className="flex items-start gap-2 rounded-md border border-red-200 bg-red-50 px-2.5 py-1.5 text-2xs text-red-800">
              <AlertTriangle size={12} strokeWidth={2} className="mt-0.5 shrink-0" />
              <span>{error}</span>
            </div>
          )}
        </div>
      </div>
    </>
  )
}

function Field({
  label,
  icon,
  children,
}: {
  label: string
  icon: React.ReactNode
  children: React.ReactNode
}) {
  return (
    <label className="block">
      <span className="mb-1 inline-flex items-center gap-1.5 text-2xs font-medium uppercase tracking-[0.08em] text-ink-500">
        {icon}
        {label}
      </span>
      {children}
    </label>
  )
}
