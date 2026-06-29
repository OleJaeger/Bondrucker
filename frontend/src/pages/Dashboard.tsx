import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { ApiError, fetchJobs, fetchPrinterStatus } from '../api/client'
import type { PrinterStatusResponse } from '../api/types'
import { OnlineBadge } from '../components/StatusBadge'

const POLL_INTERVAL_MS = 5000

export function Dashboard() {
  const [status, setStatus] = useState<PrinterStatusResponse | null>(null)
  const [failedCount, setFailedCount] = useState<number | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false

    const load = async () => {
      try {
        const [printerStatus, failedJobs] = await Promise.all([fetchPrinterStatus(), fetchJobs('failed')])
        if (cancelled) return
        setStatus(printerStatus)
        setFailedCount(failedJobs.length)
        setError(null)
      } catch (err) {
        if (cancelled) return
        setError(err instanceof ApiError ? err.message : 'Daten konnten nicht geladen werden.')
      }
    }

    load()
    const interval = window.setInterval(load, POLL_INTERVAL_MS)
    return () => {
      cancelled = true
      window.clearInterval(interval)
    }
  }, [])

  return (
    <>
      <div className="page-header">
        <h2>Übersicht</h2>
        <Link to="/jobs/new" className="button button-primary">
          Neuer Druckauftrag
        </Link>
      </div>

      {error && <p className="error-text">{error}</p>}

      <div className="stat-grid">
        <div className="stat-card">
          <div className="stat-label">Drucker</div>
          <div className="stat-value">{status ? <OnlineBadge online={status.online} /> : '…'}</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">Warteschlange</div>
          <div className="stat-value">{status?.queue_length ?? '…'}</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">Aktueller Auftrag</div>
          <div className="stat-value">{status?.current_job ? status.current_job.slice(0, 8) : '–'}</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">Fehlgeschlagen</div>
          <div className="stat-value">{failedCount ?? '…'}</div>
        </div>
      </div>

      <div className="card">
        <h3>Schnellzugriff</h3>
        <p>
          <Link to="/queue">Warteschlange ansehen</Link>
        </p>
        <p>
          <Link to="/failed">Fehlgeschlagene Aufträge ansehen</Link>
        </p>
        <p>
          <Link to="/printer">Detaillierter Drucker-Status</Link>
        </p>
      </div>
    </>
  )
}
