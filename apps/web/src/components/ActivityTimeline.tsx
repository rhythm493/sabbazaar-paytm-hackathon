import { useState, useEffect, useCallback } from 'react'
import { RefreshCw, Package, ShoppingBag, Box, CheckCircle, XCircle, Upload, Send } from 'lucide-react'
import { getActivity, extractApiError } from '../api/client'
import type { ActivityEvent, AuditEventType } from '../types/contracts'
import { LoadingState } from './Spinner'
import { EmptyState } from './Alert'

const EVENT_ICONS: Partial<Record<AuditEventType, React.ReactNode>> = {
  'ingestion.requested':      <Upload className="w-4 h-4" />,
  'ingestion.completed':      <Package className="w-4 h-4" />,
  'catalogue.draft.created':  <Box className="w-4 h-4" />,
  'product.approved':         <CheckCircle className="w-4 h-4" />,
  'product.rejected':         <XCircle className="w-4 h-4" />,
  'listing.publish.requested':<Send className="w-4 h-4" />,
  'listing.published':        <CheckCircle className="w-4 h-4" />,
  'listing.failed':           <XCircle className="w-4 h-4" />,
  'channel.order.received':   <ShoppingBag className="w-4 h-4" />,
}

const EVENT_COLOR: Partial<Record<AuditEventType, string>> = {
  'ingestion.completed':      'text-blue-600 bg-blue-50',
  'catalogue.draft.created':  'text-blue-600 bg-blue-50',
  'product.approved':         'text-green-600 bg-green-50',
  'product.rejected':         'text-gray-500 bg-gray-50',
  'listing.published':        'text-emerald-600 bg-emerald-50',
  'listing.failed':           'text-red-600 bg-red-50',
  'channel.order.received':   'text-purple-600 bg-purple-50',
}

function formatRelativeTime(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime()
  if (diff < 60_000) return 'just now'
  if (diff < 3_600_000) return `${Math.floor(diff / 60_000)}m ago`
  if (diff < 86_400_000) return `${Math.floor(diff / 3_600_000)}h ago`
  return new Date(iso).toLocaleDateString('en-IN')
}

interface ActivityTimelineProps {
  events?: ActivityEvent[]   // pass mock events directly
  isMock?: boolean
  autoRefresh?: boolean
}

export function ActivityTimeline({ events: mockEvents, isMock, autoRefresh = true }: ActivityTimelineProps) {
  const [events, setEvents] = useState<ActivityEvent[]>(mockEvents ?? [])
  const [loading, setLoading] = useState(!isMock)
  const [error, setError] = useState<string | null>(null)

  // Keep events in sync if parent passes updated mock events
  useEffect(() => {
    if (isMock && mockEvents) {
      setEvents(mockEvents)
    }
  }, [isMock, mockEvents])

  const fetchEvents = useCallback(async () => {
    if (isMock) return
    try {
      const data = await getActivity(50)
      setEvents(data)
      setError(null)
    } catch (err) {
      setError(extractApiError(err))
    } finally {
      setLoading(false)
    }
  }, [isMock])

  useEffect(() => {
    fetchEvents()
  }, [fetchEvents])

  // Auto-refresh every 5s for live API
  useEffect(() => {
    if (!autoRefresh || isMock) return
    const interval = setInterval(fetchEvents, 5000)
    return () => clearInterval(interval)
  }, [autoRefresh, isMock, fetchEvents])

  if (loading) return <LoadingState message="Loading activity…" />

  return (
    <div className="rounded-xl border border-gray-200 bg-white shadow-sm overflow-hidden">
      <div className="flex items-center justify-between px-5 py-4 border-b border-gray-100">
        <div>
          <h3 className="font-semibold text-gray-900">Activity</h3>
          <p className="text-xs text-gray-500 mt-0.5">Every action is audited and logged</p>
        </div>
        {!isMock && (
          <button
            onClick={fetchEvents}
            className="p-1.5 rounded-lg text-gray-400 hover:text-gray-600 hover:bg-gray-100 transition-colors"
            title="Refresh"
          >
            <RefreshCw className="w-4 h-4" />
          </button>
        )}
      </div>

      {error && (
        <div className="px-5 py-3 bg-red-50 border-b border-red-100 text-xs text-red-600">
          Could not load activity: {error}
        </div>
      )}

      {events.length === 0 ? (
        <EmptyState
          title="No activity yet"
          description="Upload a product image or use the demo fixture to get started."
        />
      ) : (
        <div className="divide-y divide-gray-50">
          {events.map((event, i) => {
            const icon = EVENT_ICONS[event.event_type]
            const colorClass = EVENT_COLOR[event.event_type] ?? 'text-gray-500 bg-gray-50'

            return (
              <div key={event.id} className="flex items-start gap-3 px-5 py-3">
                {/* Timeline line */}
                <div className="flex flex-col items-center flex-shrink-0">
                  <div className={`w-7 h-7 rounded-full flex items-center justify-center ${colorClass}`}>
                    {icon ?? <div className="w-2 h-2 rounded-full bg-current" />}
                  </div>
                  {i < events.length - 1 && (
                    <div className="w-px flex-1 bg-gray-100 mt-1 min-h-[12px]" />
                  )}
                </div>

                <div className="flex-1 min-w-0 pb-1">
                  <p className="text-sm text-gray-800 leading-snug">{event.summary}</p>
                  <p className="text-xs text-gray-400 mt-0.5">{formatRelativeTime(event.occurred_at)}</p>
                </div>
              </div>
            )
          })}
        </div>
      )}

      {isMock && (
        <div className="px-5 py-2 bg-purple-50 border-t border-purple-100">
          <p className="text-xs text-purple-600">🎭 Demo mode — activity from fixture data</p>
        </div>
      )}
    </div>
  )
}
