import { useState } from "react"
import { TopBar } from "./components/TopBar"

export default function App() {
  const [uploadOpen, setUploadOpen] = useState(false)
  const [demoOpen, setDemoOpen] = useState(false)
  return (
    <div className="min-h-screen bg-brand-primary text-neutral-900 font-sans">
      <TopBar
        brand="Snitch"
        onUploadClick={() => setUploadOpen(true)}
        onDemoClick={() => setDemoOpen((v) => !v)}
      />
      <main className="px-6 py-4">
        {uploadOpen && <p className="text-sm">Upload modal placeholder</p>}
        {demoOpen && <p className="text-sm">Demo menu placeholder</p>}
      </main>
    </div>
  )
}
