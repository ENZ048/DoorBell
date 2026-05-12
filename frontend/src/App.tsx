import { useEffect, useState } from "react"
import { api } from "./api"
import { useStore } from "./store"
import { TopBar } from "./components/TopBar"
import { UploadModal } from "./components/UploadModal"
import { OrderTable } from "./components/OrderTable"
import { BucketTabs } from "./components/BucketTabs"
import { OrderDrawer } from "./components/OrderDrawer"

export default function App() {
  const setOrders = useStore((s) => s.setOrders)
  const [uploadOpen, setUploadOpen] = useState(false)

  useEffect(() => {
    void api.listOrders().then((r) => setOrders(r.orders))
  }, [setOrders])

  return (
    <div className="min-h-screen bg-brand-primary text-neutral-900 font-sans">
      <TopBar brand="Snitch" onUploadClick={() => setUploadOpen(true)} onDemoClick={() => {}} />
      <main className="px-6 py-4 space-y-4">
        <BucketTabs />
        <OrderTable />
      </main>
      <UploadModal open={uploadOpen} onClose={() => setUploadOpen(false)} />
      <OrderDrawer />
    </div>
  )
}
