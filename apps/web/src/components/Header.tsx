import { useState, useEffect } from 'react'
import { Wifi, WifiOff, Store } from 'lucide-react'
import { getChannels, getStore, extractApiError } from '../api/client'
import type { ChannelStatus, Store as StoreType } from '../types/contracts'
import { MOCK_CHANNELS, MOCK_STORE } from '../api/mockData'
import { StatusBadge } from './StatusBadge'

interface HeaderProps {
  isMock: boolean
  onToggleMock: () => void
  store?: StoreType
}

export function Header({ isMock, onToggleMock, store }: HeaderProps) {
  const [channels, setChannels] = useState<ChannelStatus[]>([])
  const [apiOnline, setApiOnline] = useState<boolean | null>(null)

  useEffect(() => {
    if (isMock) {
      setChannels(MOCK_CHANNELS)
      setApiOnline(false)
      return
    }

    async function load() {
      try {
        const [ch] = await Promise.all([getChannels()])
        setChannels(ch)
        setApiOnline(true)
      } catch {
        setApiOnline(false)
        setChannels(MOCK_CHANNELS)
      }
    }
    load()
  }, [isMock])

  const shopify = channels.find(c => c.channel === 'shopify')

  return (
    <header className="bg-white border-b border-gray-200 sticky top-0 z-10">
      <div className="max-w-5xl mx-auto px-4 sm:px-6 py-3 flex items-center justify-between gap-4">
        {/* Logo + store name */}
        <div className="flex items-center gap-3">
          <div className="bg-gradient-to-br from-blue-600 to-blue-800 text-white rounded-lg px-2.5 py-1 font-bold text-lg leading-none">
            SB
          </div>
          <div>
            <h1 className="font-bold text-gray-900 leading-none">SabBazaar</h1>
            {store && (
              <div className="flex items-center gap-1 text-xs text-gray-500 mt-0.5">
                <Store className="w-3 h-3" />
                {store.name}
              </div>
            )}
          </div>
        </div>

        {/* Right side — status indicators */}
        <div className="flex items-center gap-3">
          {shopify && (
            <div className="hidden sm:flex items-center gap-1.5 text-xs">
              <span className={`w-2 h-2 rounded-full ${shopify.connected ? 'bg-green-500' : 'bg-gray-300'}`} />
              <span className="text-gray-600">{shopify.connected ? 'Shopify connected' : 'Shopify not connected'}</span>
            </div>
          )}

          {/* API health */}
          <div className="flex items-center gap-1.5 text-xs">
            {apiOnline === null ? null : apiOnline ? (
              <>
                <Wifi className="w-4 h-4 text-green-500" />
                <span className="hidden sm:inline text-gray-500">API online</span>
              </>
            ) : (
              <>
                <WifiOff className="w-4 h-4 text-orange-400" />
                <span className="hidden sm:inline text-orange-600">API offline</span>
              </>
            )}
          </div>

          {/* Mock toggle */}
          <button
            onClick={onToggleMock}
            className={`text-xs rounded-lg px-2.5 py-1.5 border font-medium transition-colors ${
              isMock
                ? 'bg-purple-50 text-purple-700 border-purple-200 hover:bg-purple-100'
                : 'bg-gray-50 text-gray-600 border-gray-200 hover:bg-gray-100'
            }`}
          >
            {isMock ? '🎭 Demo mode' : 'Demo mode'}
          </button>
        </div>
      </div>
    </header>
  )
}
