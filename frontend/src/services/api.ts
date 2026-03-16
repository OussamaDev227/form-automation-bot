import axios from 'axios'
import type {
  AnalyzeResponse,
  AutomationSettings,
  AutomationStatusResponse,
  FormField,
} from '../types'

// Base URL from env (empty = same origin, proxied by nginx/vite)
const BASE_URL = import.meta.env.VITE_API_URL ?? ''

const api = axios.create({ baseURL: `${BASE_URL}/api` })

// Attach API key to every request
api.interceptors.request.use((config) => {
  const key = import.meta.env.VITE_API_KEY
  if (key) config.headers['X-API-Key'] = key
  return config
})

// ── Form analysis ─────────────────────────────────────────

export async function analyzeForm(url: string): Promise<AnalyzeResponse> {
  const { data } = await api.post<AnalyzeResponse>('/analyze-form', { url })
  return data
}

// ── Automation control ────────────────────────────────────

export interface StartAutomationPayload {
  url:      string
  fields:   FormField[]
  values:   Record<string, string>
  settings: AutomationSettings
}

export async function startAutomation(
  payload: StartAutomationPayload,
): Promise<{ job_id: string; status: string }> {
  const { data } = await api.post('/start-automation', payload)
  return data
}

export async function stopAutomation(jobId: string): Promise<void> {
  await api.post(`/stop-automation/${jobId}`)
}

export async function getAutomationStatus(
  jobId: string,
): Promise<AutomationStatusResponse> {
  const { data } = await api.get<AutomationStatusResponse>(
    `/automation-status/${jobId}`,
  )
  return data
}

export async function getAutomationLogs(jobId: string) {
  const { data } = await api.get(`/automation-logs/${jobId}`)
  return data
}
