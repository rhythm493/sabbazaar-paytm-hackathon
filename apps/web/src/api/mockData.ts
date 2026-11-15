// Mock data fixtures for development without a backend.
// These are used when the API server is not reachable.
// Clearly labelled as FIXTURE data throughout the UI.

import type { Product, Ingestion, ActivityEvent, Store, ChannelStatus, Listing } from '../types/contracts'

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
