import { useEffect, useMemo, useRef, useState } from 'react'
import { ApiError, fetchIcons } from '../api/client'
import { IconGlyph, iconLabel } from './IconGlyph'

interface IconPickerProps {
  value: string
  onChange: (value: string) => void
  placeholder?: string
}

const MAX_RESULTS = 60

// Module-level cache so the (large) icon list is fetched only once per page load.
let iconsCache: string[] | null = null
let iconsPromise: Promise<string[]> | null = null

function loadIcons(): Promise<string[]> {
  if (iconsCache) return Promise.resolve(iconsCache)
  if (!iconsPromise) {
    iconsPromise = fetchIcons()
      .then((icons) => {
        iconsCache = icons
        return icons
      })
      .catch((err: unknown) => {
        iconsPromise = null
        throw err
      })
  }
  return iconsPromise
}

/** Searchable picker for Font Awesome and custom SVG icons, showing real previews. */
export function IconPicker({ value, onChange, placeholder }: IconPickerProps) {
  const [icons, setIcons] = useState<string[] | null>(iconsCache)
  const [error, setError] = useState<string | null>(null)
  const [open, setOpen] = useState(false)
  const [query, setQuery] = useState('')
  const containerRef = useRef<HTMLDivElement>(null)
  const searchRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    if (icons !== null) return
    let cancelled = false
    loadIcons()
      .then((list) => {
        if (!cancelled) setIcons(list)
      })
      .catch((err: unknown) => {
        if (!cancelled) setError(err instanceof ApiError ? err.message : 'Icons konnten nicht geladen werden.')
      })
    return () => {
      cancelled = true
    }
  }, [icons])

  useEffect(() => {
    if (!open) return

    const handleClickOutside = (event: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(event.target as Node)) {
        setOpen(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [open])

  useEffect(() => {
    if (!open) return
    const timer = window.setTimeout(() => searchRef.current?.focus(), 0)
    return () => window.clearTimeout(timer)
  }, [open])

  const toggleOpen = () => {
    if (!open) {
      setQuery('')
    }
    setOpen((prev) => !prev)
  }

  const results = useMemo(() => {
    if (!icons) return []
    const q = query.trim().toLowerCase()
    const filtered = q
      ? icons.filter((name) => name.toLowerCase().includes(q) || iconLabel(name).toLowerCase().includes(q))
      : icons
    return filtered.slice(0, MAX_RESULTS)
  }, [icons, query])

  const handleSelect = (name: string) => {
    onChange(name)
    setOpen(false)
  }

  return (
    <div className="icon-picker" ref={containerRef}>
      <div className="icon-picker-control">
        <button
          type="button"
          className="icon-picker-trigger"
          onClick={toggleOpen}
          aria-expanded={open}
        >
          {value ? (
            <>
              <IconGlyph name={value} className="icon-picker-glyph" />
              <span>{value}</span>
            </>
          ) : (
            <span className="muted">{placeholder ?? 'Icon auswählen...'}</span>
          )}
        </button>
        {value && (
          <button
            type="button"
            className="icon-picker-clear"
            onClick={() => onChange('')}
            aria-label="Icon entfernen"
            title="Icon entfernen"
          >
            &times;
          </button>
        )}
      </div>

      {open && (
        <div className="icon-picker-dropdown">
          <input
            ref={searchRef}
            type="text"
            className="icon-picker-search"
            placeholder="Icon suchen..."
            value={query}
            onChange={(event) => setQuery(event.target.value)}
          />
          {error && <p className="error-text">{error}</p>}
          {icons === null && !error && <p className="muted">Icons werden geladen...</p>}
          {icons !== null && (
            <div className="icon-picker-list">
              {results.length === 0 && <p className="muted">Keine Icons gefunden.</p>}
              {results.map((name) => (
                <button
                  key={name}
                  type="button"
                  className={`icon-picker-item${name === value ? ' icon-picker-item-active' : ''}`}
                  onClick={() => handleSelect(name)}
                  title={name}
                >
                  <IconGlyph name={name} />
                  <span>{iconLabel(name)}</span>
                </button>
              ))}
              {icons.length > MAX_RESULTS && results.length === MAX_RESULTS && (
                <p className="muted icon-picker-more">Weitere Treffer durch genauere Suche einschränken...</p>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  )
}
