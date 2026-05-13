import type { Order, Stats, UploadResponse } from "./types"

// Backend origin. Empty string in dev (Vite proxies /api, /webhook, /stream
// to localhost:8000). In prod, set VITE_API_BASE_URL=https://api.chatroute.in
// at build time and the bundle hits that origin directly.
export const API_BASE: string = (import.meta.env.VITE_API_BASE_URL ?? "").replace(/\/$/, "")

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: { ...(init?.headers || {}) },
  })
  if (!res.ok) {
    const body = await res.json().catch(() => ({}))
    throw new Error(body?.error?.message || `${res.status} ${res.statusText}`)
  }
  return (await res.json()) as T
}

export const api = {
  uploadCsv(file: File): Promise<UploadResponse> {
    const fd = new FormData()
    fd.append("file", file)
    return request<UploadResponse>("/api/orders/upload", { method: "POST", body: fd })
  },

  listOrders(filter?: { bucket?: string; call_status?: string }): Promise<{ orders: Order[] }> {
    const qs = new URLSearchParams()
    if (filter?.bucket) qs.set("bucket", filter.bucket)
    if (filter?.call_status) qs.set("call_status", filter.call_status)
    return request<{ orders: Order[] }>(`/api/orders${qs.toString() ? "?" + qs.toString() : ""}`)
  },

  getOrder(id: string): Promise<Order & { events: unknown[] }> {
    return request(`/api/orders/${id}`)
  },

  triggerCall(id: string): Promise<{ call_status: string; bolna_call_id: string }> {
    return request(`/api/orders/${id}/call`, { method: "POST" })
  },

  triggerBatch(orderIds: string[]): Promise<{ triggered: unknown[]; failed: unknown[] }> {
    return request("/api/orders/call-batch", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ order_ids: orderIds }),
    })
  },

  recordAction(
    id: string,
    action: string,
    note?: string,
  ): Promise<{ order: Order }> {
    return request(`/api/orders/${id}/action`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ action, note: note ?? null }),
    })
  },

  stats(): Promise<Stats> {
    return request<Stats>("/api/stats")
  },
}
