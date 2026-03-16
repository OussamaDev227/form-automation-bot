import React from 'react'
import { useTranslation } from 'react-i18next'
import type { NetworkRequest } from '../types'
import styles from './NetworkPanel.module.css'

interface Props {
  requests: NetworkRequest[]
}

export const NetworkPanel: React.FC<Props> = ({ requests }) => {
  const { t } = useTranslation()

  if (requests.length === 0) {
    return (
      <p className={styles.empty}>{t('no_network')}</p>
    )
  }

  return (
    <div className={styles.list}>
      {requests.map((req, i) => (
        <div key={i} className={`${styles.entry} fade-in`}>
          <span className={`${styles.method} ${req.method === 'POST' ? styles.post : styles.get}`}>
            {req.method}
          </span>
          <span className={styles.endpoint}>{req.endpoint}</span>
          {req.status != null && (
            <span className={`badge ${req.status < 400 ? 'badge-success' : 'badge-danger'}`}>
              {req.status}
            </span>
          )}
          {req.time_ms != null && (
            <span className={styles.time}>{Math.round(req.time_ms)}ms</span>
          )}
        </div>
      ))}
    </div>
  )
}
