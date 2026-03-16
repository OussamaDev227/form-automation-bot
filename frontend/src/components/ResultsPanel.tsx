import React from 'react'
import { useTranslation } from 'react-i18next'
import type { AttemptRecord, AttemptStatus } from '../types'
import styles from './ResultsPanel.module.css'

interface Props {
  attempts:    AttemptRecord[]
  maxAttempts: number
  nextDelay:   number
  sessions:    number
}

const STATUS_CLASS: Record<AttemptStatus, string> = {
  success: 'badge-success',
  failed:  'badge-danger',
  retry:   'badge-info',
  busy:    'badge-warn',
  limited: 'badge-warn',
  captcha: 'badge-warn',
}

export const ResultsPanel: React.FC<Props> = ({
  attempts,
  maxAttempts,
  nextDelay,
  sessions,
}) => {
  const { t } = useTranslation()

  return (
    <div className={styles.container}>
      {/* Metrics row */}
      <div className={styles.metrics}>
        <div className={styles.metric}>
          <span className={styles.metricVal}>{attempts.length}</span>
          <span className={styles.metricLbl}>{t('attempts')}</span>
        </div>
        <div className={styles.metric}>
          <span className={styles.metricVal}>{nextDelay}s</span>
          <span className={styles.metricLbl}>{t('delay')}</span>
        </div>
        <div className={styles.metric}>
          <span className={styles.metricVal}>{sessions}</span>
          <span className={styles.metricLbl}>{t('sessions')}</span>
        </div>
      </div>

      {/* Backoff bars */}
      <BackoffViz
        attempts={attempts.length}
        maxAttempts={maxAttempts}
        lastStatus={attempts[attempts.length - 1]?.status}
      />

      {/* Attempts list */}
      <div className={styles.list}>
        {attempts.length === 0 ? (
          <p className={styles.empty}>{t('no_attempts')}</p>
        ) : (
          [...attempts].reverse().map((a) => (
            <div key={a.attempt_number} className={`${styles.row} fade-in`}>
              <span className={styles.attemptNum}>#{a.attempt_number}</span>
              <span className={styles.attemptMsg}>{a.message}</span>
              <div className={styles.attemptRight}>
                <span className={`badge ${STATUS_CLASS[a.status]}`}>{a.status}</span>
                <span className={styles.delay}>{a.delay_used.toFixed(0)}s</span>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  )
}

// ── Backoff visualizer ────────────────────────────────────

interface BackoffVizProps {
  attempts:   number
  maxAttempts: number
  lastStatus?: AttemptStatus
}

const BackoffViz: React.FC<BackoffVizProps> = ({ attempts, maxAttempts, lastStatus }) => {
  const { t } = useTranslation()
  const bars = Math.min(maxAttempts, 12)

  return (
    <div>
      <p className={styles.vizLabel}>{t('backoff_viz')}</p>
      <div className={styles.bars}>
        {Array.from({ length: bars }).map((_, i) => {
          const delay = Math.min(2 * Math.pow(2, i), 60)
          const heightPct = (delay / 60) * 100
          let state = 'pending'
          if (i < attempts - 1) state = 'done'
          else if (i === attempts - 1) {
            state = lastStatus === 'success' ? 'success' : 'current'
          }
          return (
            <div
              key={i}
              className={`${styles.bar} ${styles[state]}`}
              style={{ height: `${Math.max(heightPct * 0.38, 3)}px` }}
              title={`Attempt ${i + 1}: ${delay}s delay`}
            />
          )
        })}
      </div>
      <div className={styles.vizFooter}>
        <span>{t('attempt_1') ?? 'ATT 1'}</span>
        <span>{t('max_delay') ?? 'MAX'}</span>
      </div>
    </div>
  )
}
