import { useCallback, useEffect, useState } from 'react'
import { ApiError, fetchSettings, updateSettings } from '../api/client'
import type { SettingFieldInfo } from '../api/types'
import { useToast } from '../context/ToastContext'

export function Settings() {
  const { addToast } = useToast()
  const [fields, setFields] = useState<SettingFieldInfo[] | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let cancelled = false
    fetchSettings()
      .then((list) => {
        if (!cancelled) setFields(list)
      })
      .catch((err: unknown) => {
        if (!cancelled) addToast(err instanceof ApiError ? err.message : 'Konfiguration konnte nicht geladen werden.', 'error')
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [addToast])

  const handleSaved = useCallback((updated: SettingFieldInfo[]) => {
    setFields(updated)
  }, [])

  const groups = groupByGroup(fields ?? [])

  return (
    <>
      <div className="page-header">
        <h2>Konfiguration</h2>
      </div>
      <p className="muted">
        Zugangsdaten und Standardwerte der Standarddruckobjekte. Per .env gesetzte Felder sind gesperrt und
        koennen nur dort geaendert werden.
      </p>

      {loading && <p className="muted">Konfiguration wird geladen...</p>}
      {!loading && (fields?.length ?? 0) === 0 && <p className="empty-state">Keine konfigurierbaren Einstellungen vorhanden.</p>}

      {groups.map(([group, groupFields]) => (
        <section key={group} className="card settings-group">
          <h3>{group}</h3>
          <div className="form-grid">
            {groupFields.map((field) => (
              <SettingsField key={field.key} field={field} onSaved={handleSaved} />
            ))}
          </div>
        </section>
      ))}
    </>
  )
}

function SettingsField({ field, onSaved }: { field: SettingFieldInfo; onSaved: (fields: SettingFieldInfo[]) => void }) {
  const { addToast } = useToast()
  const [value, setValue] = useState(field.secret ? '' : String(field.value ?? ''))
  const [saving, setSaving] = useState(false)

  const save = async (newValue: string | null) => {
    setSaving(true)
    try {
      const coerced = newValue === null ? null : field.type === 'int' ? Number(newValue) : newValue
      const updated = await updateSettings({ [field.key]: coerced })
      onSaved(updated)
      setValue(newValue ?? '')
      addToast(newValue === null ? `${field.label} auf Standard zurückgesetzt.` : `${field.label} gespeichert.`)
    } catch (err) {
      addToast(err instanceof ApiError ? err.message : 'Einstellung konnte nicht gespeichert werden.', 'error')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="form-field settings-field">
      <label htmlFor={`setting-${field.key}`}>
        {field.label}
        {field.locked && <span className="settings-locked-badge">Per .env gesperrt</span>}
      </label>
      <div className="settings-field-row">
        <input
          id={`setting-${field.key}`}
          type={field.secret ? 'password' : 'text'}
          value={field.locked ? String(field.value ?? '') : value}
          onChange={(event) => setValue(event.target.value)}
          disabled={field.locked || saving}
          placeholder={field.secret && field.is_set ? '•••••••• (gesetzt)' : undefined}
        />
        {!field.locked && (
          <>
            <button type="button" className="button button-small" onClick={() => save(value === '' ? null : value)} disabled={saving}>
              Speichern
            </button>
            {field.is_set && (
              <button
                type="button"
                className="button button-small button-danger"
                onClick={() => save(null)}
                disabled={saving}
              >
                Zurücksetzen
              </button>
            )}
          </>
        )}
      </div>
      <p className="form-hint">
        {field.secret ? (field.is_set ? 'Wert ist gesetzt.' : 'Kein Wert gesetzt.') : `Standard: ${field.default ?? '–'}`}
        {field.used_by_presets.length > 0 && ` · Verwendet von: ${field.used_by_presets.join(', ')}`}
      </p>
    </div>
  )
}

function groupByGroup(fields: SettingFieldInfo[]): [string, SettingFieldInfo[]][] {
  const groups = new Map<string, SettingFieldInfo[]>()
  for (const field of fields) {
    const list = groups.get(field.group)
    if (list) {
      list.push(field)
    } else {
      groups.set(field.group, [field])
    }
  }
  return [...groups.entries()]
}
