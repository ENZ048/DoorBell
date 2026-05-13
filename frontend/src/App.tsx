import { useEffect, useState } from "react"
import { Activity } from "lucide-react"
import { api } from "./api"
import { useStore } from "./store"
import { TopBar } from "./components/TopBar"
import { UploadModal } from "./components/UploadModal"
import { OrderTable } from "./components/OrderTable"
import { BucketTabs } from "./components/BucketTabs"
import { OrderDrawer } from "./components/OrderDrawer"
import { ImpactStrip } from "./components/ImpactStrip"
import { connectStream } from "./sse"
import { DemoControlsMenu } from "./components/DemoControlsMenu"

export default function App() {
  const setOrders = useStore((s) => s.setOrders)
  const [uploadOpen, setUploadOpen] = useState(false)
  const [demoOpen, setDemoOpen] = useState(false)

  useEffect(() => {
    void api.listOrders().then((r) => setOrders(r.orders))
  }, [setOrders])

  useEffect(() => {
    connectStream()
  }, [])

  return (
    <div className="relative min-h-screen page-wash font-sans text-ink-900">
      <TopBar
        brand="Snitch"
        onUploadClick={() => setUploadOpen(true)}
        onDemoClick={() => setDemoOpen((v) => !v)}
      />

      <main className="mx-auto max-w-[1320px] px-6 pb-16">
        {/* Hero band */}
        <section className="relative isolate overflow-hidden pt-8">
          <div className="bg-grid-soft pointer-events-none absolute inset-0 -z-10 opacity-70" />
          <div className="flex flex-col gap-1">
            <div className="inline-flex items-center gap-1.5 text-2xs font-medium uppercase tracking-[0.1em] text-brand-secondary-dark">
              <Activity size={11} strokeWidth={2.25} />
              Pre-delivery confirmation
            </div>
            <h1 className="text-[26px] font-semibold tracking-tightest text-ink-900">
              Today's delivery queue
            </h1>
            <p className="max-w-[640px] text-[13.5px] text-ink-600">
              Every out-for-delivery order gets a quick confirmation call before
              dispatch — address, availability, and COD intent — so RTO is caught
              before the courier leaves the hub.
            </p>
          </div>

          <div className="mt-6">
            <ImpactStrip />
          </div>
        </section>

        {/* Filters */}
        <section className="mt-6">
          <BucketTabs />
        </section>

        {/* Orders table */}
        <section className="mt-3">
          <OrderTable onUploadClick={() => setUploadOpen(true)} />
        </section>

        {/* Footer signature */}
        <footer className="mt-10 flex items-center justify-between text-2xs text-ink-400">
          <span>Doorbell · Pre-delivery RTO control · v0.1</span>
          <span className="font-mono">snitch.example.com</span>
        </footer>
      </main>

      <UploadModal open={uploadOpen} onClose={() => setUploadOpen(false)} />
      <DemoControlsMenu open={demoOpen} onClose={() => setDemoOpen(false)} />
      <OrderDrawer />
    </div>
  )
}
