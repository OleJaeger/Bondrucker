import { useCallback, useEffect, useState } from 'react'
import { ApiError, cancelJob, fetchJobs } from '../api/client'
import type { PrintJobResponse } from '../api/types'
import { JobList } from '../components/JobList'

const POLL_INTERVAL_MS = 4000

export function FailedJobs() {
  const [jobs, setJobs] = useState<PrintJobResponse[] | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [cancellingId, setCancellingId] = useState<string | null>(null)

  const load = useCallback(async () => {
    try {
      setJobs(await fetchJobs('failed'))
      setError(null)
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Fehlgeschlagene Aufträge konnten nicht geladen werden.')
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

  const handleCancel = async (job: PrintJobResponse) => {
    setCancellingId(job.id)
    try {
      await cancelJob(job.id)
      await load()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Auftrag konnte nicht abgebrochen werden.')
    } finally {
      setCancellingId(null)
    }
  }

  return (
    <>
      <div className="page-header">
        <h2>Fehlgeschlagene Aufträge</h2>
      </div>
      <p className="form-hint">
        Fehlgeschlagene Aufträge werden automatisch mit steigender Wartezeit erneut versucht, solange sie nicht
        abgebrochen werden.
      </p>
      {error && <p className="error-text">{error}</p>}
      <div className="card">
        {jobs === null ? (
          <p className="muted">Lädt...</p>
        ) : (
          <JobList
            jobs={jobs}
            onCancel={handleCancel}
            cancellingId={cancellingId}
            emptyMessage="Keine fehlgeschlagenen Aufträge."
          />
        )}
      </div>
    </>
  )
}
