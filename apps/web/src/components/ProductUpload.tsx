import { useState, useRef } from 'react'
import { Upload, Image, FileText, Zap } from 'lucide-react'
import { clsx } from 'clsx'
import { createIngestion, createIngestionFromFixture, extractApiError } from '../api/client'
import type { Ingestion } from '../types/contracts'
import { MOCK_INGESTION } from '../api/mockData'
import { Alert } from './Alert'
import { Spinner } from './Spinner'

interface ProductUploadProps {
  onIngestionStarted: (ingestion: Ingestion) => void
  useMockData?: boolean
  onUseMock?: () => void
  isMock?: boolean
}

const ACCEPTED = ['image/jpeg', 'image/png', 'image/webp', 'application/pdf']
const MAX_SIZE_MB = 10

export function ProductUpload({ onIngestionStarted, useMockData, onUseMock, isMock }: ProductUploadProps) {
  const [isDragging, setIsDragging] = useState(false)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)

  function validateFile(file: File): string | null {
    if (!ACCEPTED.includes(file.type)) {
      return `Unsupported file type (${file.type}). Please upload a JPG, PNG, WebP, or PDF.`
    }
    if (file.size > MAX_SIZE_MB * 1024 * 1024) {
      return `File is too large (${(file.size / 1024 / 1024).toFixed(1)} MB). Maximum is ${MAX_SIZE_MB} MB.`
    }
    return null
  }

  async function handleFile(file: File) {
    const validationError = validateFile(file)
    if (validationError) {
      setError(validationError)
      return
    }
    setError(null)
    setIsLoading(true)

    if (isMock) {
      setTimeout(() => {
        setIsLoading(false)
        onIngestionStarted({
          ...MOCK_INGESTION,
          id: `ing-${Date.now()}`,
          file_name: file.name,
          file_type: file.type,
          created_at: new Date().toISOString(),
        })
      }, 800)
      return
    }

    try {
      const ingestion = await createIngestion(file)
      onIngestionStarted(ingestion)
    } catch (err) {
      setError(extractApiError(err))
    } finally {
      setIsLoading(false)
    }
  }

  async function handleFixture() {
    setError(null)
    setIsLoading(true)

    if (isMock) {
      setTimeout(() => {
        setIsLoading(false)
        onIngestionStarted({
          ...MOCK_INGESTION,
          id: `ing-fixture-${Date.now()}`,
          created_at: new Date().toISOString(),
        })
      }, 500)
      return
    }

    try {
      const ingestion = await createIngestionFromFixture('saree_sample')
      onIngestionStarted(ingestion)
    } catch (err) {
      setError(extractApiError(err))
    } finally {
      setIsLoading(false)
    }
  }

  function handleDrop(e: React.DragEvent) {
    e.preventDefault()
    setIsDragging(false)
    const file = e.dataTransfer.files[0]
    if (file) handleFile(file)
  }

  function handleChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0]
    if (file) handleFile(file)
  }

  return (
    <div className="space-y-4">
      {/* Drop zone */}
      <div
        onDragOver={(e) => { e.preventDefault(); setIsDragging(true) }}
        onDragLeave={() => setIsDragging(false)}
        onDrop={handleDrop}
        onClick={() => !isLoading && fileInputRef.current?.click()}
        className={clsx(
          'relative flex flex-col items-center justify-center gap-3 rounded-xl border-2 border-dashed p-10 cursor-pointer transition-colors',
          isDragging ? 'border-blue-500 bg-blue-50' : 'border-gray-200 bg-gray-50 hover:border-blue-300 hover:bg-blue-50/40',
          isLoading && 'pointer-events-none opacity-70',
        )}
      >
        {isLoading ? (
          <>
            <Spinner size="lg" />
            <p className="text-sm text-gray-500">Uploading and analysing with AI…</p>
          </>
        ) : (
          <>
            <Upload className="w-10 h-10 text-gray-400" />
            <div className="text-center">
              <p className="font-medium text-gray-700">Drop product photos or a bill here</p>
              <p className="text-sm text-gray-500 mt-1">JPG, PNG, WebP, PDF · Max {MAX_SIZE_MB} MB</p>
            </div>
            <div className="flex gap-3 mt-1 text-xs text-gray-400">
              <span className="flex items-center gap-1"><Image className="w-3 h-3" /> Photos</span>
              <span className="flex items-center gap-1"><FileText className="w-3 h-3" /> Bills / invoices</span>
            </div>
          </>
        )}
        <input
          ref={fileInputRef}
          type="file"
          accept={ACCEPTED.join(',')}
          onChange={handleChange}
          className="hidden"
        />
      </div>

      {error && (
        <Alert
          type="error"
          message={error}
          onDismiss={() => setError(null)}
        />
      )}

      {/* Divider */}
      <div className="flex items-center gap-3 text-xs text-gray-400">
        <div className="flex-1 border-t border-gray-200" />
        or use demo data
        <div className="flex-1 border-t border-gray-200" />
      </div>

      {/* Quick-start options */}
      <div className="flex flex-col sm:flex-row gap-2">
        <button
          onClick={handleFixture}
          disabled={isLoading}
          className="flex items-center justify-center gap-2 flex-1 rounded-lg border border-blue-200 bg-white px-4 py-2.5 text-sm font-medium text-blue-700 hover:bg-blue-50 transition-colors disabled:opacity-50"
        >
          <Zap className="w-4 h-4" />
          Use sample saree catalogue (fixture)
        </button>
        {useMockData && onUseMock && (
          <button
            onClick={onUseMock}
            className="flex items-center justify-center gap-2 flex-1 rounded-lg border border-purple-200 bg-white px-4 py-2.5 text-sm font-medium text-purple-700 hover:bg-purple-50 transition-colors"
          >
            Work offline (demo mode)
          </button>
        )}
      </div>

      <p className="text-xs text-center text-gray-400">
        No real Paytm data is used. Shopify integration uses a development store only.
      </p>
    </div>
  )
}
