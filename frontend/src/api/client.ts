import type {
  JobStatus,
  PresetInfo,
  PrintJobCreate,
  PrintJobResponse,
  PrinterPowerResponse,
  PrinterStatusResponse,
  SettingFieldInfo,
  SettingsUpdate,
  TableParseResponse,
  TemplateInfo,
} from './types'

export class ApiError extends Error {
  status: number

  constructor(status: number, message: string) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }
}

async function readErrorDetail(response: Response): Promise<string> {
  try {
    const body = await response.json()
    if (typeof body?.detail === 'string') {
      return body.detail
    }
  } catch {
    // response body wasn't JSON - fall back to the status text below
  }
  return response.statusText || `HTTP ${response.status}`
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const response = await fetch(path, init)

  if (!response.ok) {
    throw new ApiError(response.status, await readErrorDetail(response))
  }

  if (response.status === 204) {
    return undefined as T
  }

  return (await response.json()) as T
}

function jsonBody(payload: unknown): RequestInit {
  return {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  }
}

export async function fetchHealth(): Promise<{ status: string }> {
  return request('/health')
}

export async function fetchTemplates(): Promise<TemplateInfo[]> {
  return request('/api/templates')
}

/** Lists the configured standard print objects (Standarddruckobjekte). */
export async function fetchPresets(): Promise<PresetInfo[]> {
  return request('/api/presets')
}

/** Resolves a preset to a print job and enqueues it. */
export async function printPreset(key: string): Promise<PrintJobResponse> {
  return request(`/api/presets/${encodeURIComponent(key)}/print`, { method: 'POST' })
}

/** Returns the list of available icon names, e.g. "fa-cart-shopping" (Font Awesome) or "svg-logo" (custom SVG). */
export async function fetchIcons(): Promise<string[]> {
  return request('/api/icons')
}

/** Returns the raw SVG file for a custom icon (e.g. "svg-logo"). */
export async function fetchIconSvg(name: string): Promise<Blob> {
  const response = await fetch(`/api/icons/${encodeURIComponent(name)}/svg`)
  if (!response.ok) {
    throw new ApiError(response.status, await readErrorDetail(response))
  }
  return response.blob()
}

export async function fetchJobs(status?: JobStatus): Promise<PrintJobResponse[]> {
  const query = status ? `?status=${encodeURIComponent(status)}` : ''
  return request(`/api/jobs${query}`)
}

export async function fetchJob(id: string): Promise<PrintJobResponse> {
  return request(`/api/jobs/${encodeURIComponent(id)}`)
}

export async function createJob(payload: PrintJobCreate): Promise<PrintJobResponse> {
  return request('/api/jobs', jsonBody(payload))
}

export async function cancelJob(id: string): Promise<PrintJobResponse> {
  return request(`/api/jobs/${encodeURIComponent(id)}`, { method: 'DELETE' })
}

export async function fetchPrinterStatus(): Promise<PrinterStatusResponse> {
  return request('/api/printer/status')
}

export async function fetchPrinterPower(): Promise<PrinterPowerResponse> {
  return request('/api/printer/power')
}

export async function togglePrinterPower(): Promise<PrinterPowerResponse> {
  return request('/api/printer/power/toggle', { method: 'POST' })
}

/** Parses an uploaded CSV or XLSX file and returns a Markdown table string. */
export async function convertTable(file: File): Promise<TableParseResponse> {
  const formData = new FormData()
  formData.append('file', file)
  const response = await fetch('/api/table/parse', { method: 'POST', body: formData })
  if (!response.ok) {
    throw new ApiError(response.status, await readErrorDetail(response))
  }
  return response.json() as Promise<TableParseResponse>
}

/** Lists the web-configurable settings fields (preset integrations) and their current values. */
export async function fetchSettings(): Promise<SettingFieldInfo[]> {
  return request('/api/settings')
}

/** Updates one or more settings fields. A value of null reverts that field to its default. */
export async function updateSettings(payload: SettingsUpdate): Promise<SettingFieldInfo[]> {
  return request('/api/settings', { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) })
}

/** Renders the print job as a PNG without enqueuing it. */
export async function fetchPreview(payload: PrintJobCreate): Promise<Blob> {
  const response = await fetch('/api/preview', jsonBody(payload))

  if (!response.ok) {
    throw new ApiError(response.status, await readErrorDetail(response))
  }
  return response.blob()
}
