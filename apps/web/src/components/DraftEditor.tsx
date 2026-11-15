import { useState } from 'react'
import { AlertTriangle, CheckCircle, Edit2, ChevronDown, ChevronUp } from 'lucide-react'
import { clsx } from 'clsx'
import type { Product, ProductPatch } from '../types/contracts'
import { patchProduct, extractApiError } from '../api/client'
import { StatusBadge } from './StatusBadge'
import { Alert } from './Alert'
import { Spinner } from './Spinner'

interface DraftEditorProps {
  product: Product
  onUpdated: (product: Product) => void
  onApprove: (product: Product) => void
  isMock?: boolean
}

export function DraftEditor({ product, onUpdated, onApprove, isMock }: DraftEditorProps) {
  const [expanded, setExpanded] = useState(true)
  const [editing, setEditing] = useState(false)
  const [form, setForm] = useState({
    title: product.title,
    description: product.description ?? '',
    price_inr: product.price_inr?.toString() ?? '',
    category: product.category ?? '',
    tags: product.tags.join(', '),
  })
  const [saving, setSaving] = useState(false)
  const [approving, setApproving] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const hasMissing = product.missing_fields.length > 0
  const isApprovable = product.status === 'draft' && !hasMissing && product.price_inr !== null && product.title.trim().length > 0
  const isAlreadyApproved = product.status === 'approved'

  async function handleSave() {
    if (isMock) {
      // Optimistic update in mock mode
      const updated: Product = {
        ...product,
        title: form.title,
        description: form.description || null,
        price_inr: form.price_inr ? parseFloat(form.price_inr) : null,
        category: form.category || null,
        tags: form.tags.split(',').map(t => t.trim()).filter(Boolean),
        missing_fields: product.missing_fields.filter(f =>
          !(f.field === 'description' && form.description) &&
          !(f.field === 'price_inr' && form.price_inr)
        ),
        version: product.version + 1,
        updated_at: new Date().toISOString(),
      }
      onUpdated(updated)
      setEditing(false)
      return
    }

    setSaving(true)
    setError(null)
    try {
      const patch: ProductPatch = {
        title: form.title,
        description: form.description || undefined,
        price_inr: form.price_inr ? parseFloat(form.price_inr) : undefined,
        category: form.category || undefined,
        tags: form.tags.split(',').map(t => t.trim()).filter(Boolean),
        version: product.version,
      }
      const updated = await patchProduct(product.id, patch)
      onUpdated(updated)
      setEditing(false)
    } catch (err) {
      setError(extractApiError(err))
    } finally {
      setSaving(false)
    }
  }

  async function handleApprove() {
    if (isMock) {
      const approved: Product = { ...product, status: 'approved', version: product.version + 1 }
      onApprove(approved)
      return
    }
    setApproving(true)
    setError(null)
    try {
      onApprove(product)
    } catch (err) {
      setError(extractApiError(err))
    } finally {
      setApproving(false)
    }
  }

  return (
    <div className={clsx(
      'rounded-xl border bg-white shadow-sm overflow-hidden',
      hasMissing && product.status === 'draft' ? 'border-yellow-200' : 'border-gray-200',
      isAlreadyApproved && 'border-green-200',
    )}>
      {/* Header */}
      <div
        className="flex items-start justify-between gap-3 px-5 py-4 cursor-pointer hover:bg-gray-50 transition-colors"
        onClick={() => setExpanded(e => !e)}
      >
        <div className="flex-1 min-w-0">
          <div className="flex flex-wrap items-center gap-2 mb-1">
            <StatusBadge status={product.status} />
            {product.stock_on_hand !== undefined && (
              <span className="inline-flex items-center text-xs text-blue-700 bg-blue-50 border border-blue-200 rounded-full px-2 py-0.5">
                Stock: {product.stock_on_hand}
              </span>
            )}
            {hasMissing && (
              <span className="inline-flex items-center gap-1 text-xs text-yellow-700 bg-yellow-50 border border-yellow-200 rounded-full px-2 py-0.5">
                <AlertTriangle className="w-3 h-3" />
                {product.missing_fields.length} field{product.missing_fields.length > 1 ? 's' : ''} missing
              </span>
            )}
            {product.confidence !== null && (
              <span className="text-xs text-gray-400">
                AI confidence: {Math.round(product.confidence * 100)}%
              </span>
            )}
          </div>
          <h3 className="font-semibold text-gray-900 truncate">
            {product.title || <span className="text-gray-400 italic">Untitled product</span>}
          </h3>
          {product.price_inr !== null && (
            <p className="text-sm text-gray-500 mt-0.5">₹{product.price_inr.toLocaleString('en-IN')}</p>
          )}
        </div>
        <div className="flex items-center gap-2 flex-shrink-0">
          {expanded ? <ChevronUp className="w-4 h-4 text-gray-400" /> : <ChevronDown className="w-4 h-4 text-gray-400" />}
        </div>
      </div>

      {/* Body */}
      {expanded && (
        <div className="border-t border-gray-100 px-5 py-4 space-y-4">

          {/* Missing fields warnings */}
          {hasMissing && (
            <div className="space-y-1">
              {product.missing_fields.map(mf => (
                <div key={mf.field} className="flex items-start gap-2 text-sm text-yellow-800 bg-yellow-50 border border-yellow-100 rounded-lg px-3 py-2">
                  <AlertTriangle className="w-4 h-4 flex-shrink-0 mt-0.5 text-yellow-500" />
                  <span><strong>{mf.field}:</strong> {mf.reason}</span>
                </div>
              ))}
            </div>
          )}

          {/* AI Evidence */}
          {product.evidence && (
            <p className="text-xs text-gray-500 bg-gray-50 rounded-lg px-3 py-2 border border-gray-100">
              <span className="font-medium text-gray-600">AI evidence:</span> {product.evidence}
            </p>
          )}

          {/* Fields */}
          {editing ? (
            <div className="space-y-3">
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">Title *</label>
                <input
                  value={form.title}
                  onChange={e => setForm(f => ({ ...f, title: e.target.value }))}
                  className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="Product title"
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">Description</label>
                <textarea
                  value={form.description}
                  onChange={e => setForm(f => ({ ...f, description: e.target.value }))}
                  rows={3}
                  className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none"
                  placeholder="Describe this product…"
                />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-medium text-gray-600 mb-1">Price (₹) *</label>
                  <input
                    type="number"
                    value={form.price_inr}
                    onChange={e => setForm(f => ({ ...f, price_inr: e.target.value }))}
                    className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                    placeholder="e.g. 3500"
                    min="0"
                    step="1"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-600 mb-1">Category</label>
                  <input
                    value={form.category}
                    onChange={e => setForm(f => ({ ...f, category: e.target.value }))}
                    className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                    placeholder="e.g. Sarees"
                  />
                </div>
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">Tags (comma-separated)</label>
                <input
                  value={form.tags}
                  onChange={e => setForm(f => ({ ...f, tags: e.target.value }))}
                  className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="silk, wedding, festive"
                />
              </div>

              {error && <Alert type="error" message={error} onDismiss={() => setError(null)} />}

              <div className="flex gap-2">
                <button
                  onClick={handleSave}
                  disabled={saving}
                  className="flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 transition-colors disabled:opacity-60"
                >
                  {saving && <Spinner size="sm" className="border-white border-t-transparent" />}
                  Save changes
                </button>
                <button
                  onClick={() => { setEditing(false); setError(null) }}
                  className="rounded-lg border border-gray-200 px-4 py-2 text-sm text-gray-600 hover:bg-gray-50 transition-colors"
                >
                  Cancel
                </button>
              </div>
            </div>
          ) : (
            <div className="space-y-2">
              <div className="grid grid-cols-2 gap-x-6 gap-y-2 text-sm">
                <div>
                  <span className="text-xs text-gray-500 block">Price</span>
                  <span className="font-medium">
                    {product.price_inr ? `₹${product.price_inr.toLocaleString('en-IN')}` : <span className="text-yellow-600 text-xs">Not set</span>}
                  </span>
                </div>
                <div>
                  <span className="text-xs text-gray-500 block">Category</span>
                  <span className="font-medium">{product.category ?? <span className="text-gray-400 text-xs">—</span>}</span>
                </div>
                {product.description && (
                  <div className="col-span-2">
                    <span className="text-xs text-gray-500 block">Description</span>
                    <span>{product.description}</span>
                  </div>
                )}
                {product.tags.length > 0 && (
                  <div className="col-span-2">
                    <span className="text-xs text-gray-500 block mb-1">Tags</span>
                    <div className="flex flex-wrap gap-1">
                      {product.tags.map(t => (
                        <span key={t} className="text-xs bg-gray-100 text-gray-600 rounded px-2 py-0.5">{t}</span>
                      ))}
                    </div>
                  </div>
                )}
              </div>

              {/* Actions */}
              {error && <Alert type="error" message={error} onDismiss={() => setError(null)} />}

              <div className="flex flex-wrap gap-2 pt-2">
                {!isAlreadyApproved && (
                  <button
                    onClick={() => setEditing(true)}
                    className="flex items-center gap-1.5 rounded-lg border border-gray-200 px-3 py-2 text-sm text-gray-600 hover:bg-gray-50 transition-colors"
                  >
                    <Edit2 className="w-3.5 h-3.5" />
                    Edit
                  </button>
                )}

                {!isAlreadyApproved && (
                  <button
                    onClick={handleApprove}
                    disabled={!isApprovable || approving}
                    title={!isApprovable ? 'Fill in missing fields before approving' : undefined}
                    className={clsx(
                      'flex items-center gap-1.5 rounded-lg px-3 py-2 text-sm font-medium transition-colors',
                      isApprovable
                        ? 'bg-green-600 text-white hover:bg-green-700'
                        : 'bg-gray-100 text-gray-400 cursor-not-allowed',
                    )}
                  >
                    {approving
                      ? <Spinner size="sm" className="border-white border-t-transparent" />
                      : <CheckCircle className="w-3.5 h-3.5" />
                    }
                    Approve for publication
                  </button>
                )}

                {isAlreadyApproved && (
                  <div className="flex items-center gap-1.5 text-sm text-green-700">
                    <CheckCircle className="w-4 h-4" />
                    Approved — ready to publish
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
