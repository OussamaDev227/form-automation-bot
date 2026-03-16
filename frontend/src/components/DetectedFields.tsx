import React from 'react'
import { useTranslation } from 'react-i18next'
import type { FormField, FieldOption } from '../types'
import styles from './DetectedFields.module.css'

interface Props {
  fields:   FormField[]
  values:   Record<string, string>
  onChange: (name: string, value: string) => void
  captchaDetected?: boolean
}

export const DetectedFields: React.FC<Props> = ({
  fields,
  values,
  onChange,
  captchaDetected,
}) => {
  const { t } = useTranslation()

  if (fields.length === 0) {
    return (
      <div className={styles.empty}>
        <div className={styles.emptyIcon}>⬡</div>
        <p>{t('no_fields')}</p>
        <p className={styles.emptyHint}>{t('enter_url_hint')}</p>
      </div>
    )
  }

  return (
    <div className={styles.container}>
      {captchaDetected && (
        <div className={styles.captchaWarn}>
          ⚠ {t('captcha_warning')}
        </div>
      )}
      {fields.map((field, idx) => (
        <FieldCard
          key={field.id ?? field.name ?? idx}
          field={field}
          value={values[field.name ?? field.id ?? ''] ?? ''}
          onChange={onChange}
        />
      ))}
    </div>
  )
}

// ── Individual field card ─────────────────────────────────

interface FieldCardProps {
  field:    FormField
  value:    string
  onChange: (name: string, value: string) => void
}

const FieldCard: React.FC<FieldCardProps> = ({ field, value, onChange }) => {
  const { t } = useTranslation()
  const key = field.name ?? field.id ?? ''

  const handleChange = (val: string) => onChange(key, val)

  return (
    <div className={styles.card}>
      <div className={styles.header}>
        <span className={styles.label}>
          {field.label ?? field.name ?? field.type}
        </span>
        <div className={styles.badges}>
          {field.required && (
            <span className="badge badge-warn">{t('required')}</span>
          )}
          <span className="badge badge-info">{field.type}</span>
        </div>
      </div>

      <div className={styles.input}>
        <FieldInput field={field} value={value} onChange={handleChange} />
      </div>
    </div>
  )
}

// ── Field input switcher ──────────────────────────────────

interface FieldInputProps {
  field:    FormField
  value:    string
  onChange: (val: string) => void
}

const FieldInput: React.FC<FieldInputProps> = ({ field, value, onChange }) => {
  const { t } = useTranslation()
  const type = field.type.toLowerCase()

  if (type === 'textarea') {
    return (
      <textarea
        className={styles.textInput}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={field.placeholder ?? ''}
        rows={2}
        style={{ resize: 'vertical' }}
      />
    )
  }

  if (type === 'select') {
    const options = field.options ?? []
    return (
      <select
        className={styles.textInput}
        value={value}
        onChange={(e) => onChange(e.target.value)}
      >
        <option value="">{t('select_placeholder')}</option>
        {options.map((opt, i) => {
          const o = typeof opt === 'string' ? { value: opt, label: opt } : (opt as FieldOption)
          return <option key={i} value={o.value}>{o.label}</option>
        })}
      </select>
    )
  }

  if (type === 'radio') {
    const options = (field.options ?? []) as FieldOption[]
    return (
      <div className={styles.radioGroup}>
        {options.map((opt, i) => (
          <label key={i} className={styles.radioItem}>
            <input
              type="radio"
              name={field.name ?? field.id}
              value={typeof opt === 'string' ? opt : opt.value}
              checked={value === (typeof opt === 'string' ? opt : opt.value)}
              onChange={() => onChange(typeof opt === 'string' ? opt : opt.value)}
            />
            <span>{typeof opt === 'string' ? opt : opt.label}</span>
          </label>
        ))}
      </div>
    )
  }

  if (type === 'checkbox') {
    return (
      <label className={styles.checkItem}>
        <input
          type="checkbox"
          checked={value === 'true'}
          onChange={(e) => onChange(e.target.checked ? 'true' : 'false')}
        />
        <span>{field.label ?? ''}</span>
      </label>
    )
  }

  // Default: text-like inputs
  return (
    <input
      className={styles.textInput}
      type={type}
      value={value}
      onChange={(e) => onChange(e.target.value)}
      placeholder={field.placeholder ?? ''}
    />
  )
}
