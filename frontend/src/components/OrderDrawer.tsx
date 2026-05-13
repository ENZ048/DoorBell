import { useEffect, useMemo, useState } from "react"
import {
  AlertOctagon,
  CalendarClock,
  CheckCircle2,
  Loader2,
  MapPin,
  Package,
  Phone,
  Receipt,
  Sparkles,
  X,
} from "lucide-react"
import { api } from "../api"
import { useStore } from "../store"
import { AudioPlayer } from "./AudioPlayer"
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

type DrawerTab = "overview" | "transcript" | "events"

type EventEntry = {
  _id: string
  type: string
  source: string
  payload?: Record<string, unknown>
  ts: string
}

export function OrderDrawer() {
  const drawerOrderId = useStore((s) => s.drawerOrderId)
  const setDrawerOrderId = useStore((s) => s.setDrawerOrderId)
  const upsertOrder = useStore((s) => s.upsertOrder)
  const orderFromStore = useStore((s) =>
    s.drawerOrderId ? s.orders.get(s.drawerOrderId) : undefined,
  )
  const [detail, setDetail] = useState<(Order & { events: EventEntry[] }) | null>(null)
  const [tab, setTab] = useState<DrawerTab>("overview")
  const [note, setNote] = useState("")
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    if (!drawerOrderId) {
      setDetail(null)
      setTab("overview")
      return
    }
    void api.getOrder(drawerOrderId).then((d) => setDetail(d as unknown as Order & { events: EventEntry[] }))
  }, [drawerOrderId])

  if (!drawerOrderId) return null

  const o = detail ?? (orderFromStore as Order | undefined)
  const events = detail?.events ?? []

  async function runAction(actionKey: string) {
    if (!o) return
    setBusy(true)
    try {
      const res = await api.recordAction(o._id, actionKey, note || undefined)
      upsertOrder(res.order)
      setDetail({ ...(o as Order), ...res.order, events })
      setNote("")
    } finally {
      setBusy(false)
    }
  }

  return (
    <>
      {/* Backdrop */}
      <div
        onClick={() => setDrawerOrderId(null)}
        className="fixed inset-0 z-40 bg-ink-950/15 backdrop-blur-[1.5px] animate-fade-in"
      />
      {/* Drawer */}
      <aside
        className="fixed right-0 top-0 z-50 flex h-full w-full max-w-[640px] flex-col border-l border-ink-200 bg-white shadow-drawer animate-slide-in-right"
        aria-modal="true"
        role="dialog"
      >
        {!o ? (
          <DrawerSkeleton onClose={() => setDrawerOrderId(null)} />
        ) : (
          <>
            <DrawerHeader order={o} onClose={() => setDrawerOrderId(null)} />
            <TabBar
              tab={tab}
              onChange={setTab}
              transcriptCount={o.transcript?.length ?? 0}
              eventsCount={events.length}
            />
            <div className="flex-1 overflow-y-auto">
              {tab === "overview" && <OverviewTab order={o} />}
              {tab === "transcript" && <TranscriptTab order={o} />}
              {tab === "events" && <EventsTab events={events} />}
            </div>
            <DrawerFooter
              order={o}
              note={note}
              setNote={setNote}
              busy={busy}
              onAction={runAction}
            />
          </>
        )}
      </aside>
    </>
  )
}

function DrawerSkeleton({ onClose }: { onClose: () => void }) {
  return (
    <>
      <div className="flex h-14 items-center justify-between border-b border-ink-150 px-5">
        <span className="text-2xs uppercase tracking-[0.08em] text-ink-500">Loading order…</span>
        <button onClick={onClose} className="text-ink-500 hover:text-ink-900">
          <X size={16} strokeWidth={2} />
        </button>
      </div>
      <div className="flex flex-1 items-center justify-center text-ink-400">
        <Loader2 size={18} className="animate-spin" />
      </div>
    </>
  )
}

