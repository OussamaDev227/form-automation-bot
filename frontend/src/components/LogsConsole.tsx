import React, { useEffect, useRef } from 'react'
import { useTranslation } from 'react-i18next'
import type { LogEntry, LogLevel } from '../types'
import styles from './LogsConsole.module.css'

interface Props {
  logs:    LogEntry[]
  onClear: () => void
}

export const LogsConsole: React.FC<Props> = ({ logs, onClear }) => {
  const { t } = useTranslation()
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [logs])

  const copyAll = () => {
    const text = logs.map((l) => `[${l.seq}] ${l.message}`).join('\n')
    navigator.clipboard.writeText(text).catch(() => {})
  }

  return (
    <div className={styles.wrapper}>
      <div className={styles.toolbar}>
        <button className={styles.toolBtn} onClick={copyAll}>{t('copy')}</button>
        <button className={styles.toolBtn} onClick={onClear}>{t('clear')}</button>
      </div>
      <div className={styles.console}>
        {logs.length === 0 && (
          <div className={styles.line}>
            <span className={styles.num}>—</span>
            <span className={styles.default}>{t('console_ready')}</span>
          </div>
        )}
        {logs.map((entry) => (
          <div key={entry.seq} className={`${styles.line} ${styles.fadein}`}>
            <span className={styles.num}>{entry.seq}</span>
            <span className={styles[entry.level as LogLevel] ?? styles.default}>
              {entry.message}
            </span>
          </div>
        ))}
        <div ref={bottomRef} />
      </div>
    </div>
  )
}
