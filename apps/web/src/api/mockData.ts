// Mock data fixtures for development without a backend.
// These are used when the API server is not reachable.
// Clearly labelled as FIXTURE data throughout the UI.

import type { Product, Ingestion, ActivityEvent, Store, ChannelStatus, Listing, Action, BillPreviewLine, BillIngestionView } from '../types/contracts'

export const MOCK_STORE: Store = {
  id: 'store-001',
  name: "Meena's Saree Shop",
  owner_name: 'Meena Desai',
  gst_number: null,
  pan_number: null,
  price_change_threshold_pct: 10,
}

export const MOCK_PRODUCTS: Product[] = [
  {
    id: 'prod-001',
    store_id: 'store-001',
    status: 'draft',
    version: 1,
    title: 'Banarasi Silk Saree – Red Gold',
    description: 'Hand-woven Banarasi silk saree with zari border. Perfect for weddings and festivals. Available in 5.5 metres.',
    price_inr: 3500,
    category: 'Sarees',
    tags: ['banarasi', 'silk', 'wedding', 'festive'],
    image_url: null,
    missing_fields: [],
    confidence: 0.91,
    evidence: 'Extracted from product photo: visible zari work, red base, gold border pattern.',
    created_at: new Date(Date.now() - 120000).toISOString(),
    updated_at: new Date(Date.now() - 120000).toISOString(),
    ingestion_id: 'ing-001',
  },
  {
    id: 'prod-002',
    store_id: 'store-001',
    status: 'draft',
    version: 1,
    title: 'Cotton Printed Saree',
    description: null,
    price_inr: null,
    category: 'Sarees',
    tags: ['cotton', 'casual'],
    image_url: null,
    missing_fields: [
      { field: 'description', reason: 'AI could not extract full description from image.' },
      { field: 'price_inr', reason: 'No price visible in photo. Please enter manually.' },
    ],
    confidence: 0.62,
    evidence: 'Extracted from product photo: cotton weave, floral print.',
    created_at: new Date(Date.now() - 90000).toISOString(),
    updated_at: new Date(Date.now() - 90000).toISOString(),
    ingestion_id: 'ing-001',
  },
  {
    id: 'prod-003',
    store_id: 'store-001',
    status: 'approved',
    version: 2,
    title: 'Chanderi Silk Saree – Pastel Blue',
    description: 'Lightweight Chanderi silk with delicate embroidery. Ideal for summer occasions.',
    price_inr: 2200,
    category: 'Sarees',
    tags: ['chanderi', 'silk', 'summer', 'embroidery'],
    image_url: null,
    missing_fields: [],
    confidence: 0.88,
    evidence: 'Extracted from product photo and bill: Chanderi fabric, light blue colour, embroidery detail.',
    created_at: new Date(Date.now() - 300000).toISOString(),
    updated_at: new Date(Date.now() - 60000).toISOString(),
    ingestion_id: 'ing-001',
  },
]

export const MOCK_INGESTION: Ingestion = {
  id: 'ing-001',
  store_id: 'store-001',
  status: 'completed',
  file_name: 'saree_rack.jpg',
  file_type: 'image/jpeg',
  error: null,
  products: MOCK_PRODUCTS,
  created_at: new Date(Date.now() - 320000).toISOString(),
  updated_at: new Date(Date.now() - 300000).toISOString(),
}

export const MOCK_LISTINGS: Listing[] = [
  {
    id: 'list-001',
    product_id: 'prod-003',
    channel: 'shopify',
    status: 'live',
    channel_listing_id: 'shopify-prod-7890',
    channel_url: 'https://your-dev-store.myshopify.com/products/chanderi-silk-saree',
    error: null,
    job_id: 'job-001',
    created_at: new Date(Date.now() - 60000).toISOString(),
    updated_at: new Date(Date.now() - 30000).toISOString(),
  },
]

