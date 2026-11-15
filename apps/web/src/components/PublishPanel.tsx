import { useState } from 'react'
import { Send, Store } from 'lucide-react'
import type { Product, Listing } from '../types/contracts'
import { publishProducts, extractApiError } from '../api/client'
import { Alert } from './Alert'
import { Spinner } from './Spinner'

const CHANNELS = [
  { id: 'shopify', label: 'Shopify Dev Store', available: true },
  { id: 'ondc',   label: 'ONDC',              available: false },
  { id: 'meesho', label: 'Meesho',            available: false },
  { id: 'amazon', label: 'Amazon',            available: false },
]

interface PublishPanelProps {
  approvedProducts: Product[]
  onPublished: (listings: Listing[]) => void
  isMock?: boolean
}

export function PublishPanel({ approvedProducts, onPublished, isMock }: PublishPanelProps) {
  const [selectedProducts, setSelectedProducts] = useState<Set<string>>(new Set())
  const [selectedChannels, setSelectedChannels] = useState<Set<string>>(new Set(['shopify']))
  const [publishing, setPublishing] = useState(false)
  const [error, setError] = useState<string | null>(null)

  function toggleProduct(id: string) {
    setSelectedProducts(s => {
      const n = new Set(s)
      n.has(id) ? n.delete(id) : n.add(id)
      return n
    })
  }

  function toggleChannel(id: string) {
    if (!CHANNELS.find(c => c.id === id)?.available) return
    setSelectedChannels(s => {
      const n = new Set(s)
      n.has(id) ? n.delete(id) : n.add(id)
      return n
    })
  }

  async function handlePublish() {
    if (isMock) {
      // Simulate publication in mock mode
      const mockListings: Listing[] = Array.from(selectedProducts).map(pid => ({
        id: `list-mock-${pid}`,
        product_id: pid,
        channel: 'shopify',
        status: 'queued',
        channel_listing_id: null,
        channel_url: null,
        error: null,
        job_id: null,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      }))
      onPublished(mockListings)
      return
    }

    setPublishing(true)
    setError(null)
    try {
      const listings = await publishProducts(
        Array.from(selectedProducts),
        Array.from(selectedChannels),
      )
      onPublished(listings)
      setSelectedProducts(new Set())
    } catch (err) {
      setError(extractApiError(err))
    } finally {
      setPublishing(false)
    }
  }

  if (approvedProducts.length === 0) {
    return (
      <div className="rounded-xl border border-gray-200 bg-white shadow-sm p-6 text-center">
        <Store className="w-8 h-8 text-gray-300 mx-auto mb-2" />
        <p className="text-sm text-gray-500">Approve products to publish them to channels.</p>
      </div>
    )
  }

  const canPublish = selectedProducts.size > 0 && selectedChannels.size > 0

  return (
    <div className="rounded-xl border border-gray-200 bg-white shadow-sm overflow-hidden">
      <div className="px-5 py-4 border-b border-gray-100">
        <h3 className="font-semibold text-gray-900">Publish to Channels</h3>
        <p className="text-xs text-gray-500 mt-0.5">Select approved products and channels to publish</p>
      </div>

      <div className="px-5 py-4 space-y-4">
        {/* Product selection */}
        <div>
          <p className="text-xs font-medium text-gray-600 mb-2">Approved products</p>
          <div className="space-y-2">
            {approvedProducts.map(p => (
              <label key={p.id} className="flex items-center gap-3 cursor-pointer group">
                <input
                  type="checkbox"
                  checked={selectedProducts.has(p.id)}
                  onChange={() => toggleProduct(p.id)}
                  className="w-4 h-4 rounded accent-blue-600"
                />
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-gray-800 truncate">{p.title}</p>
                  {p.price_inr && (
                    <p className="text-xs text-gray-500">₹{p.price_inr.toLocaleString('en-IN')}</p>
                  )}
                </div>
              </label>
            ))}
          </div>
        </div>

        {/* Channel selection */}
        <div>
          <p className="text-xs font-medium text-gray-600 mb-2">Target channels</p>
          <div className="grid grid-cols-2 gap-2">
            {CHANNELS.map(ch => (
              <button
                key={ch.id}
                onClick={() => toggleChannel(ch.id)}
                disabled={!ch.available}
                className={`flex items-center justify-between gap-2 rounded-lg border px-3 py-2 text-sm transition-colors ${
                  !ch.available
                    ? 'border-gray-100 bg-gray-50 text-gray-400 cursor-not-allowed'
                    : selectedChannels.has(ch.id)
                    ? 'border-blue-300 bg-blue-50 text-blue-700'
                    : 'border-gray-200 bg-white text-gray-700 hover:bg-gray-50'
                }`}
              >
                <span>{ch.label}</span>
                {!ch.available && (
                  <span className="text-xs bg-gray-200 text-gray-500 rounded px-1">Soon</span>
                )}
              </button>
            ))}
          </div>
        </div>

        {error && <Alert type="error" message={error} onDismiss={() => setError(null)} />}

        <button
          onClick={handlePublish}
          disabled={!canPublish || publishing}
          className="w-full flex items-center justify-center gap-2 rounded-lg bg-blue-600 px-4 py-2.5 text-sm font-medium text-white hover:bg-blue-700 transition-colors disabled:opacity-60 disabled:cursor-not-allowed"
        >
          {publishing
            ? <><Spinner size="sm" className="border-white border-t-transparent" /> Publishing…</>
            : <><Send className="w-4 h-4" /> Publish {selectedProducts.size > 0 ? selectedProducts.size : ''} product{selectedProducts.size !== 1 ? 's' : ''}</>
          }
        </button>

        {isMock && (
          <p className="text-xs text-center text-purple-600">
            🎭 Demo mode — publication will show queued state only
          </p>
        )}
      </div>
    </div>
  )
}
