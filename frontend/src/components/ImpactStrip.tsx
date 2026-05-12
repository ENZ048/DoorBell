import { useEffect } from "react"
import { ArrowUpRight, IndianRupee, PhoneCall, ShieldAlert, ShieldCheck } from "lucide-react"
import { api } from "../api"
import { useStore } from "../store"
import { formatINR } from "../lib/format"

interface KpiProps {
  label: string
  value: React.ReactNode
  hint?: string
  icon: React.ReactNode
  tone?: "default" | "positive" | "negative"
  highlight?: boolean
}

function Kpi({ label, value, hint, icon, tone = "default", highlight = false }: KpiProps) {
  const valueTone =
    tone === "positive" ? "text-brand-secondary-dark"
    : tone === "negative" ? "text-red-600"
    : "text-ink-900"

  return (
    <div
      className={
        "group relative flex flex-col rounded-xl border bg-white p-4 shadow-card transition-all " +
        (highlight
          ? "border-brand-secondary/40 ring-1 ring-brand-secondary/10"
          : "border-ink-200/80 hover:border-ink-300")
      }
    >
      <div className="flex items-center justify-between text-ink-500">
        <span className="text-2xs font-medium uppercase tracking-[0.08em]">
          {label}
        </span>
        <span
          className={
            "inline-flex h-7 w-7 items-center justify-center rounded-md " +
            (highlight ? "bg-brand-secondary-mist text-brand-secondary-dark" : "bg-ink-50 text-ink-500")
          }
        >
          {icon}
        </span>
      </div>
      <div className={`mt-3 text-[28px] font-semibold leading-none tracking-tightest tnum ${valueTone}`}>
        {value}
      </div>
      {hint && (
        <div className="mt-2 text-[12px] text-ink-500">{hint}</div>
      )}
    </div>
  )
}

export function ImpactStrip() {
  const stats = useStore((s) => s.stats)
  const setStats = useStore((s) => s.setStats)
  const orders = useStore((s) => s.orders)

  useEffect(() => {
    void api.stats().then(setStats)
  }, [orders, setStats])

  const called = stats?.called ?? 0
  const confirmed = stats?.confirmed_count ?? 0
  const issues = stats?.issues_caught ?? 0
  const costSaved = stats?.cost_saved ?? 0
  const callSpend = stats?.call_spend ?? 0
  const net = stats?.net ?? 0

  const confirmRate = called > 0 ? Math.round((confirmed / called) * 100) : 0
  const issuePct = called > 0 ? Math.round((issues / called) * 100) : 0
  const roiMultiple = callSpend > 0 ? (costSaved / callSpend).toFixed(1) : "—"

  return (
    <section className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">
      <Kpi
        label="Calls today"
        value={called}
        hint={called > 0 ? `${callSpend ? formatINR(callSpend) : "—"} call spend` : "Awaiting first dispatch"}
        icon={<PhoneCall size={14} strokeWidth={1.75} />}
      />
      <Kpi
        label="Confirmed"
        value={confirmed}
        hint={called > 0 ? `${confirmRate}% confirm rate` : "—"}
        icon={<ShieldCheck size={14} strokeWidth={1.75} />}
      />
      <Kpi
        label="Issues caught early"
        value={issues}
        hint={called > 0 ? `${issuePct}% of called orders` : "—"}
        icon={<ShieldAlert size={14} strokeWidth={1.75} />}
      />
      <Kpi
        label="Net saved"
        value={
          <span className="inline-flex items-baseline gap-1.5">
            <span>{(net >= 0 ? "+" : "") + formatINR(net)}</span>
            {net >= 0 && callSpend > 0 && (
              <span className="text-xs font-medium text-ink-500 tracking-normal">
                <ArrowUpRight size={12} strokeWidth={2} className="mb-0.5 inline" /> {roiMultiple}× ROI
              </span>
            )}
          </span>
        }
        hint={
          called > 0
            ? `${formatINR(costSaved)} RTO cost averted`
            : "ROI accrues as outcomes land"
        }
        icon={<IndianRupee size={14} strokeWidth={1.75} />}
        tone={net >= 0 ? "positive" : "negative"}
        highlight={net > 0}
      />
    </section>
  )
}
