import { useRef, useState, useEffect } from 'react'
import { Camera, ImagePlus, Loader2, X } from 'lucide-react'
import { clsx } from 'clsx'

import type { Product } from '../types/contracts'
import { createProductFromPhoto, extractApiError } from '../api/client'
import { Alert } from './Alert'

interface PhotoProductPanelProps {
  onCreated: (product: Product) => void
}

export function PhotoProductPanel({ onCreated }: PhotoProductPanelProps) {
  const [file, setFile] = useState<File | null>(null)
  const [previewUrl, setPreviewUrl] = useState<string | null>(null)
  const [dragging, setDragging] = useState(false)
  const [price, setPrice] = useState('')
  const [title, setTitle] = useState('')
  const [sku, setSku] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [createdTitle, setCreatedTitle] = useState<string | null>(null)
  const inputRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    if (!file) {
      setPreviewUrl(null)
      return
    }
    const url = URL.createObjectURL(file)
    setPreviewUrl(url)
    return () => URL.revokeObjectURL(url)
  }, [file])

  function handleFiles(list: FileList | null) {
    const picked = list?.[0]
    if (!picked) return
    if (!picked.type.startsWith('image/')) {
      setError('Please choose an image file (photo of a single product).')
      return
    }
    setError(null)
    setCreatedTitle(null)
    setFile(picked)
  }

  function reset() {
    setFile(null)
    setPrice('')
    setTitle('')
    setSku('')
    setError(null)
    if (inputRef.current) inputRef.current.value = ''
  }

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault()
    if (!file) {
      setError('Choose a product photo first.')
      return
    }
    setSubmitting(true)
    setError(null)
    setCreatedTitle(null)
    try {
      const product = await createProductFromPhoto(file, {
        priceInr: price.trim() === '' ? undefined : price.trim(),
        sku: sku.trim() || undefined,
        title: title.trim() || undefined,
      })
      setCreatedTitle(product.title)
      onCreated(product)
      reset()
    } catch (err) {
      setError(extractApiError(err))
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <section className="rounded-xl border border-gray-200 bg-white shadow-sm overflow-hidden">
      <div className="flex items-center gap-3 border-b border-gray-100 px-5 py-4">
        <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-blue-50 text-blue-600">
          <Camera className="w-5 h-5" />
        </div>
        <div>
          <h2 className="text-sm font-semibold text-gray-900">One product, one photo</h2>
          <p className="text-xs text-gray-500">Snap a photo — AI drafts the listing for you to review and approve.</p>
        </div>
      </div>

      <form onSubmit={handleSubmit} className="px-5 py-4 space-y-4">
        {error && <Alert type="error" message={error} onDismiss={() => setError(null)} />}
        {createdTitle && (
          <Alert type="success" message={`Draft created: “${createdTitle}” — review it in Products below and approve when it looks right.`} />
        )}

        {!file ? (
          <button
            type="button"
            onClick={() => inputRef.current?.click()}
            onDragOver={event => {
              event.preventDefault()
              setDragging(true)
            }}
            onDragLeave={() => setDragging(false)}
            onDrop={event => {
              event.preventDefault()
              setDragging(false)
              handleFiles(event.dataTransfer.files)
            }}
            className={clsx(
              'flex w-full flex-col items-center gap-2 rounded-lg border-2 border-dashed px-4 py-8 text-sm transition',
              dragging ? 'border-blue-400 bg-blue-50 text-blue-700' : 'border-gray-200 text-gray-500 hover:border-blue-300 hover:text-blue-600',
            )}
          >
            <ImagePlus className="w-7 h-7" />
            <span className="font-medium">Drop a product photo here, or click to choose</span>
            <span className="text-xs text-gray-400">PNG, JPEG or WebP · up to 10 MB</span>
          </button>
        ) : (
          <div className="flex items-start gap-4">
            <img src={previewUrl ?? ''} alt="Selected product" className="h-24 w-24 rounded-lg border border-gray-200 object-cover" />
            <div className="min-w-0 flex-1">
              <p className="truncate text-sm font-medium text-gray-900">{file.name}</p>
              <p className="text-xs text-gray-500">{(file.size / 1024).toFixed(0)} KB</p>
              <button
                type="button"
                onClick={reset}
                className="mt-2 inline-flex items-center gap-1 text-xs font-medium text-gray-500 hover:text-gray-700"
              >
                <X className="w-3.5 h-3.5" /> Choose a different photo
              </button>
            </div>
          </div>
        )}
        <input
          ref={inputRef}
          type="file"
          accept="image/*"
          capture="environment"
          className="hidden"
          onChange={event => handleFiles(event.target.files)}
        />

        <div className="grid gap-3 sm:grid-cols-3">
          <label className="block">
            <span className="text-xs font-medium text-gray-600">Price ₹</span>
            <input
              type="number"
              min="0"
              step="0.01"
              value={price}
              onChange={event => setPrice(event.target.value)}
              placeholder="799"
              className="mt-1 w-full rounded-lg border border-gray-200 px-3 py-2 text-sm focus:border-blue-400 focus:outline-none"
            />
          </label>
          <label className="block">
            <span className="text-xs font-medium text-gray-600">Title</span>
            <input
              type="text"
              value={title}
              onChange={event => setTitle(event.target.value)}
              placeholder="Auto-detect"
              className="mt-1 w-full rounded-lg border border-gray-200 px-3 py-2 text-sm focus:border-blue-400 focus:outline-none"
            />
          </label>
          <label className="block">
            <span className="text-xs font-medium text-gray-600">SKU</span>
            <input
              type="text"
              value={sku}
              onChange={event => setSku(event.target.value)}
              placeholder="Auto-generate"
              className="mt-1 w-full rounded-lg border border-gray-200 px-3 py-2 text-sm focus:border-blue-400 focus:outline-none"
            />
          </label>
        </div>
        <p className="text-xs text-gray-400">Price is required unless it is clearly printed in the photo. AI never invents a price.</p>

        <button
          type="submit"
          disabled={submitting || !file}
          className="inline-flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white transition hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-50"
        >
          {submitting ? <Loader2 className="h-4 w-4 animate-spin" /> : <Camera className="h-4 w-4" />}
          {submitting ? 'Reading the photo…' : 'Draft product from photo'}
        </button>
      </form>
    </section>
  )
}
