import { useEffect, useRef, useState } from 'react'
import { Mic, Square, Send, Check, X, ShoppingBag } from 'lucide-react'

import type { Action } from '../types/contracts'
import {
  sendVoiceCommand,
  approveAction,
  rejectAction,
  getActions,
  extractApiError,
} from '../api/client'
import { MOCK_VOICE_ACTIONS, MOCK_VOICE_TRANSCRIPT } from '../api/mockData'
import { Alert } from './Alert'
import { Spinner } from './Spinner'

interface VoiceCommandPanelProps {
  isMock: boolean
}

const INTENT_LABELS: Record<string, string> = {
  set_price: 'Price change',
  set_stock: 'Set stock',
  adjust_stock: 'Adjust stock',
}

function pickMimeType(): string | undefined {
  if (typeof MediaRecorder === 'undefined') return undefined
  // Prefer bare MIME types (no ;codecs=… params) — the server and Sarvam reject parameterized types.
  const candidates = ['audio/webm', 'audio/ogg', 'audio/mp4']
  return candidates.find(t => MediaRecorder.isTypeSupported(t))
}

function payloadNumber(action: Action, key: string): number | null {
  const value = action.payload?.[key]
  return typeof value === 'number' ? value : null
}

function payloadString(action: Action, key: string): string | null {
  const value = action.payload?.[key]
  return typeof value === 'string' ? value : null
}

function formatChange(action: Action): string {
  const intent = payloadString(action, 'intent')
  if (intent === 'set_price') {
    const oldPrice = payloadNumber(action, 'price_inr_old')
    const newPrice = payloadNumber(action, 'price_inr_new')
    return `₹${oldPrice?.toLocaleString('en-IN') ?? '—'} → ₹${newPrice?.toLocaleString('en-IN') ?? '—'}`
  }
  if (intent === 'set_stock') {
    return `New stock: ${payloadNumber(action, 'quantity') ?? '—'} units`
  }
  if (intent === 'adjust_stock') {
    const delta = payloadNumber(action, 'delta')
    return `Stock delta: ${delta !== null && delta >= 0 ? '+' : ''}${delta ?? '—'} units`
  }
  return 'Inventory change'
}

