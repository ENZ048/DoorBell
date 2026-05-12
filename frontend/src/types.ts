export type CallStatus = "pending" | "dialing" | "completed" | "failed" | "no_answer"
export type Bucket = "confirmed" | "address_updated" | "rescheduled" | "cancel_intent" | "escalate"
export type ActionState =
  | "dispatched"
  | "cancelled"
  | "rescheduled_confirmed"
  | "address_pushed"
  | "human_assigned"

export interface TranscriptTurn {
  role: string
  speaker_label?: string
  text: string
  ts?: string
}

export interface SellerAction {
  action: string
  note?: string | null
  by: string
  ts: string
}

export interface Order {
  _id: string
  order_id: string
  customer_name: string
  customer_phone: string
  product: string
  delivery_slot_label: string
  address: string
  pincode: string
  payment_type: "COD" | "PREPAID"
  amount: number
  call_status: CallStatus
  bolna_call_id?: string | null
  bucket?: Bucket | null
  action_state?: ActionState | null
  transcript: TranscriptTurn[]
  recording_url?: string | null
  extracted_variables: Record<string, unknown>
  updated_address?: string | null
  reschedule_preference?: string | null
  actions: SellerAction[]
  created_at: string
  updated_at: string
}

export interface UploadResponse {
  inserted: Order[]
  rejected: Array<{ row_number: number; raw: Record<string, string>; reason: string }>
  total_parsed: number
}

export interface Stats {
  called: number
  confirmed_count: number
  address_updated_count: number
  rescheduled_count: number
  cancel_intent_count: number
  escalate_count: number
  issues_caught: number
  cost_saved: number
  call_spend: number
  net: number
}

export interface OrderUpdatedEvent {
  event: "order.updated"
  snapshot: Partial<Order> & { _id: string }
}