function DrawerHeader({ order, onClose }: { order: Order; onClose: () => void }) {
  const bucket = order.bucket as Bucket | null
  return (
    <header className="border-b border-ink-150 px-5 pt-4 pb-4">
      <div className="flex items-start justify-between">
        <div className="flex items-center gap-2">
          <span className="font-mono text-[12.5px] font-medium text-ink-900">
            {order.order_id}
          </span>
          <span className="text-2xs text-ink-300">·</span>
          <span className="text-2xs text-ink-500 tnum">
            opened {formatRelativeTime(order.created_at)}
          </span>
        </div>
        <button
          onClick={onClose}
          className="-mr-1 inline-flex h-7 w-7 items-center justify-center rounded-md text-ink-500 hover:bg-ink-100 hover:text-ink-900"
          aria-label="Close"
        >
          <X size={15} strokeWidth={2} />
        </button>
      </div>

      <div className="mt-2 flex items-baseline gap-3">
        <h2 className="text-[20px] font-semibold tracking-tight text-ink-900">
          {order.customer_name}
        </h2>
        <span className="font-mono text-[12.5px] text-ink-500">{order.customer_phone}</span>
      </div>

      <div className="mt-3 flex flex-wrap items-center gap-2">
        {bucket && (
          <span
            className={`inline-flex items-center gap-1.5 rounded-full px-2 py-0.5 text-2xs font-medium ${BUCKET_PILL[bucket]}`}
          >
            <span className={`h-1.5 w-1.5 rounded-full ${BUCKET_DOT[bucket]}`} />
            {BUCKET_LABELS[bucket]}
          </span>
        )}
        {order.action_state && (
          <span className="inline-flex items-center gap-1 rounded-full bg-brand-secondary-mist px-2 py-0.5 text-2xs font-medium text-brand-secondary-dark ring-1 ring-inset ring-brand-secondary/20">
            <CheckCircle2 size={11} strokeWidth={2.25} />
            {ACTION_STATE_LABEL[order.action_state] ?? order.action_state}
          </span>
        )}
        <span
          className={
            "inline-flex h-5 items-center rounded-md px-1.5 text-2xs font-medium ring-1 ring-inset " +
            (order.payment_type === "COD"
              ? "bg-amber-50 text-amber-800 ring-amber-200/70"
              : "bg-ink-50 text-ink-700 ring-ink-200")
          }
        >
          {order.payment_type} · {formatINR(order.amount)}
        </span>
      </div>
    </header>
  )
}

function TabBar({
  tab,
  onChange,
  transcriptCount,
  eventsCount,
}: {
  tab: DrawerTab
  onChange: (t: DrawerTab) => void
  transcriptCount: number
  eventsCount: number
}) {
  const tabs: Array<{ id: DrawerTab; label: string; count?: number }> = [
    { id: "overview",   label: "Overview" },
    { id: "transcript", label: "Transcript", count: transcriptCount },
    { id: "events",     label: "Events",     count: eventsCount },
  ]
  return (
    <div className="flex items-center gap-4 border-b border-ink-150 px-5">
      {tabs.map((t) => {
        const isActive = tab === t.id
        return (
          <button
            key={t.id}
            onClick={() => onChange(t.id)}
            className={
              "relative -mb-px py-2.5 text-[13px] font-medium transition-colors " +
              (isActive
                ? "text-ink-900"
                : "text-ink-500 hover:text-ink-800")
            }
          >
            <span className="inline-flex items-center gap-1.5">
              {t.label}
              {typeof t.count === "number" && (
                <span
                  className={
                    "tnum rounded px-1 text-2xs " +
                    (isActive ? "bg-ink-100 text-ink-700" : "bg-ink-100 text-ink-500")
                  }
                >
                  {t.count}
                </span>
              )}
            </span>
            <span
              className={
                "absolute inset-x-0 -bottom-px h-[2px] rounded-full transition-opacity " +
                (isActive ? "bg-ink-900 opacity-100" : "opacity-0")
              }
            />
          </button>
        )
      })}
    </div>
  )
}

