import React, { useState } from 'react'
import { useTranslation } from 'react-i18next'
import styles from './URLInput.module.css'

interface Props {
  onAnalyze: (url: string) => void
  loading:   boolean
}

export const URLInput: React.FC<Props> = ({ onAnalyze, loading }) => {
  const { t } = useTranslation()
  const [url, setUrl] = useState('')

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (url.trim()) onAnalyze(url.trim())
  }

  return (
    <form className={styles.row} onSubmit={handleSubmit}>
      <input
        className={styles.input}
        type="url"
        value={url}
        onChange={(e) => setUrl(e.target.value)}
        placeholder={t('enter_url')}
        required
        disabled={loading}
      />
      <button
        className={styles.btn}
        type="submit"
        disabled={loading || !url.trim()}
      >
        {loading ? (
          <>
            <span className={styles.spinner} />
            {t('analyzing')}
          </>
        ) : (
          <>
            <SearchIcon />
            {t('analyze')}
          </>
        )}
      </button>
    </form>
  )
}

const SearchIcon = () => (
  <svg width="13" height="13" fill="currentColor" viewBox="0 0 16 16">
    <path d="M11.742 10.344a6.5 6.5 0 1 0-1.397 1.398l3.85 3.85a1 1 0 0 0 1.415-1.414l-3.868-3.834zM12 6.5a5.5 5.5 0 1 1-11 0 5.5 5.5 0 0 1 11 0z"/>
  </svg>
)
