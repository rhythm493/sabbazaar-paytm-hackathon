import { useEffect, useRef, useState } from 'react'
import {
  Upload,
  Receipt,
  CheckCircle2,
  AlertTriangle,
  Trash2,
  RotateCcw,
  ExternalLink,
  Loader2,
} from 'lucide-react'

import type { BillIngestionView, BillAnswer, BillJob } from '../types/contracts'
import {
  uploadBill,
  getBillIngestion,
  answerBillQuestions,
  editBillPreview,
  confirmBillPreview,
  retryBillIngestion,
  rejectBillIngestion,
  extractApiError,
} from '../api/client'
import { MOCK_BILL_NEEDS_INPUT, MOCK_BILL_AWAITING_CONFIRMATION, MOCK_BILL_COMPLETED } from '../api/mockData'
import { Alert } from './Alert'
import { Spinner } from './Spinner'

interface BillIntakePanelProps {
  isMock: boolean
}

const MAX_BYTES = 10 * 1024 * 1024
const POLL_STATUSES = ['received', 'extracting', 'checking']
const POLL_TIMEOUT_MS = 120_000

function mockCopy(base: BillIngestionView, id: string): BillIngestionView {
  return {
    ...structuredClone(base),
    id,
    preview: base.preview ? { ...structuredClone(base.preview) } : null,
    jobs: base.jobs.map((j, i) => ({ ...j, id: `mock-job-${id}-${i}` })),
  }
}

function jobChip(job: BillJob) {
  const ok = job.status === 'succeeded'
  const bad = job.status === 'retryable_failure' || job.status === 'terminal_failure'
  const cls = ok
    ? 'bg-green-50 text-green-700 border-green-200'
    : bad
      ? 'bg-amber-50 text-amber-700 border-amber-200'
      : 'bg-gray-100 text-gray-600 border-gray-200'
  return (
    <span className={`inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-xs font-medium ${cls}`}>
      {job.status}
    </span>
  )
}

