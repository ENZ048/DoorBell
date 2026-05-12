import { useEffect, useState } from "react"
import { api } from "./api"
import { useStore } from "./store"
import { TopBar } from "./components/TopBar"
import { UploadModal } from "./components/UploadModal"
import { OrderTable } from "./components/OrderTable"
import { BucketTabs } from "./components/BucketTabs"
import { OrderDrawer } from "./components/OrderDrawer"
import { ImpactStrip } from "./components/ImpactStrip"
import { connectStream } from "./sse"
import { ConnectionDot } from "./components/ConnectionDot"
import { DemoControlsMenu } from "./components/DemoControlsMenu"

export default function App() {
  const setOrders = useStore((s) => s.setOrders)
  const [uploadOpen, setUploadOpen] = useState(false)
  const [demoOpen, setDemoOpen] = useState(false)

  useEffect(() => {
    void api.listOrders().then((r) => setOrders(r.orders))
  }, [setOrders])

  useEffect(() => { connectStream() }, [])

  return (
    <div className="min-h-screen bg-brand-primary text-neutral-900 font-sans">
      <TopBar brand="Snitch" onUploadClick={() => setUploadOpen(true)} onDemoClick={() => setDemoOpen((v) => !v)} />
      <main className="px-6 py-4 space-y-4">
        <ImpactStrip />
        <BucketTabs />
        <OrderTable />
        <div className="pt-2">
          <ConnectionDot />
        </div>
      </main>
      <UploadModal open={uploadOpen} onClose={() => setUploadOpen(false)} />
      <DemoControlsMenu open={demoOpen} onClose={() => setDemoOpen(false)} />
      <OrderDrawer />
    </div>
  )
}
