interface Props {
  brand: string
  onUploadClick: () => void
  onDemoClick: () => void
}

export function TopBar({ brand, onUploadClick, onDemoClick }: Props) {
  return (
    <header className="flex items-center justify-between border-b border-neutral-200 bg-brand-primary px-6 py-4">
      <div className="flex items-baseline gap-2">
        <span className="text-lg font-semibold">{brand}</span>
        <span className="text-neutral-400">•</span>
        <span className="text-sm font-medium text-neutral-600">Riya Console</span>
      </div>
      <div className="flex items-center gap-3">
        <button
          onClick={onUploadClick}
          className="rounded-md bg-brand-secondary px-3 py-1.5 text-sm font-medium text-white hover:bg-brand-secondary/90"
        >
          Upload CSV
        </button>
        <button
          onClick={onDemoClick}
          className="rounded-md border border-neutral-300 px-3 py-1.5 text-sm text-neutral-700 hover:bg-neutral-100"
        >
          ⚙ Demo ▾
        </button>
      </div>
    </header>
  )
}