export const MOCK_ACTIVITY: ActivityEvent[] = [
  {
    id: 'evt-001',
    event_type: 'ingestion.requested',
    occurred_at: new Date(Date.now() - 320000).toISOString(),
    merchant_id: 'store-001',
    aggregate_type: 'ingestion',
    aggregate_id: 'ing-001',
    summary: 'Image upload started — saree_rack.jpg',
    metadata: { file_name: 'saree_rack.jpg' },
  },
  {
    id: 'evt-002',
    event_type: 'ingestion.completed',
    occurred_at: new Date(Date.now() - 300000).toISOString(),
    merchant_id: 'store-001',
    aggregate_type: 'ingestion',
    aggregate_id: 'ing-001',
    summary: 'AI extracted 3 product drafts',
    metadata: { product_count: 3 },
  },
  {
    id: 'evt-003',
    event_type: 'catalogue.draft.created',
    occurred_at: new Date(Date.now() - 295000).toISOString(),
    merchant_id: 'store-001',
    aggregate_type: 'product',
    aggregate_id: 'prod-003',
    summary: 'Draft created: Chanderi Silk Saree – Pastel Blue',
    metadata: { product_id: 'prod-003', confidence: 0.88 },
  },
  {
    id: 'evt-004',
    event_type: 'product.approved',
    occurred_at: new Date(Date.now() - 60000).toISOString(),
    merchant_id: 'store-001',
    aggregate_type: 'product',
    aggregate_id: 'prod-003',
    summary: 'Merchant approved: Chanderi Silk Saree – Pastel Blue',
    metadata: { product_id: 'prod-003' },
  },
  {
    id: 'evt-005',
    event_type: 'listing.publish.requested',
    occurred_at: new Date(Date.now() - 55000).toISOString(),
    merchant_id: 'store-001',
    aggregate_type: 'listing',
    aggregate_id: 'list-001',
    summary: 'Publication to Shopify requested',
    metadata: { channel: 'shopify', product_id: 'prod-003' },
  },
  {
    id: 'evt-006',
    event_type: 'listing.published',
    occurred_at: new Date(Date.now() - 30000).toISOString(),
    merchant_id: 'store-001',
    aggregate_type: 'listing',
    aggregate_id: 'list-001',
    summary: '✓ Published to Shopify — product is now live',
    metadata: { channel: 'shopify', channel_url: 'https://your-dev-store.myshopify.com/products/chanderi-silk-saree' },
  },
]

export const MOCK_VOICE_TRANSCRIPT = 'stock of banarasi silk saree to 25 and price of chanderi silk saree to 2100'

export const MOCK_VOICE_ACTIONS: Action[] = [
  {
    id: 'mock-action-voice-1',
    store_id: 'store-001',
    type: 'shopify.set_inventory',
    status: 'awaiting_approval',
    payload: {
      intent: 'set_stock',
      operation: 'set_inventory',
      product_id: 'prod-001',
      variant_id: 'var-mock-001',
      sku: 'BNR-BAN-0001',
      title: 'Banarasi Silk Saree – Red Gold',
      quantity: 25,
      rationale: 'Merchant asked to set stock of Banarasi silk saree to 25.',
    },
    rationale: 'Merchant asked to set stock of Banarasi silk saree to 25.',
    idempotency_key: 'cmd:mockvoice001',
    created_at: new Date(Date.now() - 30000).toISOString(),
    resolved_at: null,
  },
  {
    id: 'mock-action-voice-2',
    store_id: 'store-001',
    type: 'shopify.update_product',
    status: 'awaiting_approval',
    payload: {
      intent: 'set_price',
      operation: 'update_product',
      product_id: 'prod-003',
      variant_id: 'var-mock-003',
      sku: 'CHN-CHN-0003',
      title: 'Chanderi Silk Saree – Pastel Blue',
      price_inr_old: 2200,
      price_inr_new: 2100,
      rationale: 'Merchant asked to lower the price to ₹2,100.',
    },
    rationale: 'Merchant asked to lower the price to ₹2,100.',
    idempotency_key: 'cmd:mockvoice002',
    created_at: new Date(Date.now() - 20000).toISOString(),
    resolved_at: null,
  },
]

