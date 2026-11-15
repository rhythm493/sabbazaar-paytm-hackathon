import { useState } from 'react'
import { Settings, AlertTriangle } from 'lucide-react'
import { updateStore, extractApiError } from '../api/client'
import type { Store } from '../types/contracts'
import { Alert } from './Alert'

interface PriceThresholdControlProps {
  store: Store
  onUpdated: (store: Store) => void
  isMock?: boolean
}

export function PriceThresholdControl({ store, onUpdated, isMock }: PriceThresholdControlProps) {
  const [threshold, setThreshold] = useState(store.price_change_threshold_pct)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [saved, setSaved] = useState(false)

  async function handleSave() {
    if (isMock) {
      onUpdated({ ...store, price_change_threshold_pct: threshold })
      setSaved(true)
      setTimeout(() => setSaved(false), 2000)
      return
    }
    setSaving(true)
    setError(null)
    try {
      const updated = await updateStore({ price_change_threshold_pct: threshold })
      onUpdated(updated)
      setSaved(true)
      setTimeout(() => setSaved(false), 2000)
    } catch (err) {
      setError(extractApiError(err))
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="rounded-xl border border-gray-200 bg-white shadow-sm overflow-hidden">
      <div className="flex items-center gap-2 px-5 py-4 border-b border-gray-100">
        <Settings className="w-4 h-4 text-gray-400" />
        <div>
          <h3 className="font-semibold text-gray-900 text-sm">Price Change Threshold</h3>
          <p className="text-xs text-gray-500">AI can change prices within this limit without approval</p>
        </div>
      </div>

      <div className="px-5 py-4 space-y-4">
        <div className="flex items-center gap-4">
          <div className="flex-1">
            <input
              type="range"
              min={1}
              max={50}
              value={threshold}
              onChange={e => setThreshold(Number(e.target.value))}
              className="w-full accent-blue-600"
            />
            <div className="flex justify-between text-xs text-gray-400 mt-1">
              <span>1%</span>
              <span>50%</span>
            </div>
          </div>
          <div className="flex-shrink-0 w-16 text-center">
            <span className="text-2xl font-bold text-blue-600">±{threshold}%</span>
          </div>
        </div>

        <div className="flex items-start gap-2 text-xs text-amber-700 bg-amber-50 border border-amber-100 rounded-lg px-3 py-2">
          <AlertTriangle className="w-3.5 h-3.5 flex-shrink-0 mt-0.5" />
          <span>
            Price changes beyond ±{threshold}% will require your approval before being applied to any channel.
          </span>
        </div>

        {error && <Alert type="error" message={error} onDismiss={() => setError(null)} />}
        {saved && <Alert type="success" message="Threshold saved." />}

        <button
          onClick={handleSave}
          disabled={saving || threshold === store.price_change_threshold_pct}
          className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 transition-colors disabled:opacity-60"
        >
          {saving ? 'Saving…' : 'Save threshold'}
        </button>
      </div>
    </div>
  )
}
