import type { Bucket } from "../types"

export const BUCKET_LABELS: Record<Bucket, string> = {
  confirmed:       "Confirmed",
  address_updated: "Address updated",
  rescheduled:     "Rescheduled",
  cancel_intent:   "Cancel intent",
  escalate:        "Escalate",
}

// Subtle pill — neutral surface + colored dot. Linear/Vercel style.
export const BUCKET_PILL: Record<Bucket, string> = {
  confirmed:       "bg-brand-secondary-mist text-emerald-800 ring-1 ring-inset ring-emerald-200/70",
  address_updated: "bg-amber-50          text-amber-800   ring-1 ring-inset ring-amber-200/70",
  rescheduled:     "bg-indigo-50         text-indigo-800  ring-1 ring-inset ring-indigo-200/70",
  cancel_intent:   "bg-red-50            text-red-800     ring-1 ring-inset ring-red-200/70",
  escalate:        "bg-orange-50         text-orange-800  ring-1 ring-inset ring-orange-200/70",
}

export const BUCKET_DOT: Record<Bucket, string> = {
  confirmed:       "bg-bucket-confirmed",
  address_updated: "bg-bucket-address",
  rescheduled:     "bg-bucket-reschedule",
  cancel_intent:   "bg-bucket-cancel",
  escalate:        "bg-bucket-escalate",
}

export function formatINR(amount: number): string {
  return "₹" + amount.toLocaleString("en-IN")
}

export function formatRelativeTime(iso: string): string {
  const d = new Date(iso)
  const diff = Date.now() - d.getTime()
  const sec = Math.floor(diff / 1000)
  if (sec < 60) return `${Math.max(sec, 1)}s ago`
  const min = Math.floor(sec / 60)
  if (min < 60) return `${min}m ago`
  const hr = Math.floor(min / 60)
  if (hr < 24) return `${hr}h ago`
  const day = Math.floor(hr / 24)
  return `${day}d ago`
}

export const PRIMARY_ACTION: Record<Bucket, { action: string; label: string }> = {
  confirmed:       { action: "approve_dispatch",   label: "Approve dispatch" },
  address_updated: { action: "push_new_address",   label: "Push new address" },
  rescheduled:     { action: "confirm_reschedule", label: "Confirm new slot" },
  cancel_intent:   { action: "cancel_dispatch",    label: "Cancel dispatch" },
  escalate:        { action: "assign_human",       label: "Assign to human" },
}

// Short action verb labels (drawer secondary buttons)
export const ACTION_LABEL: Record<string, string> = {
  approve_dispatch:   "Approve dispatch",
  cancel_dispatch:    "Cancel dispatch",
  push_new_address:   "Push new address",
  confirm_reschedule: "Confirm new slot",
  assign_human:       "Assign to human",
}

// Human-readable resolution state (what we show after a seller acts)
export const ACTION_STATE_LABEL: Record<string, string> = {
  dispatched:            "Dispatched",
  cancelled:             "Cancelled",
  rescheduled_confirmed: "Reschedule confirmed",
  address_pushed:        "Address pushed",
  human_assigned:        "Assigned to human",
}

export const CALL_STATUS_LABEL: Record<string, string> = {
  pending:   "Pending",
  dialing:   "Dialing",
  completed: "Completed",
  failed:    "Failed",
  no_answer: "No answer",
}
