import { useState, useEffect, useCallback } from 'react'
import { PackageOpen, Sparkles } from 'lucide-react'

import type { Product, Ingestion, Listing, Store, ActivityEvent } from '../types/contracts'
import { getProducts, getStore, approveProduct, extractApiError } from '../api/client'
import { MOCK_PRODUCTS, MOCK_STORE, MOCK_ACTIVITY, MOCK_LISTINGS } from '../api/mockData'

import { Header } from '../components/Header'
import { ProductUpload } from '../components/ProductUpload'
import { DraftEditor } from '../components/DraftEditor'
import { PublishPanel } from '../components/PublishPanel'
import { PublicationStatus } from '../components/PublicationStatus'
import { ActivityTimeline } from '../components/ActivityTimeline'
import { PriceThresholdControl } from '../components/PriceThresholdControl'
import { LoadingState } from '../components/Spinner'
import { EmptyState } from '../components/Alert'

type Section = 'catalogue' | 'publish' | 'activity' | 'settings'

export default function Dashboard() {
  const [isMock, setIsMock] = useState(false)
  const [store, setStore] = useState<Store | null>(null)
  const [products, setProducts] = useState<Product[]>([])
  const [listings, setListings] = useState<Listing[]>([])
  const [mockActivity, setMockActivity] = useState<ActivityEvent[]>(MOCK_ACTIVITY)
  const [loading, setLoading] = useState(true)
  const [activeSection, setActiveSection] = useState<Section>('catalogue')

  // ── Load initial data ───────────────────────────────────────────────────────
  const loadData = useCallback(async () => {
    if (isMock) {
      setStore(MOCK_STORE)
      setProducts(MOCK_PRODUCTS)
      setListings(MOCK_LISTINGS)
      setLoading(false)
      return
    }

    try {
      const [storeData, productsData] = await Promise.all([
        getStore(),
        getProducts({ limit: 50 }),
      ])
      setStore(storeData)
      setProducts(productsData.items)
    } catch (err) {
      const msg = extractApiError(err)
      console.warn('API is unreachable, auto-switching to demo mode:', msg)
      // Auto-fallback to demo mode so the UI is immediately interactive
      setIsMock(true)
      setStore(MOCK_STORE)
      setProducts(MOCK_PRODUCTS)
      setListings(MOCK_LISTINGS)
    } finally {
      setLoading(false)
    }
  }, [isMock])

  useEffect(() => {
    setLoading(true)
    loadData()
  }, [loadData, isMock])

  // ── Handlers ────────────────────────────────────────────────────────────────

  function handleToggleMock() {
    setIsMock(prev => {
      const next = !prev
      if (next) {
        setStore(MOCK_STORE)
        setProducts(MOCK_PRODUCTS)
        setListings(MOCK_LISTINGS)
      } else {
        setLoading(true)
      }
      return next
    })
  }

  function handleIngestionStarted(ingestion: Ingestion) {
    if (ingestion.products && ingestion.products.length > 0) {
      setProducts(prev => [
        ...ingestion.products,
        ...prev.filter(p => !ingestion.products.find(np => np.id === p.id)),
      ])
      if (isMock) {
        setMockActivity(prev => [
          {
            id: `evt-ingest-${Date.now()}`,
            event_type: 'ingestion.completed',
            occurred_at: new Date().toISOString(),
            merchant_id: MOCK_STORE.id,
            aggregate_type: 'ingestion',
            aggregate_id: ingestion.id,
            summary: `Catalogue updated: ${ingestion.products.length} product draft(s) created`,
            metadata: { file_name: ingestion.file_name },
          },
          ...prev,
        ])
      }
    }
    setActiveSection('catalogue')
  }

  function handleUseMock() {
    setIsMock(true)
    setStore(MOCK_STORE)
    setProducts(MOCK_PRODUCTS)
    setListings(MOCK_LISTINGS)
    setLoading(false)
  }

  function handleProductUpdated(updated: Product) {
    setProducts(prev => prev.map(p => p.id === updated.id ? updated : p))
  }

  async function handleApprove(product: Product) {
    if (isMock) {
      const approved: Product = { ...product, status: 'approved', version: product.version + 1 }
      setProducts(prev => prev.map(p => p.id === product.id ? approved : p))
      setMockActivity(prev => [
        {
          id: `evt-approve-${product.id}-${Date.now()}`,
          event_type: 'product.approved',
          occurred_at: new Date().toISOString(),
          merchant_id: MOCK_STORE.id,
          aggregate_type: 'product',
          aggregate_id: product.id,
          summary: `Merchant approved: ${product.title}`,
          metadata: { product_id: product.id },
        },
        ...prev,
      ])
      return
    }
    try {
      const approved = await approveProduct(product.id)
      setProducts(prev => prev.map(p => p.id === product.id ? approved : p))
    } catch (err) {
      console.error('Approve failed:', extractApiError(err))
    }
  }

  function handlePublished(newListings: Listing[]) {
    setListings(prev => [
      ...newListings,
      ...prev.filter(l => !newListings.find(nl => nl.id === l.id)),
    ])
    if (isMock) {
      setMockActivity(prev => [
        {
          id: `evt-publish-${Date.now()}`,
          event_type: 'listing.publish.requested',
          occurred_at: new Date().toISOString(),
          merchant_id: MOCK_STORE.id,
          aggregate_type: 'listing',
          aggregate_id: newListings[0]?.id ?? 'list-new',
          summary: `Publication requested for ${newListings.length} product(s)`,
          metadata: { channel: 'shopify' },
        },
        ...prev,
      ])
    }
    setActiveSection('publish')
  }

  // ── Derived state ───────────────────────────────────────────────────────────
  const approvedProducts = products.filter(p => p.status === 'approved')

  const listingsByProduct = (productId: string) =>
    listings.filter(l => l.product_id === productId)

  // ── Render ──────────────────────────────────────────────────────────────────
  const navItems: { id: Section; label: string; count?: number }[] = [
    { id: 'catalogue', label: 'Catalogue', count: products.length },
    { id: 'publish',   label: 'Publish',   count: listings.length },
    { id: 'activity',  label: 'Activity' },
    { id: 'settings',  label: 'Settings' },
  ]

  return (
    <div className="min-h-screen bg-gray-50">
      <Header isMock={isMock} onToggleMock={handleToggleMock} store={store ?? undefined} />

      {/* Nav tabs */}
      <div className="bg-white border-b border-gray-200">
        <div className="max-w-5xl mx-auto px-4 sm:px-6 flex gap-1 overflow-x-auto scrollbar-thin">
          {navItems.map(item => (
            <button
              key={item.id}
              onClick={() => setActiveSection(item.id)}
              className={`flex items-center gap-1.5 px-4 py-3 text-sm font-medium border-b-2 transition-colors whitespace-nowrap ${
                activeSection === item.id
                  ? 'border-blue-600 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700'
              }`}
            >
              {item.label}
              {item.count !== undefined && item.count > 0 && (
                <span className={`text-xs rounded-full px-1.5 py-0.5 font-medium ${
                  activeSection === item.id ? 'bg-blue-100 text-blue-700' : 'bg-gray-100 text-gray-500'
                }`}>
                  {item.count}
                </span>
              )}
            </button>
          ))}
        </div>
      </div>

      <main className="max-w-5xl mx-auto px-4 sm:px-6 py-6">
        {/* Demo Mode banner */}
        {isMock && (
          <div className="mb-6 flex items-center justify-between gap-3 rounded-xl bg-purple-50 border border-purple-200 px-4 py-3 text-sm text-purple-900 shadow-sm">
            <div className="flex items-center gap-2.5">
              <Sparkles className="w-4 h-4 text-purple-600 flex-shrink-0" />
              <span>
                <strong>Demo Mode Active:</strong> You are exploring with interactive simulated store data. When Ridam boots the backend API on port 8000, toggle Demo Mode off in the top right to connect live.
              </span>
            </div>
          </div>
        )}

        {loading ? (
          <LoadingState message="Loading your store…" />
        ) : (
          <>
            {/* ── CATALOGUE ───────────────────────────────────────── */}
            {activeSection === 'catalogue' && (
              <div className="space-y-6">
                {/* Upload section */}
                <section>
                  <h2 className="text-base font-semibold text-gray-900 mb-3">Add Products</h2>
                  <ProductUpload
                    onIngestionStarted={handleIngestionStarted}
                    useMockData={!isMock}
                    onUseMock={handleUseMock}
                    isMock={isMock}
                  />
                </section>

                {/* Product list */}
                {products.length > 0 && (
                  <section>
                    <h2 className="text-base font-semibold text-gray-900 mb-3">
                      Products
                      {isMock && (
                        <span className="ml-2 text-xs font-normal text-purple-600 bg-purple-50 border border-purple-200 rounded-full px-2 py-0.5">
                          fixture data
                        </span>
                      )}
                    </h2>
                    <div className="space-y-3">
                      {products.map(product => (
                        <div key={product.id}>
                          <DraftEditor
                            product={product}
                            onUpdated={handleProductUpdated}
                            onApprove={handleApprove}
                            isMock={isMock}
                          />
                          {/* Inline publication status for this product */}
                          {listingsByProduct(product.id).length > 0 && (
                            <div className="mt-2 ml-4">
                              <PublicationStatus
                                productId={product.id}
                                initialListings={listingsByProduct(product.id)}
                                isMock={isMock}
                              />
                            </div>
                          )}
                        </div>
                      ))}
                    </div>
                  </section>
                )}

                {products.length === 0 && !loading && (
                  <EmptyState
                    icon={<PackageOpen className="w-12 h-12" />}
                    title="No products yet"
                    description="Upload product photos or a bill to let AI create your catalogue."
                  />
                )}
              </div>
            )}

            {/* ── PUBLISH ─────────────────────────────────────────── */}
            {activeSection === 'publish' && (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div>
                  <PublishPanel
                    approvedProducts={approvedProducts}
                    onPublished={handlePublished}
                    isMock={isMock}
                  />
                </div>
                <div className="space-y-4">
                  {listings.length > 0 ? (
                    listings.map(listing => (
                      <PublicationStatus
                        key={listing.id}
                        productId={listing.product_id}
                        initialListings={[listing]}
                        isMock={isMock}
                      />
                    ))
                  ) : (
                    <EmptyState
                      title="No publications yet"
                      description="Approve products in the Catalogue tab, then publish them here."
                    />
                  )}
                </div>
              </div>
            )}

            {/* ── ACTIVITY ─────────────────────────────────────────── */}
            {activeSection === 'activity' && (
              <ActivityTimeline
                events={isMock ? mockActivity : undefined}
                isMock={isMock}
                autoRefresh={!isMock}
              />
            )}

            {/* ── SETTINGS ─────────────────────────────────────────── */}
            {activeSection === 'settings' && store && (
              <div className="max-w-md space-y-6">
                <PriceThresholdControl
                  store={store}
                  onUpdated={setStore}
                  isMock={isMock}
                />

                {/* Store info */}
                <div className="rounded-xl border border-gray-200 bg-white shadow-sm overflow-hidden">
                  <div className="px-5 py-4 border-b border-gray-100">
                    <h3 className="font-semibold text-gray-900 text-sm">Store Information</h3>
                  </div>
                  <div className="px-5 py-4 space-y-3 text-sm">
                    <div>
                      <span className="text-xs text-gray-500">Store name</span>
                      <p className="font-medium">{store.name}</p>
                    </div>
                    <div>
                      <span className="text-xs text-gray-500">Owner</span>
                      <p className="font-medium">{store.owner_name}</p>
                    </div>
                    <div>
                      <span className="text-xs text-gray-500">GST Number</span>
                      <p className="font-medium">{store.gst_number ?? <span className="text-gray-400">Not provided</span>}</p>
                    </div>
                  </div>
                </div>

                <div className="rounded-xl border border-gray-200 bg-white shadow-sm px-5 py-4">
                  <h3 className="font-semibold text-gray-900 text-sm mb-2">About this prototype</h3>
                  <div className="text-xs text-gray-500 space-y-1">
                    <p>🏪 Shopify integration uses a development store only.</p>
                    <p>🤖 AI uses Goedel Machines OpenAI-compatible endpoint.</p>
                    <p>🚫 No live Paytm production data is used.</p>
                    <p>📋 All actions are audited and logged locally.</p>
                  </div>
                </div>
              </div>
            )}
          </>
        )}
      </main>
    </div>
  )
}
