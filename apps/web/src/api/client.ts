import axios, { AxiosError } from 'axios'
import type {
  Product,
  ProductPatch,
  Ingestion,
  Action,
  Listing,
  ActivityEvent,
  Store,
  ChannelStatus,
  Order,
  InventoryEntry,
  PaginatedResponse,
  ApiError,
} from '../types/contracts'

// ─── Axios instance ───────────────────────────────────────────────────────────

const api = axios.create({
  baseURL: '/v1',
  headers: { 'Content-Type': 'application/json' },
  timeout: 30_000,
})

// Error normalizer
export function extractApiError(err: unknown): string {
  if (err instanceof AxiosError) {
    const data = err.response?.data as (ApiError & { detail?: string | { message?: string } }) | undefined
    if (data?.message) return data.message
    if (typeof data?.detail === 'string') return data.detail
    if (data?.detail?.message) return data.detail.message
    if (err.response?.status === 404) return 'Resource not found.'
    if (err.response?.status === 409) return 'Conflict: resource was updated. Please refresh.'
    if (err.response?.status === 422) return 'Validation error. Check the form fields.'
    if (err.response?.status && err.response.status >= 500)
      return 'Server error. Please try again shortly.'
    if (err.code === 'ECONNABORTED') return 'Request timed out. Is the API server running?'
    if (!err.response) return 'Cannot reach the server. Is it running on port 8000?'
  }
  return 'An unexpected error occurred.'
}

// ─── Store ───────────────────────────────────────────────────────────────────

export async function getStore(): Promise<Store> {
  const { data } = await api.get<Store>('/store')
  return data
}

export async function updateStore(patch: Partial<Store>): Promise<Store> {
  const { data } = await api.patch<Store>('/store', patch)
  return data
}

// ─── Channels ────────────────────────────────────────────────────────────────

export async function getChannels(): Promise<ChannelStatus[]> {
  const { data } = await api.get<ChannelStatus[]>('/channels')
  return data
}

export async function getShopifyStatus(): Promise<ChannelStatus> {
  const { data } = await api.get<ChannelStatus>('/channels/shopify/status')
  return data
}

// ─── Ingestions ──────────────────────────────────────────────────────────────

export async function createIngestion(file: File): Promise<Ingestion> {
  const form = new FormData()
  form.append('file', file)
  const { data } = await api.post<Ingestion>('/ingestions', form, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
  return data
}

export async function createIngestionFromFixture(fixtureName: string = 'saree_sample'): Promise<Ingestion> {
  const { data } = await api.post<Ingestion>('/ingestions', { fixture: fixtureName })
  return data
}

export async function getIngestion(id: string): Promise<Ingestion> {
  const { data } = await api.get<Ingestion>(`/ingestions/${id}`)
  return data
}

// ─── Products ────────────────────────────────────────────────────────────────

export async function getProducts(params?: {
  status?: string
  limit?: number
  offset?: number
}): Promise<PaginatedResponse<Product>> {
  const { data } = await api.get<PaginatedResponse<Product>>('/products', { params })
  return data
}

export async function getProduct(id: string): Promise<Product> {
  const { data } = await api.get<Product>(`/products/${id}`)
  return data
}

export async function patchProduct(id: string, patch: ProductPatch): Promise<Product> {
  const { data } = await api.patch<Product>(`/products/${id}`, patch)
  return data
}

export async function approveProduct(id: string): Promise<Product> {
  const { data } = await api.post<Product>(`/products/${id}/approve`)
  return data
}

export async function createProductManual(draft: Omit<Product, 'id' | 'store_id' | 'version' | 'created_at' | 'updated_at' | 'ingestion_id' | 'status'>): Promise<Product> {
  const { data } = await api.post<Product>('/products', draft)
  return data
}

// ─── Actions ─────────────────────────────────────────────────────────────────

export async function getActions(status?: string): Promise<Action[]> {
  const { data } = await api.get<Action[]>('/actions', {
    params: status ? { status } : undefined,
  })
  return data
}

export async function approveAction(id: string): Promise<Action> {
  const { data } = await api.post<Action>(`/actions/${id}/approve`)
  return data
}

export async function rejectAction(id: string): Promise<Action> {
  const { data } = await api.post<Action>(`/actions/${id}/reject`)
  return data
}

// ─── Publications ────────────────────────────────────────────────────────────

export async function publishProducts(productIds: string[], channels: string[]): Promise<Listing[]> {
  const { data } = await api.post<Listing[]>('/publications', { product_ids: productIds, channels })
  return data
}

// ─── Listings ────────────────────────────────────────────────────────────────

export async function getListings(productId?: string): Promise<Listing[]> {
  const { data } = await api.get<Listing[]>('/listings', {
    params: productId ? { product_id: productId } : undefined,
  })
  return data
}

export async function getListing(id: string): Promise<Listing> {
  const { data } = await api.get<Listing>(`/listings/${id}`)
  return data
}

export async function retryListing(id: string): Promise<Listing> {
  const { data } = await api.post<Listing>(`/listings/${id}/retry`)
  return data
}

export async function pauseListing(id: string): Promise<Listing> {
  const { data } = await api.post<Listing>(`/listings/${id}/pause`)
  return data
}

// ─── Orders ──────────────────────────────────────────────────────────────────

export async function getOrders(): Promise<Order[]> {
  const { data } = await api.get<Order[]>('/orders')
  return data
}

// ─── Inventory ───────────────────────────────────────────────────────────────

export async function getInventory(): Promise<InventoryEntry[]> {
  const { data } = await api.get<InventoryEntry[]>('/inventory')
  return data
}

// ─── Activity ────────────────────────────────────────────────────────────────

export async function getActivity(limit = 50): Promise<ActivityEvent[]> {
  const { data } = await api.get<ActivityEvent[]>('/activity', { params: { limit } })
  return data
}

// ─── Health ──────────────────────────────────────────────────────────────────

export async function checkHealth(): Promise<{ status: string }> {
  const { data } = await axios.get<{ status: string }>('/health/ready')
  return data
}