export function BillIntakePanel({ isMock }: BillIntakePanelProps) {
  const [view, setView] = useState<BillIngestionView | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState<string | null>(null)
  const [answers, setAnswers] = useState<Record<string, string>>({})
  const [priceDrafts, setPriceDrafts] = useState<Record<string, string>>({})
  const fileRef = useRef<HTMLInputElement | null>(null)
  const pollingSinceRef = useRef<number>(0)

  const status = view?.status ?? null
  const polling = status !== null && POLL_STATUSES.includes(status) && !isMock

  // Poll while extraction is in flight (mock mode advances via timeouts instead)
  useEffect(() => {
    if (!polling || !view) return
    if (!pollingSinceRef.current) pollingSinceRef.current = Date.now()
    const interval = window.setInterval(async () => {
      try {
        const next = await getBillIngestion(view.id)
        setView(next)
        if (Date.now() - pollingSinceRef.current > POLL_TIMEOUT_MS && POLL_STATUSES.includes(next.status)) {
          setError('Extraction is taking too long. Try again, or check the API logs.')
          setView(null)
        }
      } catch (err) {
        setError(extractApiError(err))
        window.clearInterval(interval)
      }
    }, 2000)
    return () => window.clearInterval(interval)
  }, [polling, view])

  useEffect(() => {
    if (!view?.preview) return
    const drafts: Record<string, string> = {}
    for (const line of view.preview.lines) drafts[line.line_id] = line.price_after
    setPriceDrafts(drafts)
  }, [view?.preview?.version])

  function reset() {
    setView(null)
    setError(null)
    setBusy(null)
    setAnswers({})
    setPriceDrafts({})
    pollingSinceRef.current = 0
    if (fileRef.current) fileRef.current.value = ''
  }

  async function handleFile(file: File) {
    setError(null)
    if (file.size > MAX_BYTES) {
      setError('Bill exceeds 10 MB. Please export a smaller image or PDF.')
      return
    }
    setBusy('upload')
    try {
      if (isMock) {
        await new Promise(resolve => window.setTimeout(resolve, 800))
        const id = `mock-bill-${Date.now()}`
        setView(mockCopy(MOCK_BILL_NEEDS_INPUT, id))
      } else {
        pollingSinceRef.current = Date.now()
        setView(await uploadBill(file))
      }
    } catch (err) {
      setError(extractApiError(err))
    } finally {
      setBusy(null)
    }
  }

  async function submitAnswers() {
    if (!view) return
    const payload: BillAnswer[] = view.questions.map(q => ({
      question_id: q.id,
      value: answers[q.id] ?? q.suggestion ?? null,
    }))
    const missing = view.questions.filter(
      q => q.blocking && !(answers[q.id] ?? q.suggestion ?? '').trim()
    )
    if (missing.length) {
      setError('Please answer every required question.')
      return
    }
    setBusy('answers')
    setError(null)
    try {
      if (isMock) {
        await new Promise(resolve => window.setTimeout(resolve, 600))
        setView(mockCopy(MOCK_BILL_AWAITING_CONFIRMATION, view.id))
      } else {
        setView(await answerBillQuestions(view.id, payload))
      }
      setAnswers({})
    } catch (err) {
      setError(extractApiError(err))
    } finally {
      setBusy(null)
    }
  }

  async function dropLine(lineId: string) {
    if (!view) return
    setBusy('drop')
    try {
      if (isMock) {
        // mock: no-op beyond UX — real backends remove the line from the preview
        setView(prev => (prev?.preview ? { ...prev, preview: { ...prev.preview, lines: prev.preview.lines.filter(l => l.line_id !== lineId), version: prev.preview.version + 1 } } : prev))
      } else {
        setView(await editBillPreview(view.id, lineId, {}, true))
      }
    } catch (err) {
      setError(extractApiError(err))
    } finally {
      setBusy(null)
    }
  }

  async function savePrice(lineId: string) {
    if (!view?.preview) return
    const value = (priceDrafts[lineId] ?? '').trim()
    if (!value) return
    setBusy(`price:${lineId}`)
    setError(null)
    try {
      if (isMock) {
        setView(prev =>
          prev?.preview
            ? {
                ...prev,
                preview: {
                  ...prev.preview,
                  version: prev.preview.version + 1,
                  lines: prev.preview.lines.map(l => (l.line_id === lineId ? { ...l, price_after: value } : l)),
                },
              }
            : prev
        )
      } else {
        setView(await editBillPreview(view.id, lineId, { selling_price: value }))
      }
    } catch (err) {
      setError(extractApiError(err))
    } finally {
      setBusy(null)
    }
  }

  async function confirm() {
    if (!view?.preview) return
    setBusy('confirm')
    setError(null)
    try {
      if (isMock) {
        await new Promise(resolve => window.setTimeout(resolve, 900))
        setView(mockCopy(MOCK_BILL_COMPLETED, view.id))
      } else {
        setView(await confirmBillPreview(view.id, view.preview.version))
      }
    } catch (err) {
      setError(extractApiError(err))
    } finally {
      setBusy(null)
    }
  }

  async function retry() {
    if (!view) return
    setBusy('retry')
    setError(null)
    try {
      if (isMock) {
        await new Promise(resolve => window.setTimeout(resolve, 700))
        setView(mockCopy(MOCK_BILL_NEEDS_INPUT, view.id))
      } else {
        pollingSinceRef.current = Date.now()
        setView(await retryBillIngestion(view.id))
      }
    } catch (err) {
      setError(extractApiError(err))
    } finally {
      setBusy(null)
    }
  }

  async function reject() {
    if (!view) return
    setBusy('reject')
    setError(null)
    try {
      if (isMock) {
        setView(prev => (prev ? { ...prev, status: 'rejected' } : prev))
      } else {
        setView(await rejectBillIngestion(view.id))
      }
    } catch (err) {
      setError(extractApiError(err))
    } finally {
      setBusy(null)
    }
  }

  // ─── Render ────────────────────────────────────────────────────────────

  const fallbackBanner = view?.fallback_used ? (
    <Alert type="info" message="Extraction used recorded fixtures — verify every line below." />
  ) : null

  // Idle uploader
  if (!view) {
    return (
      <div className="rounded-xl border border-gray-200 bg-white shadow-sm overflow-hidden">
        <div className="flex items-center gap-2 border-b border-gray-100 px-5 py-4">
          <Receipt className="h-5 w-5 text-blue-600" />
          <h2 className="font-semibold text-gray-900">Bill intake</h2>
        </div>
        <div className="p-6">
          {error && <Alert type="error" message={error} />}
          <p className="text-sm text-gray-600 mb-4">
            Upload a supplier bill (PNG, JPEG, WEBP or PDF). SabBazaar extracts the lines with AI, asks for anything
            unclear, and only creates draft Shopify products after you approve the preview.
          </p>
          <button
            type="button"
            onClick={() => fileRef.current?.click()}
            disabled={busy === 'upload'}
            className="flex w-full flex-col items-center justify-center rounded-lg border-2 border-dashed border-gray-300 bg-gray-50 px-6 py-10 text-center transition hover:border-blue-400 hover:bg-blue-50 disabled:opacity-60"
          >
            {busy === 'upload' ? (
              <Spinner size="md" className="mb-3" />
            ) : (
              <Upload className="mb-3 h-8 w-8 text-blue-500" />
            )}
            <span className="text-sm font-medium text-gray-900">
              {busy === 'upload' ? 'Sending your bill…' : 'Click to upload a bill'}
            </span>
            <span className="mt-1 text-xs text-gray-500">PNG, JPEG, WEBP or PDF · max 10 MB</span>
          </button>
          <input
            ref={fileRef}
            type="file"
            accept=".png,.jpg,.jpeg,.webp,.pdf,image/png,image/jpeg,image/webp,application/pdf"
            className="hidden"
            onChange={e => {
              const file = e.target.files?.[0]
              if (file) void handleFile(file)
            }}
          />
        </div>
      </div>
    )
  }

  // Any active ingestion
  return (
    <div className="rounded-xl border border-gray-200 bg-white shadow-sm overflow-hidden">
      <div className="flex items-center justify-between border-b border-gray-100 px-5 py-4">
        <div className="flex min-w-0 items-center gap-2">
          <Receipt className="h-5 w-5 shrink-0 text-blue-600" />
          <h2 className="font-semibold text-gray-900">Bill intake</h2>
          <span className="truncate font-mono text-xs text-gray-400" title={view.filename ?? ''}>
            {view.filename}
          </span>
        </div>
        <button
          type="button"
          onClick={reset}
          className="shrink-0 rounded-lg px-3 py-1.5 text-sm font-medium text-gray-600 transition hover:bg-gray-100"
        >
          Analyse another bill
        </button>
      </div>

      <div className="space-y-4 p-5">
        {error && <Alert type="error" message={error} onDismiss={() => setError(null)} />}
        {fallbackBanner}

        {/* In-flight */}
        {POLL_STATUSES.includes(status ?? '') && (
          <div className="flex items-center gap-3 rounded-lg border border-blue-100 bg-blue-50 px-4 py-3 text-sm text-blue-800">
            <Loader2 className="h-4 w-4 animate-spin" />
            Analysing your bill with AI… this can take 15–45 seconds.
          </div>
        )}

        {/* Needs input */}
        {status === 'needs_input' && (
          <>
            <div className="overflow-hidden rounded-lg border border-gray-100">
              <table className="min-w-full text-sm">
                <thead className="bg-gray-50 text-left text-xs uppercase tracking-wide text-gray-500">
                  <tr>
                    <th className="px-3 py-2">Line</th>
                    <th className="px-3 py-2">Item</th>
                    <th className="px-3 py-2 text-right">Qty</th>
                    <th className="px-3 py-2 text-right">MRP</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {view.lines.map(line => (
                    <tr key={line.id}>
                      <td className="px-3 py-2 font-mono text-xs text-gray-500">{line.id}</td>
                      <td className="px-3 py-2 text-gray-900">{String(line.fields.title?.value ?? '—')}</td>
                      <td className="px-3 py-2 text-right text-gray-700">{String(line.fields.quantity?.value ?? '—')}</td>
                      <td className="px-3 py-2 text-right text-gray-700">
                        {line.fields.mrp?.value != null ? `₹${String(line.fields.mrp.value)}` : '—'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <div className="space-y-3">
              {view.questions.map(q => (
                <div key={q.id} className="rounded-lg border border-gray-100 bg-gray-50 p-3">
                  <label className="mb-1 block text-sm font-medium text-gray-900">{q.prompt}</label>
                  <div className="flex items-center gap-2">
                    <input
                      type="text"
                      inputMode="decimal"
                      value={answers[q.id] ?? q.suggestion ?? ''}
                      onChange={e => setAnswers(prev => ({ ...prev, [q.id]: e.target.value }))}
                      placeholder={q.suggestion ? `Suggestion: ${q.suggestion}` : 'Your answer'}
                      className="w-48 rounded-lg border border-gray-300 px-3 py-2 text-sm outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
                    />
                    {q.allow_drop && (
                      <button
                        type="button"
                        onClick={() => void dropLine(q.line_id)}
                        disabled={busy !== null}
                        className="flex items-center gap-1 rounded-lg border border-gray-300 px-3 py-2 text-sm text-gray-600 transition hover:bg-gray-100 disabled:opacity-50"
                      >
                        <Trash2 className="h-4 w-4" /> Drop line
                      </button>
                    )}
                  </div>
                </div>
              ))}
            </div>
            <button
              type="button"
              onClick={() => void submitAnswers()}
              disabled={busy !== null}
              className="flex w-full items-center justify-center gap-2 rounded-lg bg-blue-600 px-4 py-2.5 font-medium text-white transition hover:bg-blue-700 disabled:opacity-60"
            >
              {busy === 'answers' ? <Spinner size="sm" className="border-white border-t-transparent" /> : null}
              Continue to preview
            </button>
          </>
        )}

        {/* Preview */}
        {status === 'awaiting_confirmation' && view.preview && (
          <>
            <div className="flex items-center justify-between rounded-lg bg-gray-50 px-3 py-2 font-mono text-xs text-gray-500">
              <span>Preview v{view.preview.version}</span>
              <span title={view.preview.hash}>{view.preview.hash.slice(0, 12)}…</span>
            </div>
            <div className="overflow-hidden rounded-lg border border-gray-100">
              <table className="min-w-full text-sm">
                <thead className="bg-gray-50 text-left text-xs uppercase tracking-wide text-gray-500">
                  <tr>
                    <th className="px-3 py-2">Item</th>
                    <th className="px-3 py-2">SKU</th>
                    <th className="px-3 py-2 text-right">Stock</th>
                    <th className="px-3 py-2 text-right">Price (₹)</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {view.preview.lines.map(line => (
                    <tr key={line.line_id}>
                      <td className="px-3 py-2 text-gray-900">{line.title}</td>
                      <td className="px-3 py-2 font-mono text-xs text-gray-500">{line.sku}</td>
                      <td className="px-3 py-2 text-right text-gray-700">
                        {line.stock_before} → {line.stock_after}
                        <span className="ml-1 text-green-700">(+{line.quantity_added})</span>
                      </td>
                      <td className="px-3 py-2">
                        <div className="flex items-center justify-end gap-2">
                          <input
                            type="text"
                            inputMode="decimal"
                            value={priceDrafts[line.line_id] ?? line.price_after}
                            onChange={e => setPriceDrafts(prev => ({ ...prev, [line.line_id]: e.target.value }))}
                            className="w-24 rounded-lg border border-gray-200 px-2 py-1 text-right text-sm outline-none focus:border-blue-500"
                          />
                          <button
                            type="button"
                            onClick={() => void savePrice(line.line_id)}
                            disabled={busy !== null}
                            className="rounded-lg border border-gray-300 px-2 py-1 text-xs font-medium text-gray-600 transition hover:bg-gray-100 disabled:opacity-50"
                          >
                            {busy === `price:${line.line_id}` ? '…' : 'Save'}
                          </button>
                        </div>
                        {line.warnings.length > 0 &&
                          line.warnings.map((w, i) => (
                            <p key={i} className="mt-1 text-right text-xs text-amber-600">
                              ⚠ {w}
                            </p>
                          ))}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <p className="text-xs text-gray-500">
              Confirming creates <span className="font-semibold">draft</span> products in Shopify only — nothing goes live
              until you publish them yourself.
            </p>
            <div className="flex gap-3">
              <button
                type="button"
                onClick={() => void confirm()}
                disabled={busy !== null}
                className="flex flex-1 items-center justify-center gap-2 rounded-lg bg-green-600 px-4 py-2.5 font-medium text-white transition hover:bg-green-700 disabled:opacity-60"
              >
                {busy === 'confirm' ? <Spinner size="sm" className="border-white border-t-transparent" /> : <CheckCircle2 className="h-4 w-4" />}
                Confirm &amp; create drafts
              </button>
              <button
                type="button"
                onClick={() => void reject()}
                disabled={busy !== null}
                className="rounded-lg border border-gray-300 px-4 py-2.5 text-sm font-medium text-gray-600 transition hover:bg-gray-100 disabled:opacity-50"
              >
                Reject
              </button>
            </div>
          </>
        )}

        {/* Jobs / terminal result */}
        {(status === 'applying' ||
          status === 'completed' ||
          status === 'partially_failed' ||
          status === 'failed' ||
          status === 'rejected') && (
          <>
            {status === 'completed' && (
              <Alert type="success" message="Drafts created in Shopify. Review them in Products → Shopify drafts before publishing." />
            )}
            {status === 'partially_failed' && (
              <Alert type="warning" title="Some jobs failed" message="Retry the failed jobs after fixing the cause (e.g. a missing location)." />
            )}
            {status === 'rejected' && <Alert type="info" message="Bill rejected. Nothing was created." />}
            {status === 'failed' && (
              <Alert type="error" title="Bill intake failed" message={view.error ?? 'Extraction or application failed. Try again.'} />
            )}
            <div className="overflow-hidden rounded-lg border border-gray-100">
              <ul className="divide-y divide-gray-100">
                {view.jobs.map(job => (
                  <li key={job.id} className="flex items-center justify-between gap-3 px-3 py-2.5 text-sm">
                    <div className="min-w-0">
                      <p className="font-medium text-gray-900">
                        {job.operation} · {job.channel}
                        <span className="ml-2 font-mono text-xs text-gray-400">{job.line_id}</span>
                      </p>
                      {job.error_code && (
                        <p className="mt-0.5 font-mono text-xs text-red-600">
                          {job.error_code}
                          {job.message ? ` — ${job.message}` : ''}
                        </p>
                      )}
                      {job.admin_url && (
                        <a
                          href={job.admin_url}
                          target="_blank"
                          rel="noreferrer"
                          className="mt-0.5 inline-flex items-center gap-1 text-xs font-medium text-blue-600 hover:underline"
                        >
                          Open in Shopify admin <ExternalLink className="h-3 w-3" />
                        </a>
                      )}
                    </div>
                    {jobChip(job)}
                  </li>
                ))}
              </ul>
            </div>
            {(status === 'partially_failed' || status === 'failed') && (
              <div className="flex gap-3">
                <button
                  type="button"
                  onClick={() => void retry()}
                  disabled={busy !== null}
                  className="flex flex-1 items-center justify-center gap-2 rounded-lg bg-blue-600 px-4 py-2.5 font-medium text-white transition hover:bg-blue-700 disabled:opacity-60"
                >
                  <RotateCcw className="h-4 w-4" /> Retry failed jobs
                </button>
                <button
                  type="button"
                  onClick={() => void reject()}
                  disabled={busy !== null}
                  className="rounded-lg border border-gray-300 px-4 py-2.5 text-sm font-medium text-gray-600 transition hover:bg-gray-100 disabled:opacity-50"
                >
                  Reject
                </button>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  )
}
