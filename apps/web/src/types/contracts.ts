// ─── Core domain types ───────────────────────────────────────────────────────
// These mirror the backend canonical model defined in packages/contracts.
// Update here when the backend contract changes.

export type ProductStatus =
  | 'draft'
  | 'approved'
  | 'publishing'
  | 'shopify_draft'
  | 'live'
  | 'failed'
  | 'publish_failed'
  | 'paused'
  | 'rejected'

export type ListingStatus =
  | 'draft'
  | 'queued'
  | 'publishing'
  | 'live'
  | 'failed'
  | 'paused'
  | 'blocked'

export type IngestionStatus =
  | 'pending'
  | 'processing'
  | 'completed'
  | 'failed'

export type ActionStatus =
  | 'proposed'
  | 'awaiting_approval'
  | 'approved'
  | 'rejected'
  | 'cancelled'
  | 'executed'
  | 'failed'

export type Channel = 'shopify' | 'ondc' | 'meesho' | 'amazon'

// ─── Product / Catalogue ─────────────────────────────────────────────────────

export interface MissingField {
  field: string
  reason: string
}

export interface ProductVariantWeb {
  id: string
  sku: string
  title: string
  price_inr: number | null
  inventory_item_id: string | null
  stock_on_hand: number
}

export interface Product {
  id: string
  store_id: string
  status: ProductStatus
  version: number
  title: string
  description: string | null
  price_inr: number | null
  category: string | null
  tags: string[]
  image_url: string | null
  missing_fields: MissingField[]
  confidence: number | null       // 0–1 from AI extraction
  evidence: string | null         // AI-sourced evidence summary
  created_at: string
  updated_at: string
  ingestion_id: string | null
  external_product_id?: string | null
  admin_url?: string | null
  variants?: ProductVariantWeb[]
  stock_on_hand?: number
}

export interface ProductPatch {
  title?: string
  description?: string
  price_inr?: number
  category?: string
  tags?: string[]
  image_url?: string
  version: number                 // optimistic concurrency
}

// ─── Ingestion ───────────────────────────────────────────────────────────────

export interface Ingestion {
  id: string
  store_id: string
  status: IngestionStatus
  file_name: string | null
  file_type: string | null
  error: string | null
  products: Product[]
  created_at: string
  updated_at: string
}

// ─── Actions ─────────────────────────────────────────────────────────────────

export interface Action {
  id: string
  store_id: string
  type: string
  status: ActionStatus
  payload: Record<string, unknown>
  rationale: string | null
  idempotency_key: string
  created_at: string
  resolved_at: string | null
}

// ─── Voice commands ─────────────────────────────────────────────────────────

export interface VoiceCommandResponse {
  transcript: string
  language_code?: string | null
  actions: Action[]
  unparsed: string[]
  message: string
}

// ─── Listings / Publications ─────────────────────────────────────────────────

export interface Listing {
  id: string
  product_id: string
  channel: Channel
  status: ListingStatus
  channel_listing_id: string | null
  channel_url: string | null
  error: string | null
  job_id: string | null
  created_at: string
  updated_at: string
}

// ─── Orders / Inventory ──────────────────────────────────────────────────────

export interface Order {
  id: string
  store_id: string
  channel: Channel
  channel_order_id: string
  status: string
  total_inr: number
  line_items: OrderLineItem[]
  created_at: string
}

export interface OrderLineItem {
  product_id: string | null
  channel_product_id: string
  title: string
  quantity: number
  price_inr: number
}

export interface InventoryEntry {
  product_id: string
  available_quantity: number
  reserved_quantity: number
  updated_at: string
}

// ─── Activity / Audit ────────────────────────────────────────────────────────

export type AuditEventType =
  | 'ingestion.requested'
  | 'ingestion.completed'
  | 'catalogue.draft.created'
  | 'product.approved'
  | 'product.rejected'
  | 'action.proposed'
  | 'action.approved'
  | 'action.rejected'
  | 'listing.publish.requested'
  | 'listing.published'
  | 'listing.failed'
  | 'channel.order.received'
  | 'inventory.changed'

