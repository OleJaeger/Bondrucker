import { useEffect, useState } from 'react'
import { ApiError, fetchPresets, printPreset } from '../api/client'
import type { PresetInfo } from '../api/types'
import { IconGlyph } from '../components/IconGlyph'
import { useToast } from '../context/ToastContext'

type PrintStatus = 'idle' | 'printing'

export function Presets() {
  const { addToast } = useToast()
  const [presets, setPresets] = useState<PresetInfo[] | null>(null)
  const [loading, setLoading] = useState(true)
  const [printStatus, setPrintStatus] = useState<Record<string, PrintStatus>>({})

  useEffect(() => {
    let cancelled = false
    fetchPresets()
      .then((list) => {
        if (!cancelled) setPresets(list)
      })
      .catch((err: unknown) => {
        if (!cancelled)
          addToast(err instanceof ApiError ? err.message : 'Standarddruckobjekte konnten nicht geladen werden.', 'error')
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [addToast])

  const handlePrint = async (key: string) => {
    setPrintStatus((prev) => ({ ...prev, [key]: 'printing' }))
    try {
      const job = await printPreset(key)
      addToast(`Druckauftrag ${job.id} wurde in die Warteschlange eingereiht.`)
    } catch (err) {
      addToast(err instanceof ApiError ? err.message : 'Druckauftrag konnte nicht erstellt werden.', 'error')
    } finally {
      setPrintStatus((prev) => ({ ...prev, [key]: 'idle' }))
    }
  }

  const categories = groupByCategory(presets ?? [])

  return (
    <>
      <div className="page-header">
        <h2>Standarddruckobjekte</h2>
      </div>

      {loading && <p className="muted">Standarddruckobjekte werden geladen...</p>}
      {!loading && presets?.length === 0 && <p className="empty-state">Keine Standarddruckobjekte konfiguriert.</p>}

      {categories.map(([category, categoryPresets]) => (
        <section key={category} className="preset-category">
          <h3 className="preset-category-header">{category}</h3>
          <div className="preset-grid">
            {categoryPresets.map((preset) => {
              const status = printStatus[preset.key] ?? 'idle'
              return (
                <div key={preset.key} className="preset-card">
                  <div className="preset-card-icon">{preset.icon && <IconGlyph name={preset.icon} />}</div>
                  <h3>{preset.name}</h3>
                  <p className="muted">{preset.description}</p>
                  <button
                    type="button"
                    className="button button-primary"
                    onClick={() => handlePrint(preset.key)}
                    disabled={status === 'printing'}
                  >
                    {status === 'printing' ? 'Wird gedruckt...' : 'Drucken'}
                  </button>
                </div>
              )
            })}
          </div>
        </section>
      ))}
    </>
  )
}

function groupByCategory(presets: PresetInfo[]): [string, PresetInfo[]][] {
  const groups = new Map<string, PresetInfo[]>()
  for (const preset of presets) {
    const group = groups.get(preset.category)
    if (group) {
      group.push(preset)
    } else {
      groups.set(preset.category, [preset])
    }
  }
  return [...groups.entries()].sort(([a], [b]) => a.localeCompare(b, 'de'))
}
