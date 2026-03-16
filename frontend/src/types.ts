// ── Form field types ──────────────────────────────────────

export interface FieldOption {
  value: string
  label: string
}

export interface FormField {
  id?:          string
  name?:        string
  type:         string
  label?:       string
  placeholder?: string
  required:     boolean
  default?:     string
  options?:     (FieldOption | string)[]
}

// ── Automation settings ───────────────────────────────────

export type RetryStrategy = 'resubmit' | 'reload' | 'hybrid'

export interface SuccessChecks {
  url_redirect:     boolean
  success_message:  boolean
  form_disappear:   boolean
  session_cookie:   boolean
  api_response_200: boolean
}

export interface AutomationSettings {
  max_attempts:      number
  initial_delay:     number
  retry_strategy:    RetryStrategy
  parallel_sessions: number
  direct_api_mode:   boolean
  success_checks:    SuccessChecks
}

// ── Job / attempt models ──────────────────────────────────

export type JobStatus = 'created' | 'analyzing' | 'ready' | 'running' | 'success' | 'failed' | 'stopped'

export type AttemptStatus = 'success' | 'failed' | 'retry' | 'busy' | 'limited' | 'captcha'

export interface AttemptRecord {
  attempt_number: number
  status:         AttemptStatus
  message:        string
  delay_used:     number
  response_time?: number
  http_status?:   number
}

export interface AutomationStatusResponse {
  job_id:    string
  status:    JobStatus
  attempts:  AttemptRecord[]
  message?:  string
}

// ── Log entry ─────────────────────────────────────────────

export type LogLevel = 'info' | 'success' | 'warn' | 'error' | 'default'

export interface LogEntry {
  job_id:    string
  seq:       number
  level:     LogLevel
  message:   string
  timestamp: string
}

// ── Network request ───────────────────────────────────────

export interface NetworkRequest {
  method:    string
  endpoint:  string
  payload?:  Record<string, unknown>
  status?:   number
  time_ms?:  number
}

// ── Analyze response ──────────────────────────────────────

export interface AnalyzeResponse {
  url:               string
  fields:            FormField[]
  captcha_detected:  boolean
  raw_html_snippet?: string
}
