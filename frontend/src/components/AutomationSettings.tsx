import React from 'react'
import { useTranslation } from 'react-i18next'
import type { AutomationSettings, RetryStrategy, SuccessChecks } from '../types'
import styles from './AutomationSettings.module.css'

interface Props {
  settings:  AutomationSettings
  onChange:  (s: AutomationSettings) => void
}

export const AutomationSettingsPanel: React.FC<Props> = ({ settings, onChange }) => {
  const { t } = useTranslation()

  const set = <K extends keyof AutomationSettings>(key: K, value: AutomationSettings[K]) =>
    onChange({ ...settings, [key]: value })

  const setCheck = (key: keyof SuccessChecks, value: boolean) =>
    onChange({ ...settings, success_checks: { ...settings.success_checks, [key]: value } })

  const strategies: RetryStrategy[] = ['resubmit', 'reload', 'hybrid']

  return (
    <div className={styles.grid}>

      {/* Max attempts */}
      <div className={styles.row}>
        <label className={styles.label}>{t('max_attempts')}</label>
        <input
          className={styles.numInput}
          type="number"
          min={1} max={100}
          value={settings.max_attempts}
          onChange={(e) => set('max_attempts', Number(e.target.value))}
        />
      </div>

      {/* Initial delay */}
      <div className={styles.row}>
        <label className={styles.label}>{t('initial_delay')}</label>
        <input
          className={styles.numInput}
          type="number"
          min={1} max={60}
          value={settings.initial_delay}
          onChange={(e) => set('initial_delay', Number(e.target.value))}
        />
      </div>

      {/* Retry strategy */}
      <div className={styles.row}>
        <label className={styles.label}>{t('retry_strategy')}</label>
        <div className={styles.stratTabs}>
          {strategies.map((s) => (
            <button
              key={s}
              className={`${styles.stratBtn} ${settings.retry_strategy === s ? styles.stratActive : ''}`}
              onClick={() => set('retry_strategy', s)}
            >
              {t(s)}
            </button>
          ))}
        </div>
      </div>

      {/* Parallel sessions */}
      <div className={styles.row}>
        <label className={styles.label}>{t('parallel_sessions')}</label>
        <input
          className={styles.numInput}
          type="number"
          min={1} max={10}
          value={settings.parallel_sessions}
          onChange={(e) => set('parallel_sessions', Number(e.target.value))}
        />
      </div>

      {/* Worker preview */}
      <div className={styles.row}>
        <label className={styles.label}>{t('workers_preview')}</label>
        <div className={styles.workers}>
          {Array.from({ length: settings.parallel_sessions }).map((_, i) => (
            <div key={i} className={styles.worker}>
              <span className={styles.workerIcon}>▣</span>
              <span>{t('worker')} {i + 1}</span>
            </div>
          ))}
        </div>
      </div>

      <div className={styles.divider} />

      {/* Success detection */}
      <div className={styles.row}>
        <label className={styles.label}>{t('success_detection')}</label>
        <div className={styles.checks}>
          {(Object.keys(settings.success_checks) as (keyof SuccessChecks)[]).map((key) => (
            <label key={key} className={styles.checkItem}>
              <input
                type="checkbox"
                checked={settings.success_checks[key]}
                onChange={(e) => setCheck(key, e.target.checked)}
              />
              <span>{t(key)}</span>
            </label>
          ))}
        </div>
      </div>

      <div className={styles.divider} />

      {/* Direct API mode */}
      <div className={styles.row}>
        <label className={styles.label}>{t('direct_api_mode')}</label>
        <label className={styles.checkItem}>
          <input
            type="checkbox"
            checked={settings.direct_api_mode}
            onChange={(e) => set('direct_api_mode', e.target.checked)}
          />
          <span>{t('bypass_browser')}</span>
        </label>
      </div>

    </div>
  )
}
