import { create } from "zustand"

import type { Order, Stats } from "./types"

interface State {
  orders: Map<string, Order>
  stats: Stats | null
  connState: "connected" | "reconnecting" | "disconnected"
  filterBucket: string | null
  drawerOrderId: string | null

  setOrders(list: Order[]): void
  upsertOrder(partial: Partial<Order> & { _id: string }): void
  removeOrder(id: string): void
  clearOrders(): void
  setStats(s: Stats): void
  setConnState(s: State["connState"]): void
  setFilterBucket(b: string | null): void
  setDrawerOrderId(id: string | null): void
}

export const useStore = create<State>((set) => ({
  orders: new Map(),
  stats: null,
  connState: "disconnected",
  filterBucket: null,
  drawerOrderId: null,

  setOrders(list) {
    const m = new Map<string, Order>()
    for (const o of list) m.set(o._id, o)
    set({ orders: m })
  },

  upsertOrder(partial) {
    set((st) => {
      const m = new Map(st.orders)
      const existing = m.get(partial._id)
      m.set(partial._id, { ...(existing ?? ({} as Order)), ...(partial as Order) })
      return { orders: m }
    })
  },

  removeOrder(id) {
    set((st) => {
      const m = new Map(st.orders)
      m.delete(id)
      return { orders: m }
    })
  },

  clearOrders() {
    set({ orders: new Map() })
  },

  setStats(s) {
    set({ stats: s })
  },

  setConnState(s) {
    set({ connState: s })
  },

  setFilterBucket(b) {
    set({ filterBucket: b })
  },

  setDrawerOrderId(id) {
    set({ drawerOrderId: id })
  },
}))
