import { useState } from "react"
import { TopBar } from "./components/TopBar"
import { UploadModal } from "./components/UploadModal"

export default function App() {
  const [uploadOpen, setUploadOpen] = useState(false)
  return (
    <div className="min-h-screen bg-brand-primary text-neutral-900 font-sans">
      <TopBar brand="Snitch" onUploadClick={() => setUploadOpen(true)} onDemoClick={() => {}} />
      <UploadModal open={uploadOpen} onClose={() => setUploadOpen(false)} />
    </div>
  )
}
