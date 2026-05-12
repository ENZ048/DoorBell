import { useState } from "react"
import { AlertTriangle, CheckCircle2, FileSpreadsheet, Loader2, X } from "lucide-react"
import { api } from "../api"
import { useStore } from "../store"

interface Props {
  open: boolean
  onClose: () => void
}

export function UploadModal({ open, onClose }: Props) {
  const upsertOrder = useStore((s) => s.upsertOrder)
  const [busy, setBusy] = useState(false)
  const [dragOver, setDragOver] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [rejected, setRejected] = useState<
    Array<{ row_number: number; reason: string }>
  >([])
  const [insertedCount, setInsertedCount] = useState<number | null>(null)

  if (!open) return null

  async function handleFile(file: File) {
    setBusy(true)
    setError(null)
    setRejected([])
    setInsertedCount(null)
    try {
      const res = await api.uploadCsv(file)
      for (const o of res.inserted) upsertOrder(o)
      setRejected(res.rejected.map((r) => ({ row_number: r.row_number, reason: r.reason })))
      setInsertedCount(res.inserted.length)
      if (res.rejected.length === 0) {
        setTimeout(onClose, 700)
      }
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Upload failed")
    } finally {
      setBusy(false)
    }
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-ink-950/30 backdrop-blur-[1.5px] animate-fade-in"
      onClick={onClose}
    >
      <div
        className="w-[520px] rounded-xl border border-ink-200 bg-white p-5 shadow-elevated animate-slide-in-up"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-start justify-between">
          <div>
            <div className="text-2xs font-medium uppercase tracking-[0.08em] text-ink-500">
              Bulk ingestion
            </div>
            <h2 className="mt-1 text-[17px] font-semibold tracking-tight text-ink-900">
              Upload orders CSV
            </h2>
            <p className="mt-1 text-[12.5px] text-ink-500">
              Required columns: order_id, customer_name, customer_phone, product,
              delivery_slot_label, address, pincode, payment_type, amount.
            </p>
          </div>
          <button
            onClick={onClose}
            className="inline-flex h-8 w-8 items-center justify-center rounded-md text-ink-500 hover:bg-ink-100 hover:text-ink-900"
            aria-label="Close"
          >
            <X size={16} strokeWidth={2} />
          </button>
        </div>

        <label
          onDragOver={(e) => { e.preventDefault(); setDragOver(true) }}
          onDragLeave={() => setDragOver(false)}
          onDrop={(e) => {
            e.preventDefault()
            setDragOver(false)
            const f = e.dataTransfer.files?.[0]
            if (f) void handleFile(f)
          }}
          className={
            "mt-4 flex cursor-pointer flex-col items-center justify-center rounded-lg border-2 border-dashed p-8 text-center transition-all " +
            (dragOver
              ? "border-brand-secondary bg-brand-secondary-mist/60"
              : "border-ink-200 bg-ink-50/40 hover:border-ink-300 hover:bg-ink-50")
          }
        >
          <input
            type="file"
            accept=".csv"
            className="hidden"
            onChange={(e) => {
              const f = e.target.files?.[0]
              if (f) void handleFile(f)
            }}
          />
          <span
            className={
              "mb-3 inline-flex h-10 w-10 items-center justify-center rounded-lg " +
              (dragOver
                ? "bg-brand-secondary text-white"
                : "bg-white text-ink-500 ring-1 ring-inset ring-ink-200")
            }
          >
            <FileSpreadsheet size={18} strokeWidth={1.5} />
          </span>
          <div className="text-[13.5px] font-medium text-ink-900">
            {dragOver ? "Drop to upload" : "Drag a CSV here, or click to browse"}
          </div>
          <div className="mt-1 text-2xs text-ink-500">.csv · UTF-8 · headers required</div>
        </label>

        {busy && (
          <div className="mt-3 inline-flex items-center gap-2 text-[12.5px] text-ink-600">
            <Loader2 size={12} className="animate-spin" strokeWidth={2} />
            Parsing CSV…
          </div>
        )}

        {error && (
          <div className="mt-3 flex items-start gap-2 rounded-md border border-red-200 bg-red-50 px-3 py-2 text-[12.5px] text-red-800">
            <AlertTriangle size={14} strokeWidth={2} className="mt-0.5 shrink-0" />
            <span>{error}</span>
          </div>
        )}

        {insertedCount !== null && insertedCount > 0 && rejected.length === 0 && (
          <div className="mt-3 flex items-center gap-2 rounded-md border border-brand-secondary/20 bg-brand-secondary-mist/60 px-3 py-2 text-[12.5px] text-brand-secondary-dark">
            <CheckCircle2 size={14} strokeWidth={2} />
            Imported {insertedCount} order{insertedCount === 1 ? "" : "s"}.
          </div>
        )}

        {rejected.length > 0 && (
          <div className="mt-3 rounded-md border border-amber-200 bg-amber-50 px-3 py-2 text-[12.5px] text-amber-900">
            <div className="font-medium">
              {rejected.length} row{rejected.length === 1 ? "" : "s"} rejected
              {insertedCount ? `, ${insertedCount} imported` : ""}
            </div>
            <ul className="mt-1.5 space-y-0.5 pl-1">
              {rejected.map((r) => (
                <li key={r.row_number} className="flex gap-2 leading-snug">
                  <span className="shrink-0 font-mono text-2xs text-amber-700">
                    row {r.row_number}
                  </span>
                  <span>{r.reason}</span>
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </div>
  )
}