export interface ActivityEvent {
  id: string
  event_type: AuditEventType
  occurred_at: string
  merchant_id: string | null
  aggregate_type: string
  aggregate_id: string
  summary: string               // safe human-readable summary
  metadata: Record<string, unknown>
}

// ─── Store / Channels ────────────────────────────────────────────────────────

export interface Store {
  id: string
  name: string
  owner_name: string
  gst_number: string | null
  pan_number: string | null
  price_change_threshold_pct: number   // e.g. 10 = ±10%
}

export interface ChannelStatus {
  channel: Channel
  connected: boolean
  label: string
  status_message: string | null
}

// ─── API envelope ────────────────────────────────────────────────────────────

export interface ApiError {
  code: string
  message: string
  field_issues?: { field: string; issue: string }[]
}

export interface PaginatedResponse<T> {
  items: T[]
  total: number
  offset: number
  limit: number
}

// ─── Bill intake ─────────────────────────────────────────────────────────────
// Mirrors packages/contracts/src/sabbazaar_contracts/ingestion.py
// (IngestionView). Money and quantity fields serialize as strings/numbers.

export type BillIngestionStatus =
  | 'received'
  | 'extracting'
  | 'needs_input'
  | 'checking'
  | 'awaiting_confirmation'
  | 'applying'
  | 'completed'
  | 'partially_failed'
  | 'failed'
  | 'rejected'

export type BillLineKind = 'restock' | 'new' | 'uncertain_match' | 'unreadable'

export interface BillFieldValue {
  value: string | number | null
  source: 'bill' | 'owner' | 'catalogue' | 'config'
  confidence?: number | null
}

export interface BillWorkingLine {
  id: string
  line_nos: number[]
  kind: BillLineKind | null
  matched_book_id: string | null
  candidate_book_id: string | null
  fields: Record<string, BillFieldValue>
  notes: string[]
  dropped: boolean
}

export type BillQuestionKind = 'missing_field' | 'price' | 'confirm_match'

export interface BillQuestion {
  id: string
  line_id: string
  kind: BillQuestionKind
  field: string | null
  prompt: string
  suggestion: string | null
  blocking: boolean
  allow_drop: boolean
}

export interface BillAnswer {
  question_id: string
  value: string | null
  drop_line?: boolean
}

export interface BillChannelChange {
  channel: string
  operation: 'publish_product' | 'update_product' | 'set_inventory'
  summary: string
  price: string | null
  quantity: number | null
  expected_current: number | null
  payload: Record<string, unknown> | null
}

export interface BillPreviewLine {
  line_id: string
  kind: BillLineKind
  book_id: string | null
  sku: string
  title: string
  stock_before: number
  stock_after: number
  quantity_added: number
  price_before: string | null
  price_after: string
  price_change_pct: number | null
  mrp: string | null
  unit_cost: string | null
  author: string | null
  isbn: string | null
  publisher: string | null
  warnings: string[]
  notes: string[]
  channel_changes: BillChannelChange[]
}

export interface BillPreview {
  version: number
  hash: string
  lines: BillPreviewLine[]
}

export type BillJobStatus =
  | 'pending'
  | 'running'
  | 'succeeded'
  | 'retryable_failure'
  | 'terminal_failure'

export interface BillJob {
  id: string
  line_id: string
  channel: string
  operation: string
  status: BillJobStatus
  attempts: number
  error_code: string | null
  message: string | null
  admin_url: string | null
}

export interface BillIngestionView {
  id: string
  status: BillIngestionStatus
  filename: string
  fallback_used: boolean
  simulated_channels: string[]
  lines: BillWorkingLine[]
  questions: BillQuestion[]
  preview: BillPreview | null
  jobs: BillJob[]
  error: string | null
}
