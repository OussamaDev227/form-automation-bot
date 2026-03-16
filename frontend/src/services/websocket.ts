import type { LogEntry } from '../types'

type LogHandler    = (entry: LogEntry) => void
type StatusHandler = (connected: boolean) => void

const BASE_DELAY_MS  = 1_000
const MAX_DELAY_MS   = 30_000
const MAX_RETRIES    = 10

function getApiKey(): string {
  return import.meta.env.VITE_API_KEY ?? ''
}

export class LogSocket {
  private ws:           WebSocket | null = null
  private logHandlers:    LogHandler[]    = []
  private statusHandlers: StatusHandler[] = []
  private jobId:        string
  private stopped       = false
  private retryCount    = 0
  private retryTimer:   ReturnType<typeof setTimeout> | null = null

  constructor(jobId: string) {
    this.jobId = jobId
  }

  // ── Public API ──────────────────────────────────────────

  connect(): void {
    this.stopped = false
    this._open()
  }

  onLog(handler: LogHandler): () => void {
    this.logHandlers.push(handler)
    return () => { this.logHandlers = this.logHandlers.filter((h) => h !== handler) }
  }

  onStatus(handler: StatusHandler): () => void {
    this.statusHandlers.push(handler)
    return () => { this.statusHandlers = this.statusHandlers.filter((h) => h !== handler) }
  }

  disconnect(): void {
    this.stopped = true
    if (this.retryTimer) {
      clearTimeout(this.retryTimer)
      this.retryTimer = null
    }
    this.ws?.close(1000, 'Client disconnect')
    this.ws = null
  }

  // ── Internal ────────────────────────────────────────────

  private _open(): void {
    if (this.stopped) return

    const protocol = window.location.protocol === 'https:' ? 'wss' : 'ws'
    const base      = import.meta.env.VITE_API_URL
      ? new URL(import.meta.env.VITE_API_URL).host
      : window.location.host

    const apiKey    = getApiKey()
    const url       = `${protocol}://${base}/ws/logs/${this.jobId}?api_key=${encodeURIComponent(apiKey)}`

    try {
      this.ws = new WebSocket(url)
    } catch (err) {
      console.warn('[LogSocket] Failed to create WebSocket:', err)
      this._scheduleRetry()
      return
    }

    this.ws.onopen = () => {
      this.retryCount = 0
      this._notifyStatus(true)
    }

    this.ws.onmessage = (event) => {
      try {
        const entry: LogEntry = JSON.parse(event.data)
        this.logHandlers.forEach((h) => h(entry))
      } catch {
        // ignore malformed frames
      }
    }

    this.ws.onerror = () => {
      // onclose fires right after onerror — handle retry there
    }

    this.ws.onclose = (ev) => {
      this._notifyStatus(false)
      // Code 1000 = normal close (we called disconnect()); 4401 = auth failure
      if (this.stopped || ev.code === 1000 || ev.code === 4401) return
      this._scheduleRetry()
    }
  }

  private _scheduleRetry(): void {
    if (this.stopped || this.retryCount >= MAX_RETRIES) return

    const delay = Math.min(BASE_DELAY_MS * 2 ** this.retryCount, MAX_DELAY_MS)
    this.retryCount++
    console.info(`[LogSocket] Reconnecting in ${delay}ms (attempt ${this.retryCount})`)

    this.retryTimer = setTimeout(() => {
      this.retryTimer = null
      this._open()
    }, delay)
  }

  private _notifyStatus(connected: boolean): void {
    this.statusHandlers.forEach((h) => h(connected))
  }
}
