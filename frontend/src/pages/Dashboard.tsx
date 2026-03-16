import React, { useState, useCallback, useRef, useEffect } from 'react'
import { useTranslation } from 'react-i18next'

import { URLInput }                  from '../components/URLInput'
import { DetectedFields }            from '../components/DetectedFields'
import { AutomationSettingsPanel }   from '../components/AutomationSettings'
import { LogsConsole }               from '../components/LogsConsole'
import { ResultsPanel }              from '../components/ResultsPanel'
import { NetworkPanel }              from '../components/NetworkPanel'
import { StatusBadge }               from '../components/StatusBadge'

import { analyzeForm, startAutomation, stopAutomation } from '../services/api'
import { LogSocket }                 from '../services/websocket'

import type {
  FormField,
  AutomationSettings,
  JobStatus,
  LogEntry,
  AttemptRecord,
  NetworkRequest,
} from '../types'

import styles from './Dashboard.module.css'

// ── Default settings ──────────────────────────────────────
const defaultSettings: AutomationSettings = {
  max_attempts:      10,
  initial_delay:     2,
  retry_strategy:    'hybrid',
  parallel_sessions: 3,
  direct_api_mode:   false,
  success_checks: {
    url_redirect:     true,
    success_message:  true,
    form_disappear:   true,
    session_cookie:   true,
    api_response_200: true,
  },
}

type RightTab = 'settings' | 'logs' | 'history' | 'network'

