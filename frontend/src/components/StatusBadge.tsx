import type { JobStatus } from '../api/types'

const STATUS_LABELS: Record<JobStatus, string> = {
  queued: 'Wartend',
  printing: 'Wird gedruckt',
  failed: 'Fehlgeschlagen',
  completed: 'Abgeschlossen',
  cancelled: 'Abgebrochen',
}

export function StatusBadge({ status }: { status: JobStatus }) {
  return <span className={`badge badge-${status}`}>{STATUS_LABELS[status]}</span>
}

export function OnlineBadge({ online }: { online: boolean }) {
  return <span className={`badge ${online ? 'badge-online' : 'badge-offline'}`}>{online ? 'Online' : 'Offline'}</span>
}
