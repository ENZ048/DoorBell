import { useEffect, useRef, useState } from "react"
import { Download, Pause, Play, Volume2, VolumeX } from "lucide-react"

interface Props {
  src: string
  downloadHref?: string
  downloadFilename?: string
}

function fmt(s: number): string {
  if (!isFinite(s) || s < 0) return "0:00"
  const m = Math.floor(s / 60)
  const r = Math.floor(s % 60)
  return `${m}:${r.toString().padStart(2, "0")}`
}

export function AudioPlayer({ src, downloadHref, downloadFilename }: Props) {
  const audioRef = useRef<HTMLAudioElement | null>(null)
  const barRef = useRef<HTMLDivElement | null>(null)
  const [playing, setPlaying] = useState(false)
  const [muted, setMuted] = useState(false)
  const [current, setCurrent] = useState(0)
  const [duration, setDuration] = useState(0)
  const [loaded, setLoaded] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const a = audioRef.current
    if (!a) return
    const onTime = () => setCurrent(a.currentTime)
    const onMeta = () => {
      setDuration(a.duration)
      setLoaded(true)
    }
    const onEnd = () => setPlaying(false)
    const onErr = () => setError("Recording unavailable")
    a.addEventListener("timeupdate", onTime)
    a.addEventListener("loadedmetadata", onMeta)
    a.addEventListener("ended", onEnd)
    a.addEventListener("error", onErr)
    return () => {
      a.removeEventListener("timeupdate", onTime)
      a.removeEventListener("loadedmetadata", onMeta)
      a.removeEventListener("ended", onEnd)
      a.removeEventListener("error", onErr)
    }
  }, [src])

  function toggle() {
    const a = audioRef.current
    if (!a) return
    if (playing) {
      a.pause()
      setPlaying(false)
    } else {
      void a.play().then(() => setPlaying(true)).catch(() => setError("Cannot play"))
    }
  }

  function toggleMute() {
    const a = audioRef.current
    if (!a) return
    a.muted = !a.muted
    setMuted(a.muted)
  }

  function seek(e: React.MouseEvent<HTMLDivElement>) {
    const bar = barRef.current
    const a = audioRef.current
    if (!bar || !a || !duration) return
    const rect = bar.getBoundingClientRect()
    const ratio = Math.max(0, Math.min(1, (e.clientX - rect.left) / rect.width))
    a.currentTime = ratio * duration
    setCurrent(a.currentTime)
  }

  const pct = duration > 0 ? (current / duration) * 100 : 0

  return (
    <div className="flex items-center gap-3 rounded-lg border border-ink-200 bg-white px-3 py-2.5">
      <audio ref={audioRef} src={src} preload="metadata" />
      <button
        onClick={toggle}
        disabled={!!error}
        aria-label={playing ? "Pause" : "Play"}
        className="inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-brand-secondary text-white shadow-card transition-all hover:bg-brand-secondary-dark active:translate-y-[0.5px] disabled:cursor-not-allowed disabled:bg-ink-300"
      >
        {playing ? (
          <Pause size={14} strokeWidth={2.5} fill="currentColor" />
        ) : (
          <Play size={14} strokeWidth={2.5} fill="currentColor" className="ml-0.5" />
        )}
      </button>

      <span className="font-mono text-2xs text-ink-600 tnum w-9 shrink-0">
        {fmt(current)}
      </span>

      <div
        ref={barRef}
        onClick={seek}
        className="relative h-1.5 flex-1 cursor-pointer overflow-hidden rounded-full bg-ink-150"
        role="slider"
        aria-valuenow={Math.round(pct)}
        aria-valuemin={0}
        aria-valuemax={100}
      >
        <div
          className="absolute inset-y-0 left-0 rounded-full bg-brand-secondary transition-[width] duration-100 ease-linear"
          style={{ width: `${pct}%` }}
        />
      </div>

      <span className="font-mono text-2xs text-ink-500 tnum w-9 shrink-0 text-right">
        {loaded ? fmt(duration) : "—:—"}
      </span>

      <button
        onClick={toggleMute}
        aria-label={muted ? "Unmute" : "Mute"}
        className="inline-flex h-7 w-7 shrink-0 items-center justify-center rounded-md text-ink-500 hover:bg-ink-100 hover:text-ink-900"
      >
        {muted ? <VolumeX size={14} strokeWidth={2} /> : <Volume2 size={14} strokeWidth={2} />}
      </button>

      {downloadHref && (
        <a
          href={downloadHref}
          download={downloadFilename || true}
          aria-label="Download recording"
          title="Download recording"
          className="inline-flex h-7 w-7 shrink-0 items-center justify-center rounded-md text-ink-500 hover:bg-ink-100 hover:text-ink-900"
        >
          <Download size={14} strokeWidth={2} />
        </a>
      )}

      {error && (
        <span className="text-2xs text-red-600 ml-2">{error}</span>
      )}
    </div>
  )
}