function OverviewTab({ order }: { order: Order }) {
  const summary = useMemo(() => {
    const summaryValue = (order.extracted_variables as Record<string, unknown> | undefined)?.[
      "call_summary"
    ]
    return typeof summaryValue === "string" && summaryValue.trim().length > 0
      ? summaryValue
      : null
  }, [order.extracted_variables])

  return (
    <div className="space-y-6 px-5 py-5 animate-fade-in">
      {summary && (
        <section className="rounded-lg border border-brand-secondary/20 bg-brand-secondary-mist/60 p-3">
          <div className="flex items-center gap-1.5 text-2xs font-medium uppercase tracking-[0.08em] text-brand-secondary-dark">
            <Sparkles size={11} strokeWidth={2.25} />
            AI summary
          </div>
          <p className="mt-1 text-[13px] leading-relaxed text-ink-800">{summary}</p>
        </section>
      )}

      <section className="space-y-2">
        <h3 className="text-2xs font-medium uppercase tracking-[0.08em] text-ink-500">
          Order details
        </h3>
        <dl className="divide-y divide-ink-100 rounded-lg border border-ink-200 bg-white">
          <DetailRow icon={<Package size={14} strokeWidth={1.75} />} label="Product" value={order.product} />
          <DetailRow icon={<CalendarClock size={14} strokeWidth={1.75} />} label="Slot" value={order.delivery_slot_label} />
          <DetailRow icon={<MapPin size={14} strokeWidth={1.75} />} label="Address" value={order.address} mono={false} />
          <DetailRow
            icon={<Receipt size={14} strokeWidth={1.75} />}
            label="Payment"
            value={`${order.payment_type} · ${formatINR(order.amount)}`}
          />
          <DetailRow icon={<Phone size={14} strokeWidth={1.75} />} label="Phone" value={order.customer_phone} mono />
        </dl>
      </section>

      {(order.updated_address || order.reschedule_preference) && (
        <section className="space-y-2">
          <h3 className="text-2xs font-medium uppercase tracking-[0.08em] text-ink-500">
            Customer requests
          </h3>
          <div className="space-y-2">
            {order.updated_address && (
              <RequestCallout
                tone="amber"
                title="New delivery address"
                body={order.updated_address}
              />
            )}
            {order.reschedule_preference && (
              <RequestCallout
                tone="indigo"
                title="Reschedule preference"
                body={order.reschedule_preference}
              />
            )}
          </div>
        </section>
      )}

      {order.recording_url && (
        <section className="space-y-2">
          <h3 className="text-2xs font-medium uppercase tracking-[0.08em] text-ink-500">
            Call recording
          </h3>
          <AudioPlayer src={order.recording_url} />
        </section>
      )}
    </div>
  )
}

function TranscriptTab({ order }: { order: Order }) {
  const turns = order.transcript ?? []
  if (turns.length === 0) {
    return (
      <div className="px-5 py-10 text-center text-[13px] text-ink-500 animate-fade-in">
        <AlertOctagon size={16} className="mx-auto mb-2 text-ink-400" />
        No transcript captured yet. Transcripts appear after Riya finishes the call.
      </div>
    )
  }
  return (
    <div className="space-y-3 px-5 py-5 animate-fade-in">
      {turns.map((t, i) => {
        const isAgent = t.role === "agent"
        return (
          <div key={i} className={"flex " + (isAgent ? "justify-start" : "justify-end")}>
            <div
              className={
                "max-w-[80%] rounded-2xl px-3.5 py-2.5 text-[13px] leading-snug " +
                (isAgent
                  ? "bg-ink-100 text-ink-900 rounded-bl-md"
                  : "bg-brand-secondary text-white rounded-br-md")
              }
            >
              <div
                className={
                  "mb-0.5 text-2xs font-medium uppercase tracking-[0.08em] " +
                  (isAgent ? "text-ink-500" : "text-white/70")
                }
              >
                {isAgent ? "Riya" : t.speaker_label || order.customer_name}
              </div>
              <div>{t.text}</div>
            </div>
          </div>
        )
      })}
    </div>
  )
}

function EventsTab({ events }: { events: EventEntry[] }) {
  if (events.length === 0) {
    return (
      <div className="px-5 py-10 text-center text-[13px] text-ink-500 animate-fade-in">
        No events recorded yet.
      </div>
    )
  }
  return (
    <ol className="space-y-3 px-5 py-5 animate-fade-in">
      {events.map((e) => (
        <li key={e._id} className="relative pl-6">
          <span className="absolute left-1.5 top-1.5 h-1.5 w-1.5 rounded-full bg-ink-400" />
          <span className="absolute left-[8px] top-3 h-full w-px bg-ink-150 last:hidden" />
          <div className="flex items-baseline justify-between gap-3">
            <span className="text-[13px] font-medium text-ink-900">
              {humanizeEventType(e.type)}
            </span>
            <span className="text-2xs text-ink-500 tnum">
              {new Date(e.ts).toLocaleTimeString("en-IN", {
                hour: "2-digit",
                minute: "2-digit",
                second: "2-digit",
                hour12: false,
              })}
            </span>
          </div>
          <span className="text-2xs text-ink-500">{e.source}</span>
        </li>
      ))}
    </ol>
  )
}

