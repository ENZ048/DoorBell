import type { Bucket } from "../types"

export const BUCKET_LABELS: Record<Bucket, string> = {
  confirmed: "Confirmed",
  address_updated: "Address Updated",
  rescheduled: "Rescheduled",
  cancel_intent: "Cancel Intent",
  escalate: "Escalate",
}

export const BUCKET_COLOR: Record<Bucket, string> = {
  confirmed: "bg-emerald-100 text-emerald-800 border-emerald-300",
  address_updated: "bg-amber-100 text-amber-800 border-amber-300",
  rescheduled: "bg-indigo-100 text-indigo-800 border-indigo-300",
  cancel_intent: "bg-red-100 text-red-800 border-red-300",
  escalate: "bg-orange-100 text-orange-800 border-orange-300",
}

export const BUCKET_DOT: Record<Bucket, string> = {
  confirmed: "bg-emerald-500",
  address_updated: "bg-amber-500",
  rescheduled: "bg-indigo-500",
  cancel_intent: "bg-red-500",
  escalate: "bg-orange-500",
}

export function formatINR(amount: number): string {
  return "₹" + amount.toLocaleString("en-IN")
}

export const PRIMARY_ACTION: Record<Bucket, { action: string; label: string }> = {
  confirmed: { action: "approve_dispatch", label: "Approve Dispatch" },
  address_updated: { action: "push_new_address", label: "Push New Address" },
  rescheduled: { action: "confirm_reschedule", label: "Confirm New Slot" },
  cancel_intent: { action: "cancel_dispatch", label: "Cancel Dispatch" },
  escalate: { action: "assign_human", label: "Assign to Human" },
}
