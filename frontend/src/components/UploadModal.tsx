import { useState } from "react"
import { api } from "../api"
import { useStore } from "../store"

interface Props {
  open: boolean
  onClose: () => void
}

export function UploadModal({ open, onClose }: Props) {
  const upsertOrder = useStore((s) => s.upsertOrder)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [rejected, setRejected] = useState<
    Array<{ row_number: number; reason: string }>
  >([])

  if (!open) return null

  async function handleFile(file: File) {
    setBusy(true)
    setError(null)
    setRejected([])
    try {
      const res = await api.uploadCsv(file)
      for (const o of res.inserted) upsertOrder(o)
      setRejected(res.rejected.map((r) => ({ row_number: r.row_number, reason: r.reason })))
      if (res.rejected.length === 0) onClose()
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Upload failed")
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="fixed inset-0 z-40 flex items-center justify-center bg-black/40">
      <div className="w-[480px] rounded-lg bg-brand-primary p-6 shadow-xl">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold">Upload orders CSV</h2>
          <button onClick={onClose} className="text-neutral-500 hover:text-neutral-900">
            ×
          </button>
        </div>
        <label className="block cursor-pointer rounded-md border-2 border-dashed border-neutral-300 p-8 text-center text-sm text-neutral-600 hover:border-brand-secondary">
          <input
            type="file"
            accept=".csv"
            className="hidden"
            onChange={(e) => {
              const f = e.target.files?.[0]
              if (f) void handleFile(f)
            }}
          />
          Drop a CSV here or click to browse.
        </label>
        {busy && <p className="mt-3 text-sm">Uploading…</p>}
        {error && (
          <p className="mt-3 rounded bg-red-50 p-2 text-sm text-red-700">{error}</p>
        )}
        {rejected.length > 0 && (
          <div className="mt-3 rounded bg-amber-50 p-2 text-sm text-amber-800">
            <div className="font-medium">
              {rejected.length} row{rejected.length === 1 ? "" : "s"} rejected:
            </div>
            <ul className="ml-4 list-disc">
              {rejected.map((r) => (
                <li key={r.row_number}>
                  Row {r.row_number}: {r.reason}
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </div>
  )
}
