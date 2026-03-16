import React from 'react'
import { useTranslation } from 'react-i18next'
import type { JobStatus } from '../types'
import styles from './StatusBadge.module.css'

interface Props {
  status: JobStatus
}

const STATUS_MAP: Record<JobStatus, { cls: string; dotAnim: boolean }> = {
  created:   { cls: styles.idle,    dotAnim: false },
  analyzing: { cls: styles.running, dotAnim: true },
  ready:     { cls: styles.idle,    dotAnim: false },
  running:   { cls: styles.running, dotAnim: true },
  success:   { cls: styles.success, dotAnim: false },
  failed:    { cls: styles.failed,  dotAnim: false },
  stopped:   { cls: styles.idle,    dotAnim: false },
}

const LABEL_KEY: Record<JobStatus, string> = {
  created:   'status_idle',
  analyzing: 'analyzing',
  ready:     'status_idle',
  running:   'status_running',
  success:   'status_success',
  failed:    'status_failed',
  stopped:   'status_stopped',
}

export const StatusBadge: React.FC<Props> = ({ status }) => {
  const { t } = useTranslation()
  const { cls, dotAnim } = STATUS_MAP[status] ?? STATUS_MAP.created

  return (
    <div className={`${styles.badge} ${cls}`}>
      <span className={`${styles.dot} ${dotAnim ? styles.dotAnim : ''}`} />
      <span>{t(LABEL_KEY[status])}</span>
    </div>
  )
}
