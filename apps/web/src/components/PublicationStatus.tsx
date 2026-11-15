import { useState, useEffect } from 'react'
import { ExternalLink, RefreshCw, AlertTriangle } from 'lucide-react'
import type { Listing } from '../types/contracts'
import { getListing, retryListing, extractApiError } from '../api/client'
import { StatusBadge } from './StatusBadge'
import { Alert } from './Alert'
import { Spinner } from './Spinner'
import { MOCK_LISTINGS } from '../api/mockData'

interface PublicationStatusProps {
  productId: string
  initialListings?: Listing[]
  isMock?: boolean
}

export function PublicationStatus({ productId, initialListings, isMock }: PublicationStatusProps) {
  const [listings, setListings] = useState<Listing[]>(
    initialListings ?? (isMock ? MOCK_LISTINGS.filter(l => l.product_id === productId) : [])
  )
  const [error, setError] = useState<string | null>(null)
  const [retrying, setRetrying] = useState<string | null>(null)

  // Sync state if initialListings changes
  useEffect(() => {
    if (initialListings) {
      setListings(initialListings)
    }
  }, [initialListings])

  // Simulated progression in mock mode
  useEffect(() => {
    if (!isMock) return
    const queued = listings.find(l => l.status === 'queued')
    if (queued) {
      const timer = setTimeout(() => {
        setListings(ls => ls.map(l => l.id === queued.id ? { ...l, status: 'publishing' } : l))
      }, 1500)
      return () => clearTimeout(timer)
    }

    const publishing = listings.find(l => l.status === 'publishing')
    if (publishing) {
      const timer = setTimeout(() => {
        setListings(ls => ls.map(l => l.id === publishing.id ? {
          ...l,
          status: 'live',
          channel_url: 'https://dev-store.myshopify.com/products/demo-saree',
        } : l))
      }, 2000)
      return () => clearTimeout(timer)
    }
  }, [listings, isMock])

  // Poll while any listing is queued/publishing (real API)
  useEffect(() => {
    if (isMock) return
    const isActive = listings.some(l => l.status === 'queued' || l.status === 'publishing')
    if (!isActive) return

    const interval = setInterval(async () => {
      try {
        const updated = await Promise.all(listings.map(l => getListing(l.id)))
        setListings(updated)
      } catch {
        // silent poll failure
      }
    }, 3000)

    return () => clearInterval(interval)
  }, [listings, isMock])

  async function handleRetry(listingId: string) {
    setRetrying(listingId)
    setError(null)
    try {
      const updated = await retryListing(listingId)
      setListings(ls => ls.map(l => l.id === listingId ? updated : l))
    } catch (err) {
      setError(extractApiError(err))
    } finally {
      setRetrying(null)
    }
  }

  if (listings.length === 0) return null

  return (
    <div className="rounded-xl border border-gray-200 bg-white shadow-sm overflow-hidden">
      <div className="px-5 py-4 border-b border-gray-100">
        <h3 className="font-semibold text-gray-900">Publication Status</h3>
        <p className="text-xs text-gray-500 mt-0.5">Channel-by-channel listing status</p>
      </div>

      <div className="divide-y divide-gray-100">
        {listings.map(listing => (
          <div key={listing.id} className="px-5 py-3 flex items-center justify-between gap-3">
            <div className="flex items-center gap-3 flex-1 min-w-0">
              <div className="flex flex-col gap-1">
                <span className="text-sm font-medium capitalize">{listing.channel}</span>
                {listing.error && (
                  <span className="flex items-center gap-1 text-xs text-red-600">
                    <AlertTriangle className="w-3 h-3" />
                    {listing.error}
                  </span>
                )}
              </div>
            </div>

            <div className="flex items-center gap-2 flex-shrink-0">
              <StatusBadge status={listing.status} pulse />

              {listing.channel_url && listing.status === 'live' && (
                <a
                  href={listing.channel_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center gap-1 text-xs text-blue-600 hover:text-blue-700 hover:underline"
                >
                  View <ExternalLink className="w-3 h-3" />
                </a>
              )}

              {listing.status === 'failed' && (
                <button
                  onClick={() => handleRetry(listing.id)}
                  disabled={retrying === listing.id}
                  className="flex items-center gap-1 text-xs text-blue-600 hover:text-blue-700 border border-blue-200 rounded px-2 py-0.5 hover:bg-blue-50 transition-colors disabled:opacity-60"
                >
                  {retrying === listing.id
                    ? <Spinner size="sm" />
                    : <RefreshCw className="w-3 h-3" />
                  }
                  Retry
                </button>
              )}
            </div>
          </div>
        ))}
      </div>

      {error && (
        <div className="px-5 pb-4">
          <Alert type="error" message={error} onDismiss={() => setError(null)} />
        </div>
      )}

      {isMock && (
        <div className="px-5 py-2 bg-purple-50 border-t border-purple-100">
          <p className="text-xs text-purple-600">
            🎭 Demo mode — this shows a fixture Shopify publication result, not a live connection.
          </p>
        </div>
      )}
    </div>
  )
}
