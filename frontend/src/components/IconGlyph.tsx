import { useEffect, useState } from 'react'
import { fetchIconSvg } from '../api/client'

export const CUSTOM_ICON_PREFIX = 'svg-'

// Module-level cache of object URLs for custom SVG icons, fetched once per page load.
const svgIconUrlCache = new Map<string, string>()
const svgIconUrlPromises = new Map<string, Promise<string>>()

function loadIconSvgUrl(name: string): Promise<string> {
  const cached = svgIconUrlCache.get(name)
  if (cached) return Promise.resolve(cached)
  let promise = svgIconUrlPromises.get(name)
  if (!promise) {
    promise = fetchIconSvg(name)
      .then((blob) => {
        const url = URL.createObjectURL(blob)
        svgIconUrlCache.set(name, url)
        return url
      })
      .catch((err: unknown) => {
        svgIconUrlPromises.delete(name)
        throw err
      })
    svgIconUrlPromises.set(name, promise)
  }
  return promise
}

export function iconLabel(name: string): string {
  return name.replace(/^fa-/, '').replace(/^svg-/, '').replace(/-/g, ' ')
}

/** Renders an icon glyph: a Font Awesome ligature for "fa-*" names, or a
 * CSS mask of the SVG file for custom "svg-*" icons so it inherits `color`
 * the same way Font Awesome's `currentColor` glyphs do. */
export function IconGlyph({ name, className }: { name: string; className?: string }) {
  const isCustom = name.startsWith(CUSTOM_ICON_PREFIX)
  const [url, setUrl] = useState<string | null>(() => (isCustom ? svgIconUrlCache.get(name) ?? null : null))

  useEffect(() => {
    if (!isCustom || url) return
    let cancelled = false
    loadIconSvgUrl(name)
      .then((loaded) => {
        if (!cancelled) setUrl(loaded)
      })
      .catch(() => {
        // Broken custom icon - leave the placeholder empty rather than failing the picker.
      })
    return () => {
      cancelled = true
    }
  }, [isCustom, name, url])

  if (!isCustom) {
    return <i className={`fa-solid ${name}${className ? ` ${className}` : ''}`} aria-hidden="true" />
  }

  return (
    <span
      className={`icon-picker-img${className ? ` ${className}` : ''}`}
      style={url ? { maskImage: `url(${url})`, WebkitMaskImage: `url(${url})` } : undefined}
      aria-hidden="true"
    />
  )
}
