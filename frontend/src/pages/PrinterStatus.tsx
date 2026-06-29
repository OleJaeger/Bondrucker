import { useCallback, useEffect, useState } from 'react'
import { ApiError, fetchJob, fetchPrinterPower, fetchPrinterStatus, togglePrinterPower } from '../api/client'
import type { PrinterPowerResponse, PrinterStatusResponse, PrintJobResponse } from '../api/types'
import { OnlineBadge, StatusBadge } from '../components/StatusBadge'

const POLL_INTERVAL_MS = 3000

export function PrinterStatus() {
  const [status, setStatus] = useState<PrinterStatusResponse | null>(null)
  const [currentJob, setCurrentJob] = useState<PrintJobResponse | null>(null)
  const [power, setPower] = useState<PrinterPowerResponse | null>(null)
  const [powerError, setPowerError] = useState<string | null>(null)
  const [toggling, setToggling] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [updatedAt, setUpdatedAt] = useState<Date | null>(null)

  const load = useCallback(async () => {
    try {
      const printerStatus = await fetchPrinterStatus()
      setStatus(printerStatus)
      setUpdatedAt(new Date())
      setError(null)

      if (printerStatus.current_job) {
        setCurrentJob(await fetchJob(printerStatus.current_job))
      } else {
        setCurrentJob(null)
      }
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Drucker-Status konnte nicht geladen werden.')
    }

    try {
      setPower(await fetchPrinterPower())
      setPowerError(null)
    } catch (err) {
      setPowerError(err instanceof ApiError ? err.message : 'Strom-Status konnte nicht geladen werden.')
    }
  }, [])

  useEffect(() => {
    // Initial fetch on mount, matching the standard "fetch + poll" pattern;
    // state updates happen after the await.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    load()
    const interval = window.setInterval(load, POLL_INTERVAL_MS)
    return () => window.clearInterval(interval)
  }, [load])

  const handleToggle = async () => {
    setToggling(true)
    try {
      const result = await togglePrinterPower()
      setPower(result)
      setPowerError(null)
    } catch (err) {
      setPowerError(err instanceof ApiError ? err.message : 'Strom konnte nicht umgeschaltet werden.')
    } finally {
      setToggling(false)
    }
  }

  return (
    <>
      <div className="page-header">
        <h2>Drucker-Status</h2>
        <button type="button" className="button" onClick={load}>
          Aktualisieren
        </button>
      </div>

      {error && <p className="error-text">{error}</p>}

      <div className="card">
        {status === null ? (
          <p className="muted">Lädt...</p>
        ) : (
          <>
            <p>
              Drucker: <OnlineBadge online={status.online} />
            </p>
            <p>
              Aufträge in der Warteschlange: <strong>{status.queue_length}</strong>
            </p>
            <p>
              Aktueller Auftrag:{' '}
              {currentJob ? (
                <>
                  <strong>{currentJob.title || currentJob.id}</strong> (<StatusBadge status={currentJob.status} />)
                </>
              ) : (
                <span className="muted">keiner</span>
              )}
            </p>
            {updatedAt && <p className="form-hint">Zuletzt aktualisiert: {updatedAt.toLocaleTimeString('de-DE')}</p>}
          </>
        )}
      </div>

      <div className="card">
        <h3>Steckdose</h3>
        {powerError && <p className="error-text">{powerError}</p>}
        <p>
          Strom:{' '}
          {power === null ? (
            <span className="muted">Lädt...</span>
          ) : (
            <strong style={{ color: power.power ? 'var(--color-success, #2d7d2d)' : 'var(--color-error, #b00020)' }}>
              {power.power ? 'Ein' : 'Aus'}
            </strong>
          )}
        </p>
        <button type="button" className="button" onClick={handleToggle} disabled={toggling || power === null}>
          {toggling ? 'Schalte...' : power?.power ? 'Ausschalten' : 'Einschalten'}
        </button>
      </div>
    </>
  )
}
