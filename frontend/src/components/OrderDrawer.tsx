import { useEffect, useState } from "react"
import { api } from "../api"
import { useStore } from "../store"
import { BUCKET_COLOR, BUCKET_LABELS, PRIMARY_ACTION, formatINR } from "../lib/format"
import type { Bucket, Order } from "../types"

export function OrderDrawer() {
  const drawerOrderId = useStore((s) => s.drawerOrderId)
  const setDrawerOrderId = useStore((s) => s.setDrawerOrderId)
  const upsertOrder = useStore((s) => s.upsertOrder)
  const orderFromStore = useStore((s) =>
    s.drawerOrderId ? s.orders.get(s.drawerOrderId) : undefined,
  )
  const [detail, setDetail] = useState<(Order & { events: unknown[] }) | null>(null)
  const [note, setNote] = useState("")
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    if (!drawerOrderId) {
      setDetail(null)
      return
    }
    void api.getOrder(drawerOrderId).then(setDetail)
  }, [drawerOrderId])

  if (!drawerOrderId) return null
  const o = detail ?? (orderFromStore as Order | undefined)
  if (!o) {
    return (
      <aside className="fixed right-0 top-0 z-30 h-full w-[60%] overflow-y-auto border-l border-neutral-200 bg-brand-primary p-6 shadow-xl">
        Loading…
      </aside>
    )
  }

  const bucket = o.bucket as Bucket | null

  async function runAction(actionKey: string) {
    setBusy(true)
    try {
      const res = await api.recordAction(o!._id, actionKey, note || undefined)
      upsertOrder(res.order)
      setDetail({ ...(o as Order), ...res.order, events: detail?.events ?? [] })
      setNote("")
    } finally {
      setBusy(false)
    }
  }

  return (
    <aside className="fixed right-0 top-0 z-30 h-full w-[60%] overflow-y-auto border-l border-neutral-200 bg-brand-primary p-6 shadow-xl">
      <div className="flex items-start justify-between">
        <div>
          <div className="text-xs uppercase tracking-wide text-neutral-500">
            Order {o.order_id}
          </div>
          <h2 className="text-xl font-semibold">{o.customer_name}</h2>
          <p className="text-sm text-neutral-600">{o.customer_phone}</p>
        </div>
        <button
          onClick={() => setDrawerOrderId(null)}
          className="text-neutral-500 hover:text-neutral-900"
        >
          ×
        </button>
      </div>

      <section className="mt-5 grid grid-cols-2 gap-y-1 gap-x-6 text-sm">
        <div className="text-neutral-500">Product</div>
        <div>{o.product}</div>
        <div className="text-neutral-500">Slot</div>
        <div>{o.delivery_slot_label}</div>
        <div className="text-neutral-500">Address</div>
        <div>{o.address}</div>
        <div className="text-neutral-500">Payment</div>
        <div>
          {o.payment_type} {formatINR(o.amount)}
        </div>
      </section>

      {bucket && (
        <section className="mt-5">
          <div
            className={`inline-flex items-center rounded-full border px-2 py-0.5 text-xs font-medium ${BUCKET_COLOR[bucket]}`}
          >
            {BUCKET_LABELS[bucket]}
          </div>
          {o.updated_address && (
            <div className="mt-2 rounded bg-amber-50 p-2 text-sm">
              <span className="font-medium">New address: </span>
              {o.updated_address}
            </div>
          )}
          {o.reschedule_preference && (
            <div className="mt-2 rounded bg-indigo-50 p-2 text-sm">
              <span className="font-medium">Reschedule pref: </span>
              {o.reschedule_preference}
            </div>
          )}
        </section>
      )}

      {o.recording_url && (
        <section className="mt-5">
          <a
            href={o.recording_url}
            target="_blank"
            rel="noreferrer"
            className="text-sm text-brand-secondary underline"
          >
            ▶ Play recording
          </a>
        </section>
      )}

      <section className="mt-5">
        <h3 className="text-sm font-semibold text-neutral-700">Transcript</h3>
        <div className="mt-2 max-h-56 overflow-y-auto rounded border border-neutral-200 p-3 text-sm">
          {o.transcript.length === 0 && (
            <p className="text-neutral-500">No transcript yet.</p>
          )}
          {o.transcript.map((t, i) => (
            <p key={i} className="mb-1">
              <span className="font-medium">
                {t.role === "agent" ? "Riya" : t.speaker_label || o.customer_name}:{" "}
              </span>
              {t.text}
            </p>
          ))}
        </div>
      </section>

      {bucket && o.action_state == null && (
        <section className="mt-5">
          <h3 className="text-sm font-semibold text-neutral-700">Action</h3>
          <textarea
            value={note}
            onChange={(e) => setNote(e.target.value)}
            placeholder="Optional note…"
            className="mt-2 w-full rounded border border-neutral-300 p-2 text-sm"
            rows={2}
          />
          <div className="mt-2 flex flex-wrap gap-2">
            <button
              disabled={busy}
              onClick={() => runAction(PRIMARY_ACTION[bucket].action)}
              className="rounded-md bg-brand-secondary px-3 py-1.5 text-sm font-medium text-white hover:bg-brand-secondary/90 disabled:opacity-50"
            >
              {PRIMARY_ACTION[bucket].label}
            </button>
            <button
              disabled={busy}
              onClick={() => runAction("cancel_dispatch")}
              className="rounded-md border border-neutral-300 px-3 py-1.5 text-sm hover:bg-neutral-50"
            >
              Cancel dispatch
            </button>
            <button
              disabled={busy}
              onClick={() => runAction("assign_human")}
              className="rounded-md border border-neutral-300 px-3 py-1.5 text-sm hover:bg-neutral-50"
            >
              Assign human
            </button>
          </div>
        </section>
      )}

      {o.action_state && (
        <section className="mt-5">
          <div className="rounded bg-emerald-50 p-2 text-sm text-emerald-800">
            Action recorded: <span className="font-medium">{o.action_state}</span>
          </div>
        </section>
      )}
    </aside>
  )
}
