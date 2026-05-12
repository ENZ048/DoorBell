import { api } from "./api"
import { useStore } from "./store"

let source: EventSource | null = null

export function connectStream() {
  const store = useStore.getState()
  if (source) source.close()
  store.setConnState("disconnected")
  source = new EventSource("/stream")

  source.onopen = () => {
    useStore.getState().setConnState("connected")
    // On reconnect, re-sync orders.
    void api.listOrders().then((r) => useStore.getState().setOrders(r.orders))
    void api.stats().then((s) => useStore.getState().setStats(s))
  }

  source.addEventListener("order.updated", (ev) => {
    const data = JSON.parse((ev as MessageEvent).data) as {
      snapshot: { _id: string; [k: string]: unknown }
    }
    useStore.getState().upsertOrder(data.snapshot as { _id: string })
    void api.stats().then((s) => useStore.getState().setStats(s))
  })

  source.addEventListener("orders.reset", () => {
    useStore.getState().clearOrders()
    void api.stats().then((s) => useStore.getState().setStats(s))
  })

  source.onerror = () => {
    useStore.getState().setConnState("reconnecting")
  }
}
