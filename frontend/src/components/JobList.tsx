import type { PrintJobResponse } from '../api/types'
import { StatusBadge } from './StatusBadge'

interface JobListProps {
  jobs: PrintJobResponse[]
  emptyMessage?: string
  onCancel?: (job: PrintJobResponse) => void
  cancellingId?: string | null
}

function formatDate(value: string): string {
  return new Date(value).toLocaleString('de-DE')
}

export function JobList({ jobs, emptyMessage = 'Keine Druckaufträge.', onCancel, cancellingId }: JobListProps) {
  if (jobs.length === 0) {
    return <p className="empty-state">{emptyMessage}</p>
  }

  return (
    <table className="job-table">
      <thead>
        <tr>
          <th>Titel</th>
          <th>Vorlage</th>
          <th>Status</th>
          <th>Erstellt</th>
          <th>Versuche</th>
          <th>Fehler</th>
          {onCancel && <th />}
        </tr>
      </thead>
      <tbody>
        {jobs.map((job) => {
          const cancellable = job.status === 'queued' || job.status === 'failed'
          return (
            <tr key={job.id}>
              <td>{job.title || <span className="muted">–</span>}</td>
              <td>{job.template ?? <span className="muted">–</span>}</td>
              <td>
                <StatusBadge status={job.status} />
              </td>
              <td>{formatDate(job.created_at)}</td>
              <td>{job.retry_count}</td>
              <td className="error-cell">{job.error_message ?? ''}</td>
              {onCancel && (
                <td>
                  {cancellable && (
                    <button
                      type="button"
                      className="button button-small button-danger"
                      disabled={cancellingId === job.id}
                      onClick={() => onCancel(job)}
                    >
                      Abbrechen
                    </button>
                  )}
                </td>
              )}
            </tr>
          )
        })}
      </tbody>
    </table>
  )
}
