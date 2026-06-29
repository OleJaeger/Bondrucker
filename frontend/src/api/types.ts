export type JobStatus = 'queued' | 'printing' | 'failed' | 'completed' | 'cancelled'

export interface PrintJobCreate {
  template: string
  title?: string
  icon?: string | null
  markdown?: string
  print_timestamp?: boolean
  /** Base64-encoded image (optionally a 'data:' URL), printed after the title. Mutually exclusive with qr_code. */
  image_base64?: string | null
  /** Content to encode as a QR code, printed after the title. Mutually exclusive with image_base64. */
  qr_code?: string | null
}

export interface PrintJobResponse {
  id: string
  status: JobStatus
  created_at: string
  updated_at: string
  completed_at: string | null
  retry_count: number
  error_message: string | null
  template: string | null
  title: string | null
  icon: string | null
  markdown: string | null
  print_timestamp: boolean | null
  image_base64: string | null
  qr_code: string | null
}

export interface PrinterStatusResponse {
  online: boolean
  queue_length: number
  current_job: string | null
}

export interface PrinterPowerResponse {
  power: boolean
}

export interface TemplateInfo {
  key: string
  name: string
  type: string
  icon: string | null
  allow_markdown: boolean
  allow_attachment: boolean
  default_markdown: string | null
}

export interface TableParseResponse {
  markdown: string
  rows: number
  columns: number
  warnings: string[]
}

export interface PresetInfo {
  key: string
  name: string
  description: string
  icon: string | null
  template: string
  category: string
}

export interface SettingFieldInfo {
  key: string
  group: string
  label: string
  type: 'str' | 'int'
  secret: boolean
  locked: boolean
  value: string | number | null
  is_set: boolean
  default: string | number | null
  used_by_presets: string[]
}

/** Sparse update for PUT /api/settings - null clears the override (reverts to default). */
export type SettingsUpdate = Record<string, string | number | null>