export function VoiceCommandPanel({ isMock }: VoiceCommandPanelProps) {
  const [recording, setRecording] = useState(false)
  const [recordSeconds, setRecordSeconds] = useState(0)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [transcript, setTranscript] = useState<string | null>(null)
  const [message, setMessage] = useState<string | null>(null)
  const [unparsed, setUnparsed] = useState<string[]>([])
  const [actions, setActions] = useState<Action[]>([])
  const [typedText, setTypedText] = useState('')
  const [resolvingId, setResolvingId] = useState<string | null>(null)

  const mediaRecorderRef = useRef<MediaRecorder | null>(null)
  const streamRef = useRef<MediaStream | null>(null)
  const chunksRef = useRef<Blob[]>([])

  useEffect(() => {
    if (!recording) return
    const interval = window.setInterval(() => setRecordSeconds(s => s + 1), 1000)
    return () => window.clearInterval(interval)
  }, [recording])

  async function refresh() {
    if (isMock) return
    try {
      const pending = await getActions('awaiting_approval')
      setActions(pending)
    } catch (err) {
      console.error('Refreshing actions failed:', extractApiError(err))
    }
  }

  async function submitVoice(blob: Blob) {
    setSubmitting(true)
    setError(null)
    try {
      const res = await sendVoiceCommand(blob)
      applyResponse(res)
    } catch (err) {
      setError(extractApiError(err))
    } finally {
      setSubmitting(false)
    }
  }

  async function submitText() {
    const text = typedText.trim()
    if (!text) return
    setSubmitting(true)
    setError(null)
    try {
      if (isMock) {
        setTranscript(MOCK_VOICE_TRANSCRIPT)
        setMessage(`Proposed ${MOCK_VOICE_ACTIONS.length} changes — approve or reject them below.`)
        setUnparsed([])
        setActions(MOCK_VOICE_ACTIONS)
      } else {
        const res = await sendVoiceCommand(undefined, text)
        applyResponse(res)
      }
      setTypedText('')
    } catch (err) {
      setError(extractApiError(err))
    } finally {
      setSubmitting(false)
    }
  }

  function applyResponse(res: {
    transcript: string
    language_code?: string | null
    actions: Action[]
    unparsed: string[]
    message: string
  }) {
    setTranscript(res.transcript)
    setMessage(res.message)
    setActions(res.actions)
    setUnparsed(res.unparsed)
  }

  async function startRecording() {
    setError(null)
    if (isMock) {
      setRecording(true)
      setRecordSeconds(0)
      return
    }
    if (typeof navigator === 'undefined' || !navigator.mediaDevices?.getUserMedia) {
      setError('Microphone not available in this browser — type a command below instead.')
      return
    }
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      streamRef.current = stream
      const mimeType = pickMimeType()
      const recorder = mimeType ? new MediaRecorder(stream, { mimeType }) : new MediaRecorder(stream)
      chunksRef.current = []
      recorder.ondataavailable = event => {
        if (event.data.size > 0) chunksRef.current.push(event.data)
      }
      recorder.onstop = () => {
        streamRef.current?.getTracks().forEach(track => track.stop())
        streamRef.current = null
        const blob = new Blob(chunksRef.current, { type: mimeType ?? 'audio/webm' })
        if (blob.size > 0) submitVoice(blob)
      }
      recorder.start()
      mediaRecorderRef.current = recorder
      setRecordSeconds(0)
      setRecording(true)
    } catch {
      setError('Microphone access was denied — type a command below instead.')
    }
  }

  function stopRecording() {
    setRecording(false)
    if (isMock) {
      setTranscript(MOCK_VOICE_TRANSCRIPT)
      setMessage(`Proposed ${MOCK_VOICE_ACTIONS.length} changes — approve or reject them below.`)
      setUnparsed([])
      setActions(MOCK_VOICE_ACTIONS)
      return
    }
    const recorder = mediaRecorderRef.current
    if (recorder && recorder.state !== 'inactive') {
      recorder.stop()
    } else {
      streamRef.current?.getTracks().forEach(track => track.stop())
      streamRef.current = null
    }
    mediaRecorderRef.current = null
  }

  async function resolveAction(action: Action, decision: 'approve' | 'reject') {
    setResolvingId(action.id)
    setError(null)
    try {
      if (isMock) {
        const status = decision === 'approve' ? 'executed' : 'rejected'
        setActions(prev => prev.map(a => (a.id === action.id ? { ...a, status } : a)))
        return
      }
      if (decision === 'approve') {
        await approveAction(String(action.id))
      } else {
        await rejectAction(String(action.id))
      }
      await refresh()
    } catch (err) {
      setError(extractApiError(err))
    } finally {
      setResolvingId(null)
    }
  }

  const awaitingCount = actions.filter(a => a.status === 'awaiting_approval').length

  return (
    <div className="rounded-xl border border-gray-200 bg-white shadow-sm overflow-hidden">
      <div className="px-5 py-4 border-b border-gray-100 flex items-center gap-3">
        <div className="w-9 h-9 rounded-lg bg-blue-50 text-blue-600 flex items-center justify-center">
          <Mic className="w-5 h-5" />
        </div>
        <div>
          <h3 className="font-semibold text-gray-900 text-sm">Assistant — Voice &amp; Text Commands</h3>
          <p className="text-xs text-gray-500 mt-0.5">
            Say or type e.g. “stock of banarasi saree to 40” — nothing changes until you approve it.
          </p>
        </div>
      </div>

      <div className="px-5 py-4 space-y-4">
        {/* Mic button + timer */}
        <div className="flex flex-col items-center gap-2 py-2">
          {!recording ? (
            <button
              onClick={startRecording}
              disabled={submitting}
              className="w-20 h-20 rounded-full bg-blue-600 text-white flex items-center justify-center hover:bg-blue-700 transition-colors disabled:opacity-60 disabled:cursor-not-allowed shadow-sm"
              aria-label="Start recording"
            >
              <Mic className="w-8 h-8" />
            </button>
          ) : (
            <button
              onClick={stopRecording}
              className="w-20 h-20 rounded-full bg-red-600 text-white flex items-center justify-center hover:bg-red-700 transition-colors shadow-sm animate-pulse"
              aria-label="Stop recording"
            >
              <Square className="w-7 h-7" fill="currentColor" />
            </button>
          )}
          <p className="text-xs text-gray-500 tabular-nums">
            {recording ? `Recording… ${recordSeconds}s — tap to stop` : submitting ? 'Transcribing and parsing…' : 'Tap the mic and speak'}
          </p>
        </div>

        {/* Typed fallback — always available */}
        <div className="flex gap-2">
          <input
            type="text"
            value={typedText}
            onChange={e => setTypedText(e.target.value)}
            onKeyDown={e => { if (e.key === 'Enter') submitText() }}
            placeholder="or type a command…"
            disabled={submitting}
            className="flex-1 rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-600 focus:border-transparent disabled:opacity-60"
          />
          <button
            onClick={submitText}
            disabled={submitting || !typedText.trim()}
            className="flex items-center gap-1.5 rounded-lg bg-blue-600 px-3 py-2 text-sm font-medium text-white hover:bg-blue-700 transition-colors disabled:opacity-60 disabled:cursor-not-allowed"
          >
            {submitting ? <Spinner size="sm" className="border-white border-t-transparent" /> : <Send className="w-4 h-4" />}
            Send
          </button>
        </div>

        {error && <Alert type="error" message={error} onDismiss={() => setError(null)} />}

        {/* Transcript + parse message */}
        {transcript && (
          <div className="rounded-lg border border-gray-100 bg-gray-50 px-3 py-2 space-y-1">
            <p className="text-sm text-gray-700 italic">“{transcript}”</p>
            {message && <p className="text-xs text-gray-600">{message}</p>}
            {unparsed.length > 0 && (
              <ul className="text-xs text-amber-700 list-disc pl-4">
                {unparsed.map((note, i) => <li key={i}>{note}</li>)}
              </ul>
            )}
          </div>
        )}

        {/* Proposed actions */}
        {actions.length > 0 && (
          <div className="space-y-2">
            <p className="text-xs font-medium text-gray-600">
              Proposed changes{awaitingCount > 0 ? ` (${awaitingCount} pending)` : ''}
            </p>
            {actions.map(action => {
              const pending = action.status === 'awaiting_approval'
              const intent = payloadString(action, 'intent') ?? ''
              const title = payloadString(action, 'title') ?? `Action #${action.id}`
              const sku = payloadString(action, 'sku')
              const rationale = payloadString(action, 'rationale') ?? action.rationale
              return (
                <div
                  key={action.id}
                  className="rounded-lg border border-gray-200 p-3 space-y-2"
                >
                  <div className="flex items-start justify-between gap-3">
                    <div className="min-w-0">
                      <div className="flex items-center gap-2 flex-wrap">
                        <span className="text-xs font-semibold uppercase tracking-wide text-blue-700 bg-blue-50 border border-blue-200 rounded-full px-2 py-0.5">
                          {INTENT_LABELS[intent] ?? intent}
                        </span>
                        {sku && <span className="text-xs text-gray-500 font-mono">{sku}</span>}
                        <span className={`text-xs rounded-full px-2 py-0.5 border ${
                          action.status === 'executed' ? 'bg-green-50 text-green-700 border-green-200'
                          : action.status === 'rejected' ? 'bg-gray-50 text-gray-500 border-gray-200'
                          : action.status === 'awaiting_approval' ? 'bg-amber-50 text-amber-700 border-amber-200'
                          : 'bg-gray-50 text-gray-600 border-gray-200'
                        }`}>
                          {action.status.replace('_', ' ')}
                        </span>
                      </div>
                      <p className="text-sm font-medium text-gray-900 mt-1 truncate">{title}</p>
                      <p className="text-xs text-gray-700 mt-0.5">{formatChange(action)}</p>
                      {rationale && <p className="text-xs text-gray-500 mt-1">{rationale}</p>}
                    </div>
                    {pending && (
                      <div className="flex flex-col gap-1.5 flex-shrink-0">
                        <button
                          onClick={() => resolveAction(action, 'approve')}
                          disabled={resolvingId === action.id}
                          className="flex items-center gap-1 rounded-lg bg-green-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-green-700 transition-colors disabled:opacity-60 disabled:cursor-not-allowed"
                        >
                          {resolvingId === action.id ? <Spinner size="sm" className="border-white border-t-transparent" /> : <Check className="w-3.5 h-3.5" />}
                          Approve
                        </button>
                        <button
                          onClick={() => resolveAction(action, 'reject')}
                          disabled={resolvingId === action.id}
                          className="flex items-center gap-1 rounded-lg border border-gray-300 bg-white px-3 py-1.5 text-xs font-medium text-gray-700 hover:bg-gray-50 transition-colors disabled:opacity-60 disabled:cursor-not-allowed"
                        >
                          <X className="w-3.5 h-3.5" />
                          Reject
                        </button>
                      </div>
                    )}
                  </div>
                </div>
              )
            })}
          </div>
        )}

        {actions.length === 0 && transcript && (
          <div className="flex items-center gap-2 text-xs text-gray-500">
            <ShoppingBag className="w-4 h-4" /> No proposed changes from that command.
          </div>
        )}

        {isMock && (
          <p className="text-xs text-center text-purple-600">
            🎭 Demo mode — proposals and approvals are simulated locally
          </p>
        )}
      </div>
    </div>
  )
}