export const MOCK_CHANNELS: ChannelStatus[] = [
  {
    channel: 'shopify',
    connected: true,
    label: 'Shopify Dev Store',
    status_message: 'Connected to development store',
  },
  {
    channel: 'ondc',
    connected: false,
    label: 'ONDC',
    status_message: 'Coming soon',
  },
  {
    channel: 'meesho',
    connected: false,
    label: 'Meesho',
    status_message: 'Coming soon',
  },
]

// ─── Bill intake fixtures (live-verified shapes from the LangGraph flow) ────
// Mirrors the extraction of tests/fixtures/bills/sample_bill.png — the same
// data the demo shows when the API is unreachable.

const BILL_LINES: BillIngestionView['lines'] = [
  {
    id: 'L1', line_nos: [1, 5], kind: 'new',
    matched_book_id: null, candidate_book_id: null,
    fields: {
      title:     { value: 'Atomic Habits', source: 'bill', confidence: 1.0 },
      author:    { value: 'James Clear', source: 'bill', confidence: 1.0 },
      isbn:      { value: '9781847941831', source: 'bill', confidence: 1.0 },
      publisher: { value: 'Random House Business', source: 'bill', confidence: 1.0 },
      quantity:  { value: 8, source: 'bill', confidence: 1.0 },
      mrp:       { value: '799.00', source: 'bill', confidence: 1.0 },
      unit_cost: { value: '520.00', source: 'bill', confidence: 1.0 },
    },
    notes: ['Bill line 5 has the same ISBN; quantities were combined'],
    dropped: false,
  },
  {
    id: 'L2', line_nos: [2], kind: 'new',
    matched_book_id: null, candidate_book_id: null,
    fields: {
      title:     { value: 'The Psychology of Money', source: 'bill', confidence: 1.0 },
      author:    { value: 'Morgan House', source: 'bill', confidence: 1.0 },
      isbn:      { value: '9789390166268', source: 'bill', confidence: 1.0 },
      publisher: { value: 'Jaico Publishing House', source: 'bill', confidence: 1.0 },
      quantity:  { value: 4, source: 'bill', confidence: 1.0 },
      mrp:       { value: '399.00', source: 'bill', confidence: 1.0 },
      unit_cost: { value: '250.00', source: 'bill', confidence: 1.0 },
    },
    notes: [],
    dropped: false,
  },
  {
    id: 'L3', line_nos: [3], kind: 'new',
    matched_book_id: null, candidate_book_id: null,
    fields: {
      title:     { value: 'Ikigai', source: 'bill', confidence: 1.0 },
      author:    { value: 'Hector Garcia', source: 'bill', confidence: 1.0 },
      isbn:      { value: '9781786330895', source: 'bill', confidence: 1.0 },
      publisher: { value: 'Hutchinson', source: 'bill', confidence: 1.0 },
      quantity:  { value: 6, source: 'bill', confidence: 1.0 },
      mrp:       { value: '499.00', source: 'bill', confidence: 1.0 },
      unit_cost: { value: '330.00', source: 'bill', confidence: 1.0 },
    },
    notes: [],
    dropped: false,
  },
  {
    id: 'L4', line_nos: [4], kind: 'new',
    matched_book_id: null, candidate_book_id: null,
    fields: {
      title:     { value: 'Wings of Fire', source: 'bill', confidence: 1.0 },
      author:    { value: 'A.P.J. Abdul Kalam', source: 'bill', confidence: 1.0 },
      publisher: { value: 'Universities Press', source: 'bill', confidence: 1.0 },
      quantity:  { value: 10, source: 'bill', confidence: 1.0 },
      mrp:       { value: '350.00', source: 'bill', confidence: 1.0 },
      unit_cost: { value: '220.00', source: 'bill', confidence: 1.0 },
    },
    notes: [],
    dropped: false,
  },
  {
    id: 'L6', line_nos: [6], kind: 'new',
    matched_book_id: null, candidate_book_id: null,
    fields: {
      title:     { value: 'Sapiens', source: 'bill', confidence: 1.0 },
      author:    { value: 'Yuval Noah Harari', source: 'bill', confidence: 1.0 },
      publisher: { value: 'Vintage', source: 'bill', confidence: 1.0 },
      quantity:  { value: 2, source: 'bill', confidence: 1.0 },
      mrp:       { value: '599.00', source: 'bill', confidence: 1.0 },
      unit_cost: { value: '400.00', source: 'bill', confidence: 1.0 },
    },
    notes: ["ISBN '9780099590089' on bill line 6 is not valid and was ignored"],
    dropped: false,
  },
]

