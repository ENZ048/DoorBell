import { Upload } from "lucide-react"
import { ConnectionDot } from "./ConnectionDot"

interface Props {
  brand: string
  onUploadClick: () => void
}

export function TopBar({ brand, onUploadClick }: Props) {
  return (
    <header className="sticky top-0 z-30 border-b border-ink-200/80 bg-brand-primary/85 backdrop-blur supports-[backdrop-filter]:bg-brand-primary/70">
      <div className="mx-auto flex h-14 max-w-[1320px] items-center justify-between px-6">
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2">
            {/* Doorbell mark — chime curve in a brand tile */}
            <svg
              width="20"
              height="20"
              viewBox="0 0 20 20"
              fill="none"
              xmlns="http://www.w3.org/2000/svg"
              aria-hidden="true"
            >
              <rect width="20" height="20" rx="5" fill="#11b993" />
              <path
                d="M10 5.25c-2.21 0-3.75 1.67-3.75 3.88v1.71L5 12.62h10l-1.25-1.78V9.13c0-2.21-1.54-3.88-3.75-3.88Z"
                stroke="white"
                strokeWidth="1.4"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
              <path
                d="M8.75 13.6a1.25 1.25 0 0 0 2.5 0"
                stroke="white"
                strokeWidth="1.4"
                strokeLinecap="round"
              />
            </svg>
            <span className="text-[15px] font-semibold tracking-tightest text-ink-900">
              Doorbell
            </span>
            <span className="rounded-full bg-ink-100 px-1.5 py-0.5 text-2xs font-medium tracking-wide text-ink-500">
              v0.1
            </span>
          </div>
          <span className="h-4 w-px bg-ink-200" />
          <div className="flex items-center gap-1.5 text-[13px] text-ink-500">
            <span className="text-ink-600">{brand}</span>
            <span className="text-ink-300">/</span>
            <span className="text-ink-800">Pre-delivery operations</span>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <ConnectionDot />
          <span className="mx-1 h-4 w-px bg-ink-200" />
          <button
            onClick={onUploadClick}
            className="inline-flex h-8 items-center gap-1.5 rounded-md bg-ink-900 px-3 text-[13px] font-medium text-white shadow-card transition-all hover:bg-ink-800 active:translate-y-[0.5px]"
          >
            <Upload size={14} strokeWidth={2} />
            <span>Upload CSV</span>
          </button>
        </div>
      </div>
    </header>
  )
}