function humanizeEventType(t: string): string {
  switch (t) {
    case "created":          return "Order ingested"
    case "call_initiated":   return "Call dispatched to Bolna"
    case "webhook_received": return "Webhook received"
    case "bucketed":         return "Outcome classified"
    case "action_taken":     return "Seller action recorded"
    case "error":            return "Error logged"
    default:                 return t
  }
}

interface DetailRowProps {
  icon: React.ReactNode
  label: string
  value: string
  mono?: boolean
}

function DetailRow({ icon, label, value, mono = false }: DetailRowProps) {
  return (
    <div className="flex items-start gap-3 px-3 py-2.5">
      <span className="mt-0.5 inline-flex h-6 w-6 items-center justify-center rounded-md bg-ink-50 text-ink-500">
        {icon}
      </span>
      <div className="min-w-0 flex-1">
        <div className="text-2xs uppercase tracking-[0.08em] text-ink-500">{label}</div>
        <div className={"mt-0.5 text-[13px] text-ink-900 " + (mono ? "font-mono" : "")}>
          {value}
        </div>
      </div>
    </div>
  )
}

function RequestCallout({
  tone,
  title,
  body,
}: {
  tone: "amber" | "indigo"
  title: string
  body: string
}) {
  const classes =
    tone === "amber"
      ? "border-amber-200/70 bg-amber-50 text-amber-900"
      : "border-indigo-200/70 bg-indigo-50 text-indigo-900"
  return (
    <div className={`rounded-lg border px-3 py-2.5 ${classes}`}>
      <div className="text-2xs font-medium uppercase tracking-[0.08em] opacity-80">
        {title}
      </div>
      <div className="mt-0.5 text-[13px] leading-relaxed">{body}</div>
    </div>
  )
}

function DrawerFooter({
  order,
  note,
  setNote,
  busy,
  onAction,
}: {
  order: Order
  note: string
  setNote: (v: string) => void
  busy: boolean
  onAction: (action: string) => void | Promise<void>
}) {
  const bucket = order.bucket as Bucket | null

  if (order.action_state) {
    return (
      <div className="border-t border-ink-150 bg-brand-secondary-mist/40 px-5 py-3">
        <div className="flex items-center gap-2 text-[13px] text-ink-700">
          <CheckCircle2 size={14} strokeWidth={2} className="text-brand-secondary" />
          <span>
            <span className="font-medium text-ink-900">
              {ACTION_STATE_LABEL[order.action_state] ?? order.action_state}
            </span>{" "}
            recorded.
          </span>
        </div>
      </div>
    )
  }

  if (!bucket) {
    return (
      <div className="border-t border-ink-150 bg-white px-5 py-3 text-2xs text-ink-500">
        Awaiting call outcome before action.
      </div>
    )
  }

  return (
    <div className="border-t border-ink-150 bg-white px-5 py-3 space-y-2">
      <textarea
        value={note}
        onChange={(e) => setNote(e.target.value)}
        placeholder="Add a note (optional)"
        className="w-full resize-none rounded-md border border-ink-200 bg-white px-2.5 py-2 text-[13px] text-ink-900 placeholder:text-ink-400 transition-colors focus:border-brand-secondary focus:outline-none focus:ring-2 focus:ring-brand-secondary/15"
        rows={2}
      />
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex flex-wrap items-center gap-1.5">
          <button
            disabled={busy}
            onClick={() => onAction("cancel_dispatch")}
            className="inline-flex h-8 items-center rounded-md border border-ink-200 bg-white px-2.5 text-[12.5px] font-medium text-ink-700 transition-all hover:border-ink-300 hover:bg-ink-50 disabled:opacity-60"
          >
            Cancel dispatch
          </button>
          <button
            disabled={busy}
            onClick={() => onAction("assign_human")}
            className="inline-flex h-8 items-center rounded-md border border-ink-200 bg-white px-2.5 text-[12.5px] font-medium text-ink-700 transition-all hover:border-ink-300 hover:bg-ink-50 disabled:opacity-60"
          >
            Assign to human
          </button>
        </div>
        <button
          disabled={busy}
          onClick={() => onAction(PRIMARY_ACTION[bucket].action)}
          className="inline-flex h-8 items-center gap-1.5 rounded-md bg-brand-secondary px-3 text-[12.5px] font-medium text-white shadow-card transition-all hover:bg-brand-secondary-dark active:translate-y-[0.5px] disabled:opacity-60"
        >
          {busy && <Loader2 size={12} className="animate-spin" strokeWidth={2} />}
          {PRIMARY_ACTION[bucket].label}
        </button>
      </div>
    </div>
  )
}