const BILL_QUESTIONS: BillIngestionView['questions'] = BILL_LINES.map(l => ({
  id: `${l.id}:price:selling_price`,
  line_id: l.id,
  kind: 'price' as const,
  field: 'selling_price',
  prompt: `What selling price should '${l.fields.title.value}' have? The bill shows MRP ₹${l.fields.mrp.value}.`,
  suggestion: l.fields.mrp.value as string,
  blocking: true,
  allow_drop: false,
}))

function billPreviewLine(lineId: string, title: string, sku: string, qty: number, price: string, unitCost: string, author: string, isbn: string | null, publisher: string): BillPreviewLine {
  const mrp = price
  return {
    line_id: lineId, kind: 'new' as const, book_id: null, sku, title,
    stock_before: 0, stock_after: qty, quantity_added: qty,
    price_before: null, price_after: price, price_change_pct: null,
    mrp, unit_cost: unitCost, author, isbn, publisher,
    warnings: [], notes: [],
    channel_changes: [{
      channel: 'shopify',
      operation: 'publish_product' as const,
      summary: `Shopify: create draft product at ₹${price}, inventory ${qty}`,
      price, quantity: qty, expected_current: null,
      payload: { sku, title, status: 'draft' },
    }],
  }
}

export const MOCK_BILL_NEEDS_INPUT: BillIngestionView = {
  id: 'mock-bill-001',
  status: 'needs_input',
  filename: 'sample_bill.png',
  fallback_used: false,
  simulated_channels: ['shopify'],
  lines: BILL_LINES,
  questions: BILL_QUESTIONS,
  preview: null,
  jobs: [],
  error: null,
}

export const MOCK_BILL_AWAITING_CONFIRMATION: BillIngestionView = {
  ...MOCK_BILL_NEEDS_INPUT,
  status: 'awaiting_confirmation',
  questions: [],
  preview: {
    version: 1,
    hash: 'mock-bill-hash-0001',
    lines: [
      billPreviewLine('L1', 'Atomic Habits', '9781847941831', 8, '799.00', '520.00', 'James Clear', '9781847941831', 'Random House Business'),
      billPreviewLine('L2', 'The Psychology of Money', '9789390166268', 4, '399.00', '250.00', 'Morgan House', '9789390166268', 'Jaico Publishing House'),
      billPreviewLine('L3', 'Ikigai', '9781786330895', 6, '499.00', '330.00', 'Hector Garcia', '9781786330895', 'Hutchinson'),
      billPreviewLine('L4', 'Wings of Fire', 'SB-mock-L4', 10, '350.00', '220.00', 'A.P.J. Abdul Kalam', null, 'Universities Press'),
      billPreviewLine('L6', 'Sapiens', 'SB-mock-L6', 2, '599.00', '400.00', 'Yuval Noah Harari', null, 'Vintage'),
    ],
  },
}

export const MOCK_BILL_COMPLETED: BillIngestionView = {
  ...MOCK_BILL_AWAITING_CONFIRMATION,
  status: 'completed',
  jobs: (MOCK_BILL_AWAITING_CONFIRMATION.preview!.lines as { line_id: string }[]).map((l, i) => ({
    id: `mock-job-${i + 1}`,
    line_id: l.line_id,
    channel: 'shopify',
    operation: 'publish_product',
    status: 'succeeded' as const,
    attempts: 1,
    error_code: null,
    message: null,
    admin_url: `https://your-dev-store.myshopify.com/admin/products/1553000000000${i + 1}`,
  })),
}