export const Dashboard: React.FC = () => {
  const { t, i18n } = useTranslation()

  // ── State ──────────────────────────────────────────────
  const [analyzing,        setAnalyzing]        = useState(false)
  const [analyzeError,     setAnalyzeError]      = useState<string | null>(null)
  const [fields,           setFields]            = useState<FormField[]>([])
  const [captchaDetected,  setCaptchaDetected]   = useState(false)
  const [fieldValues,      setFieldValues]       = useState<Record<string, string>>({})
  const [settings,         setSettings]          = useState<AutomationSettings>(defaultSettings)
  const [jobId,            setJobId]             = useState<string | null>(null)
  const [jobStatus,        setJobStatus]         = useState<JobStatus>('created')
  const [logs,             setLogs]              = useState<LogEntry[]>([])
  const [attempts,         setAttempts]          = useState<AttemptRecord[]>([])
  const [nextDelay,        setNextDelay]         = useState(0)
  const [networkRequests,  setNetworkRequests]   = useState<NetworkRequest[]>([])
  const [activeTab,        setActiveTab]         = useState<RightTab>('settings')
  const [currentUrl,       setCurrentUrl]        = useState('')
  const [wsConnected,      setWsConnected]       = useState(false)

  const socketRef = useRef<LogSocket | null>(null)
  const pollRef   = useRef<ReturnType<typeof setInterval> | null>(null)

  // ── Field value change ────────────────────────────────
  const handleFieldChange = useCallback((name: string, value: string) => {
    setFieldValues((prev) => ({ ...prev, [name]: value }))
  }, [])

  // ── Analyze form ──────────────────────────────────────
  const handleAnalyze = useCallback(async (url: string) => {
    setAnalyzing(true)
    setAnalyzeError(null)
    setFields([])
    setFieldValues({})
    setCaptchaDetected(false)
    setNetworkRequests([])
    setCurrentUrl(url)

    try {
      const result = await analyzeForm(url)
      setFields(result.fields)
      setCaptchaDetected(result.captcha_detected)

      // Pre-fill defaults
      const defaults: Record<string, string> = {}
      result.fields.forEach((f) => {
        const key = f.name ?? f.id ?? ''
        if (key && f.default) defaults[key] = f.default
      })
      setFieldValues(defaults)

      setActiveTab('settings')
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Analysis failed'
      setAnalyzeError(msg)
    } finally {
      setAnalyzing(false)
    }
  }, [])

  // ── Start automation ──────────────────────────────────
  const handleStart = useCallback(async () => {
    if (!fields.length || !currentUrl) return

    setLogs([])
    setAttempts([])
    setNextDelay(settings.initial_delay)
    setJobStatus('running')
    setActiveTab('logs')

    try {
      const { job_id } = await startAutomation({
        url: currentUrl,
        fields,
        values: fieldValues,
        settings,
      })
      setJobId(job_id)

      // Connect WebSocket for live logs
      const socket = new LogSocket(job_id)
      socketRef.current = socket
      socket.onLog((entry) => {
        setLogs((prev) => [...prev, entry])
      })
      socket.onStatus((connected) => setWsConnected(connected))
      socket.connect()

      // Poll status every 2 s
      pollRef.current = setInterval(async () => {
        try {
          const { getAutomationStatus } = await import('../services/api')
          const status = await getAutomationStatus(job_id)
          setJobStatus(status.status)
          setAttempts(status.attempts)

          const lastAttempt = status.attempts.length
          if (lastAttempt > 0) {
            const delay = Math.min(
              settings.initial_delay * Math.pow(2, lastAttempt),
              60,
            )
            setNextDelay(Math.round(delay))
          }

          if (['success', 'failed', 'stopped'].includes(status.status)) {
            clearInterval(pollRef.current!)
            pollRef.current = null
          }
        } catch {
          // ignore transient poll errors
        }
      }, 2000)
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to start'
      setAnalyzeError(msg)
      setJobStatus('failed')
    }
  }, [fields, currentUrl, fieldValues, settings])

  // ── Stop automation ───────────────────────────────────
  const handleStop = useCallback(async () => {
    if (!jobId) return
    try {
      await stopAutomation(jobId)
    } catch { /* ignore */ }
    socketRef.current?.disconnect()
    socketRef.current = null
    if (pollRef.current) {
      clearInterval(pollRef.current)
      pollRef.current = null
    }
    setJobStatus('stopped')
  }, [jobId])

  // ── Cleanup on unmount ────────────────────────────────
  useEffect(() => {
    return () => {
      socketRef.current?.disconnect()
      if (pollRef.current) clearInterval(pollRef.current)
    }
  }, [])

  const isRunning = jobStatus === 'running'

  // ── Language switcher ─────────────────────────────────
  const langs = ['en', 'fr', 'ar'] as const
  const handleLang = (l: string) => {
    i18n.changeLanguage(l)
    document.documentElement.dir = l === 'ar' ? 'rtl' : 'ltr'
    document.documentElement.lang = l
  }

  // ── Tab content ───────────────────────────────────────
  const tabContent: Record<RightTab, React.ReactNode> = {
    settings: (
      <AutomationSettingsPanel
        settings={settings}
        onChange={setSettings}
      />
    ),
    logs: (
      <LogsConsole
        logs={logs}
        onClear={() => setLogs([])}
      />
    ),
    history: (
      <ResultsPanel
        attempts={attempts}
        maxAttempts={settings.max_attempts}
        nextDelay={nextDelay}
        sessions={settings.parallel_sessions}
      />
    ),
    network: (
      <NetworkPanel requests={networkRequests} />
    ),
  }

  const RIGHT_TABS: { key: RightTab; label: string }[] = [
    { key: 'settings', label: t('settings') },
    { key: 'logs',     label: t('logs') },
    { key: 'history',  label: t('history') },
    { key: 'network',  label: t('network') },
  ]

  return (
    <div className={styles.platform}>

      {/* ── Header ── */}
      <header className={styles.header}>
        <div className={styles.logo}>
          <div className={styles.logoIcon}>
            <svg width="16" height="16" fill="white" viewBox="0 0 16 16">
              <path d="M2 2h5v5H2zm7 0h5v5H9zm0 7h5v5H9zM2 9h5v5H2z"/>
            </svg>
          </div>
          <div>
            <div className={styles.logoText}>{t('app_title')}</div>
            <div className={styles.logoSub}>{t('app_subtitle')}</div>
          </div>
        </div>

        <div style={{display:'flex',alignItems:'center',gap:12}}>
          {isRunning && (
            <div style={{display:'flex',alignItems:'center',gap:5,fontFamily:'var(--mono)',fontSize:10,color: wsConnected ? 'var(--success-text)' : 'var(--warn-text)'}}>
              <span style={{width:6,height:6,borderRadius:'50%',background:'currentColor',display:'inline-block',animation: wsConnected ? 'none' : 'pulse 1s infinite'}} />
              {wsConnected ? 'WS live' : 'WS reconnecting...'}
            </div>
          )}
        <div className={styles.langSwitcher}>
          {langs.map((l) => (
            <button
              key={l}
              className={`${styles.langBtn} ${i18n.language === l ? styles.langActive : ''}`}
              onClick={() => handleLang(l)}
            >
              {l.toUpperCase()}
            </button>
          ))}
        </div>
        </div>
      </header>

      {/* ── Main two-column layout ── */}
      <div className={styles.main}>

        {/* LEFT PANEL */}
        <div className={styles.leftPanel}>

          {/* URL input */}
          <section className={styles.section}>
            <div className={styles.sectionLabel}>{t('url_target')}</div>
            <URLInput onAnalyze={handleAnalyze} loading={analyzing} />
            {analyzeError && (
              <p className={styles.errorMsg}>{analyzeError}</p>
            )}
            {!analyzing && fields.length > 0 && (
              <p className={styles.successMsg}>
                ✓ {fields.length} {t('fields_found')}
              </p>
            )}
          </section>

          {/* Detected fields */}
          <section className={`${styles.section} ${styles.sectionGrow}`}>
            <div className={styles.sectionLabel}>{t('detected_fields')}</div>
            <DetectedFields
              fields={fields}
              values={fieldValues}
              onChange={handleFieldChange}
              captchaDetected={captchaDetected}
            />
          </section>

          {/* Automation control */}
          <section className={styles.section}>
            <div className={styles.sectionLabel}>{t('automation_ctrl')}</div>
            <div className={styles.controls}>
              <button
                className={`${styles.btn} ${styles.btnStart}`}
                onClick={handleStart}
                disabled={isRunning || fields.length === 0}
              >
                <PlayIcon />
                {t('start')}
              </button>
              <button
                className={`${styles.btn} ${styles.btnStop}`}
                onClick={handleStop}
                disabled={!isRunning}
              >
                <StopIcon />
                {t('stop')}
              </button>
              <StatusBadge status={jobStatus} />
            </div>

            {/* Progress bar */}
            {(isRunning || jobStatus === 'success') && (
              <div className={styles.progressWrap}>
                <div
                  className={`${styles.progressBar} ${jobStatus === 'success' ? styles.progressSuccess : ''}`}
                  style={{
                    width: jobStatus === 'success'
                      ? '100%'
                      : `${Math.min((attempts.length / settings.max_attempts) * 100, 100)}%`,
                  }}
                />
              </div>
            )}
          </section>

        </div>

        {/* RIGHT PANEL */}
        <div className={styles.rightPanel}>

          {/* Tab bar */}
          <div className={styles.tabBar}>
            {RIGHT_TABS.map(({ key, label }) => (
              <button
                key={key}
                className={`${styles.tab} ${activeTab === key ? styles.tabActive : ''}`}
                onClick={() => setActiveTab(key)}
              >
                {label}
                {key === 'logs' && logs.length > 0 && (
                  <span className={styles.tabCount}>{logs.length}</span>
                )}
                {key === 'history' && attempts.length > 0 && (
                  <span className={styles.tabCount}>{attempts.length}</span>
                )}
              </button>
            ))}
          </div>

          {/* Tab content */}
          <div className={styles.tabContent}>
            {tabContent[activeTab]}
          </div>

        </div>
      </div>
    </div>
  )
}

// ── Icon helpers ──────────────────────────────────────────
const PlayIcon = () => (
  <svg width="12" height="12" fill="currentColor" viewBox="0 0 16 16">
    <path d="M11.596 8.697L4.25 3.5a.5.5 0 0 0-.75.434v9.13a.5.5 0 0 0 .75.434l7.346-5.197a.5.5 0 0 0 0-.864z"/>
  </svg>
)

const StopIcon = () => (
  <svg width="12" height="12" fill="currentColor" viewBox="0 0 16 16">
    <path d="M5 3.5h6A1.5 1.5 0 0 1 12.5 5v6a1.5 1.5 0 0 1-1.5 1.5H5A1.5 1.5 0 0 1 3.5 11V5A1.5 1.5 0 0 1 5 3.5z"/>
  </svg>
)
