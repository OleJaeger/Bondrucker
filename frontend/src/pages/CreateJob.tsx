import { useEffect, useMemo, useState, type ChangeEvent, type FormEvent } from 'react'
import { ApiError, convertTable, createJob, fetchTemplates } from '../api/client'
import type { TableParseResponse, TemplateInfo } from '../api/types'
import { IconPicker } from '../components/IconPicker'
import { PreviewPane } from '../components/PreviewPane'
import { useToast } from '../context/ToastContext'

type AttachmentType = 'none' | 'image' | 'qr' | 'table'
type QrType = 'url' | 'wifi' | 'vcard' | 'location'
type WifiEncryption = 'WPA' | 'WEP' | 'nopass'

function escapeWifiField(value: string): string {
  return value.replace(/([\\;,":])/g, '\\$1')
}

function buildWifiContent(ssid: string, password: string, encryption: WifiEncryption, hidden: boolean): string {
  const parts = [`T:${encryption}`, `S:${escapeWifiField(ssid)}`]
  if (encryption !== 'nopass') {
    parts.push(`P:${escapeWifiField(password)}`)
  }
  if (hidden) {
    parts.push('H:true')
  }
  return `WIFI:${parts.join(';')};;`
}

function buildVCardContent(name: string, phone: string, email: string, org: string): string {
  const lines = ['BEGIN:VCARD', 'VERSION:3.0', `FN:${name.trim()}`, `N:${name.trim()};;;;`]
  if (phone.trim()) lines.push(`TEL:${phone.trim()}`)
  if (email.trim()) lines.push(`EMAIL:${email.trim()}`)
  if (org.trim()) lines.push(`ORG:${org.trim()}`)
  lines.push('END:VCARD')
  return lines.join('\n')
}

function buildLocationContent(lat: string, lon: string, label: string): string {
  const coords = `${lat.trim()},${lon.trim()}`
  return label.trim() ? `geo:${coords}?q=${coords}(${encodeURIComponent(label.trim())})` : `geo:${coords}`
}

export function CreateJob() {
  const { addToast } = useToast()

  const [templates, setTemplates] = useState<TemplateInfo[] | null>(null)

  const [template, setTemplate] = useState('')
  const [title, setTitle] = useState('')
  const [icon, setIcon] = useState('')
  const [markdown, setMarkdown] = useState('')
  const [printTimestamp, setPrintTimestamp] = useState(true)

  const [attachmentType, setAttachmentType] = useState<AttachmentType>('none')

  const [imageBase64, setImageBase64] = useState<string | null>(null)
  const [imageFileName, setImageFileName] = useState<string | null>(null)
  const [imageError, setImageError] = useState<string | null>(null)

  const [qrType, setQrType] = useState<QrType>('url')
  const [qrUrl, setQrUrl] = useState('')
  const [wifiSsid, setWifiSsid] = useState('')
  const [wifiPassword, setWifiPassword] = useState('')
  const [wifiEncryption, setWifiEncryption] = useState<WifiEncryption>('WPA')
  const [wifiHidden, setWifiHidden] = useState(false)
  const [vcardName, setVcardName] = useState('')
  const [vcardPhone, setVcardPhone] = useState('')
  const [vcardEmail, setVcardEmail] = useState('')
  const [vcardOrg, setVcardOrg] = useState('')
  const [locationLat, setLocationLat] = useState('')
  const [locationLon, setLocationLon] = useState('')
  const [locationLabel, setLocationLabel] = useState('')

  const [tableResult, setTableResult] = useState<TableParseResponse | null>(null)
  const [tableError, setTableError] = useState<string | null>(null)
  const [tableLoading, setTableLoading] = useState(false)

  const [submitting, setSubmitting] = useState(false)

  useEffect(() => {
    let cancelled = false
    fetchTemplates()
      .then((list) => {
        if (cancelled) return
        setTemplates(list)
        if (list.length > 0) {
          setTemplate(list[0].key)
        }
      })
      .catch((err: unknown) => {
        if (cancelled) return
        addToast(err instanceof ApiError ? err.message : 'Vorlagen konnten nicht geladen werden.', 'error')
      })
    return () => {
      cancelled = true
    }
  }, [])

  const selectedTemplate = templates?.find((entry) => entry.key === template) ?? null
  const allowMarkdown = selectedTemplate?.allow_markdown ?? true
  const allowAttachment = selectedTemplate?.allow_attachment ?? true

  useEffect(() => {
    if (!selectedTemplate || selectedTemplate.allow_markdown) return
    setMarkdown(selectedTemplate.default_markdown ?? '')
  }, [selectedTemplate])

  const qrCodeContent = useMemo(() => {
    switch (qrType) {
      case 'url':
        return qrUrl.trim()
      case 'wifi':
        return wifiSsid.trim() ? buildWifiContent(wifiSsid, wifiPassword, wifiEncryption, wifiHidden) : ''
      case 'vcard':
        return vcardName.trim() ? buildVCardContent(vcardName, vcardPhone, vcardEmail, vcardOrg) : ''
      case 'location':
        return locationLat.trim() && locationLon.trim()
          ? buildLocationContent(locationLat, locationLon, locationLabel)
          : ''
      default:
        return ''
    }
  }, [qrType, qrUrl, wifiSsid, wifiPassword, wifiEncryption, wifiHidden, vcardName, vcardPhone, vcardEmail, vcardOrg, locationLat, locationLon, locationLabel])

  const hasAttachment =
    (attachmentType === 'image' && imageBase64 !== null) ||
    (attachmentType === 'qr' && qrCodeContent !== '') ||
    (attachmentType === 'table' && tableResult !== null)
  const hasContent = title.trim() !== '' || markdown.trim() !== '' || hasAttachment

  const handleImageFileChange = (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0] ?? null
    setImageError(null)
    if (!file) {
      setImageBase64(null)
      setImageFileName(null)
      return
    }

    setImageFileName(file.name)
    const reader = new FileReader()
    reader.onload = () => {
      setImageBase64(typeof reader.result === 'string' ? reader.result : null)
    }
    reader.onerror = () => {
      setImageError('Bild konnte nicht gelesen werden.')
      setImageBase64(null)
    }
    reader.readAsDataURL(file)
  }

  const handleTableFileChange = async (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0] ?? null
    setTableError(null)
    setTableResult(null)
    if (!file) return

    setTableLoading(true)
    try {
      const result = await convertTable(file)
      setTableResult(result)
    } catch (err) {
      setTableError(err instanceof ApiError ? err.message : 'Datei konnte nicht verarbeitet werden.')
    } finally {
      setTableLoading(false)
    }
  }

  const resetAttachment = () => {
    setAttachmentType('none')
    setImageBase64(null)
    setImageFileName(null)
    setImageError(null)
    setQrType('url')
    setQrUrl('')
    setWifiSsid('')
    setWifiPassword('')
    setWifiEncryption('WPA')
    setWifiHidden(false)
    setVcardName('')
    setVcardPhone('')
    setVcardEmail('')
    setVcardOrg('')
    setLocationLat('')
    setLocationLon('')
    setLocationLabel('')
    setTableResult(null)
    setTableError(null)
  }

  useEffect(() => {
    if (!selectedTemplate || selectedTemplate.allow_attachment) return
    resetAttachment()
  }, [selectedTemplate])

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault()
    if (!hasContent) {
      addToast('Titel, Inhalt, Bild oder QR-Code darf nicht leer sein.', 'error')
      return
    }

    setSubmitting(true)

    try {
      const tableMarkdown = attachmentType === 'table' && tableResult ? tableResult.markdown : null
      const combinedMarkdown = [tableMarkdown, markdown].filter(Boolean).join('\n\n')

      const job = await createJob({
        template,
        title,
        icon: icon.trim() ? icon.trim() : null,
        markdown: combinedMarkdown,
        print_timestamp: printTimestamp,
        image_base64: attachmentType === 'image' ? imageBase64 : null,
        qr_code: attachmentType === 'qr' ? qrCodeContent : null,
      })
      addToast(`Druckauftrag ${job.id} wurde erstellt und in die Warteschlange eingereiht.`)
      setTitle('')
      setIcon('')
      setMarkdown('')
      resetAttachment()
    } catch (err) {
      addToast(err instanceof ApiError ? err.message : 'Druckauftrag konnte nicht erstellt werden.', 'error')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <>
      <div className="page-header">
        <h2>Neuer Druckauftrag</h2>
      </div>

      <div className="card">
        <form className="form-grid" onSubmit={handleSubmit}>
          <div className="form-field">
            <label htmlFor="template">Vorlage</label>
            <select id="template" value={template} onChange={(event) => setTemplate(event.target.value)} required>
              {templates === null && <option value="">Lädt...</option>}
              {templates?.length === 0 && <option value="">Keine Vorlagen konfiguriert</option>}
              {templates?.map((entry) => (
                <option key={entry.key} value={entry.key}>
                  {entry.name} ({entry.type})
                </option>
              ))}
            </select>
          </div>

          <div className="form-field">
            <label htmlFor="title">Titel</label>
            <input id="title" type="text" value={title} onChange={(event) => setTitle(event.target.value)} />
          </div>

          <div className="form-field">
            <label htmlFor="icon">Icon (optional)</label>
            <IconPicker
              value={icon}
              onChange={setIcon}
              placeholder={
                selectedTemplate?.icon ? `Standard der Vorlage: ${selectedTemplate.icon}` : 'Icon auswählen...'
              }
            />
            <span className="form-hint">
              Leer lassen, um das Standard-Icon der Vorlage zu verwenden
              {selectedTemplate?.icon ? ` (${selectedTemplate.icon})` : ' (falls vorhanden)'}.
            </span>
          </div>

          <div className="form-field">
            <label htmlFor="markdown">Inhalt (Markdown)</label>
            <textarea
              id="markdown"
              value={markdown}
              onChange={(event) => setMarkdown(event.target.value)}
              placeholder={'# Aufgaben\n\n- [ ] Milch\n- [x] Brot'}
              disabled={!allowMarkdown}
            />
            {!allowMarkdown && (
              <span className="form-hint">
                Diese Vorlage hat ein festes Layout ohne Textfeld – die Fläche bleibt zum Malen frei.
              </span>
            )}
          </div>

          {allowAttachment && (
          <fieldset className="form-field attachment-field">
            <legend>Anhang (optional)</legend>
            <div className="attachment-type-selector">
              <label className="attachment-type-option">
                <input
                  type="radio"
                  name="attachment-type"
                  value="none"
                  checked={attachmentType === 'none'}
                  onChange={() => setAttachmentType('none')}
                />
                Kein Anhang
              </label>
              <label className="attachment-type-option">
                <input
                  type="radio"
                  name="attachment-type"
                  value="image"
                  checked={attachmentType === 'image'}
                  onChange={() => setAttachmentType('image')}
                />
                Bild
              </label>
              <label className="attachment-type-option">
                <input
                  type="radio"
                  name="attachment-type"
                  value="qr"
                  checked={attachmentType === 'qr'}
                  onChange={() => setAttachmentType('qr')}
                />
                QR-Code
              </label>
              <label className="attachment-type-option">
                <input
                  type="radio"
                  name="attachment-type"
                  value="table"
                  checked={attachmentType === 'table'}
                  onChange={() => setAttachmentType('table')}
                />
                Tabelle (CSV/XLSX)
              </label>
            </div>
            <span className="form-hint">
              {attachmentType === 'table'
                ? 'Tabelle wird als Markdown-Tabelle vor dem Inhalt eingefügt.'
                : 'Wird nach dem Titel und vor dem Inhalt gedruckt, automatisch in Schwarz/Weiß umgewandelt.'}
            </span>

            {attachmentType === 'image' && (
              <div className="attachment-section">
                <label htmlFor="image-upload">Bilddatei</label>
                <input id="image-upload" type="file" accept="image/*" onChange={handleImageFileChange} />
                {imageFileName && <span className="form-hint">{imageFileName}</span>}
                {imageError && <p className="error-text">{imageError}</p>}
              </div>
            )}

            {attachmentType === 'qr' && (
              <div className="attachment-section">
                <label htmlFor="qr-type">QR-Code-Typ</label>
                <select id="qr-type" value={qrType} onChange={(event) => setQrType(event.target.value as QrType)}>
                  <option value="url">URL</option>
                  <option value="wifi">WLAN</option>
                  <option value="vcard">Kontakt (vCard)</option>
                  <option value="location">Standort</option>
                </select>

                {qrType === 'url' && (
                  <div className="attachment-qr-fields">
                    <input
                      type="url"
                      placeholder="https://example.com"
                      value={qrUrl}
                      onChange={(event) => setQrUrl(event.target.value)}
                    />
                  </div>
                )}

                {qrType === 'wifi' && (
                  <div className="attachment-qr-fields">
                    <input
                      type="text"
                      placeholder="Netzwerkname (SSID)"
                      value={wifiSsid}
                      onChange={(event) => setWifiSsid(event.target.value)}
                    />
                    <select value={wifiEncryption} onChange={(event) => setWifiEncryption(event.target.value as WifiEncryption)}>
                      <option value="WPA">WPA/WPA2</option>
                      <option value="WEP">WEP</option>
                      <option value="nopass">Kein Passwort</option>
                    </select>
                    {wifiEncryption !== 'nopass' && (
                      <input
                        type="text"
                        placeholder="Passwort"
                        value={wifiPassword}
                        onChange={(event) => setWifiPassword(event.target.value)}
                      />
                    )}
                    <label className="form-field-checkbox">
                      <input type="checkbox" checked={wifiHidden} onChange={(event) => setWifiHidden(event.target.checked)} />
                      Verstecktes Netzwerk
                    </label>
                  </div>
                )}

                {qrType === 'vcard' && (
                  <div className="attachment-qr-fields">
                    <input
                      type="text"
                      placeholder="Name"
                      value={vcardName}
                      onChange={(event) => setVcardName(event.target.value)}
                    />
                    <input
                      type="tel"
                      placeholder="Telefon (optional)"
                      value={vcardPhone}
                      onChange={(event) => setVcardPhone(event.target.value)}
                    />
                    <input
                      type="email"
                      placeholder="E-Mail (optional)"
                      value={vcardEmail}
                      onChange={(event) => setVcardEmail(event.target.value)}
                    />
                    <input
                      type="text"
                      placeholder="Firma (optional)"
                      value={vcardOrg}
                      onChange={(event) => setVcardOrg(event.target.value)}
                    />
                  </div>
                )}

                {qrType === 'location' && (
                  <div className="attachment-qr-fields">
                    <input
                      type="text"
                      placeholder="Breitengrad, z. B. 52.5200"
                      value={locationLat}
                      onChange={(event) => setLocationLat(event.target.value)}
                    />
                    <input
                      type="text"
                      placeholder="Längengrad, z. B. 13.4050"
                      value={locationLon}
                      onChange={(event) => setLocationLon(event.target.value)}
                    />
                    <input
                      type="text"
                      placeholder="Bezeichnung (optional)"
                      value={locationLabel}
                      onChange={(event) => setLocationLabel(event.target.value)}
                    />
                  </div>
                )}
              </div>
            )}

            {attachmentType === 'table' && (
              <div className="attachment-section">
                <label htmlFor="table-upload">Tabellendatei (CSV oder XLSX)</label>
                <input
                  id="table-upload"
                  type="file"
                  accept=".csv,.xlsx"
                  onChange={handleTableFileChange}
                  disabled={tableLoading}
                />
                {tableLoading && <span className="form-hint">Tabelle wird verarbeitet…</span>}
                {tableError && <p className="error-text">{tableError}</p>}
                {tableResult && (
                  <div>
                    <span className="form-hint">
                      {tableResult.rows} Zeile{tableResult.rows !== 1 ? 'n' : ''},{' '}
                      {tableResult.columns} Spalte{tableResult.columns !== 1 ? 'n' : ''} – bereit zum Drucken.
                    </span>
                    {tableResult.warnings.map((w) => (
                      <p key={w} className="form-hint" style={{ color: 'var(--color-warning, #b45309)' }}>
                        ⚠ {w}
                      </p>
                    ))}
                  </div>
                )}
              </div>
            )}
          </fieldset>
          )}

          <div className="form-field form-field-checkbox">
            <input
              id="print-timestamp"
              type="checkbox"
              checked={printTimestamp}
              onChange={(event) => setPrintTimestamp(event.target.checked)}
            />
            <label htmlFor="print-timestamp">Druckdatum/Uhrzeit unten rechts drucken</label>
          </div>

          <div className="form-actions">
            <button type="submit" className="button button-primary" disabled={submitting || !template || !hasContent}>
              {submitting ? 'Wird erstellt...' : 'Druckauftrag erstellen'}
            </button>
            {!hasContent && (
              <span className="form-hint">Titel, Inhalt, Bild oder QR-Code angeben, um drucken zu können.</span>
            )}
          </div>

        </form>
      </div>

      <div className="card">
        <h3>Vorschau</h3>
        <PreviewPane
          enabled={Boolean(template)}
          template={template}
          title={title}
          icon={icon || null}
          markdown={
            attachmentType === 'table' && tableResult
              ? [tableResult.markdown, markdown].filter(Boolean).join('\n\n')
              : markdown
          }
          printTimestamp={printTimestamp}
          imageBase64={attachmentType === 'image' ? imageBase64 : null}
          qrCode={attachmentType === 'qr' ? qrCodeContent : null}
        />
      </div>
    </>
  )
}
