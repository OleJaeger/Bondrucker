import { useEffect, useRef, useState } from 'react'
import { ApiError, fetchPreview } from '../api/client'

interface PreviewPaneProps {
  enabled: boolean
  template: string
  title: string
  icon: string | null
  markdown: string
  printTimestamp: boolean
  imageBase64?: string | null
  qrCode?: string | null
}

const DEBOUNCE_MS = 400

export function PreviewPane({
  enabled,
  template,
  title,
  icon,
  markdown,
  printTimestamp,
  imageBase64 = null,
  qrCode = null,
}: PreviewPaneProps) {
  const [imageUrl, setImageUrl] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)
  const objectUrlRef = useRef<string | null>(null)

  const hasContent = title.trim() !== '' || markdown.trim() !== '' || Boolean(imageBase64) || Boolean(qrCode)

  useEffect(() => {
    if (!enabled || !hasContent) {
      // Nothing to fetch; the early returns below render a placeholder
      // regardless of `loading`/`error`, and re-enabling resets both anyway.
      return
    }

    let cancelled = false
    // Standard "set loading state before starting an async fetch" pattern;
    // the actual request is debounced via setTimeout below.
    /* eslint-disable react-hooks/set-state-in-effect */
    setLoading(true)
    setError(null)
    /* eslint-enable react-hooks/set-state-in-effect */

    const timer = window.setTimeout(() => {
      fetchPreview({
        template,
        title,
        icon,
        markdown,
        print_timestamp: printTimestamp,
        image_base64: imageBase64,
        qr_code: qrCode,
      })
        .then((blob) => {
          if (cancelled) return
          const url = URL.createObjectURL(blob)
          if (objectUrlRef.current) {
            URL.revokeObjectURL(objectUrlRef.current)
          }
          objectUrlRef.current = url
          setImageUrl(url)
        })
        .catch((err: unknown) => {
          if (cancelled) return
          setError(err instanceof ApiError ? err.message : 'Vorschau konnte nicht geladen werden.')
        })
        .finally(() => {
          if (!cancelled) setLoading(false)
        })
    }, DEBOUNCE_MS)

    return () => {
      cancelled = true
      window.clearTimeout(timer)
    }
  }, [enabled, hasContent, template, title, icon, markdown, printTimestamp, imageBase64, qrCode])

  useEffect(() => {
    return () => {
      if (objectUrlRef.current) {
        URL.revokeObjectURL(objectUrlRef.current)
      }
    }
  }, [])

  if (!enabled) {
    return <p className="empty-state">Vorlage auswählen, um eine Vorschau zu sehen.</p>
  }

  if (!hasContent) {
    return <p className="empty-state">Titel oder Inhalt eingeben, um eine Vorschau zu sehen.</p>
  }

  return (
    <div className="preview-pane">
      {loading && <p className="muted">Vorschau wird aktualisiert...</p>}
      {error && <p className="error-text">{error}</p>}
      {imageUrl && <img src={imageUrl} alt="Vorschau des Druckauftrags" className="preview-image" />}
    </div>
  )
}
