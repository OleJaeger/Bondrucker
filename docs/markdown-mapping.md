# Markdown → ESC/POS Mapping

Markdown wird mit `mistune` (AST-Modus, Plugins `table`, `task_lists`,
`strikethrough`) in eine druckerunabhängige Zwischendarstellung (IR,
`app/rendering/document.py`) übersetzt (`app/rendering/markdown.py`). Sowohl der
ESC/POS-Renderer als auch der PNG-Vorschau-Renderer konsumieren dieselbe IR – die
Vorschau entspricht daher exakt dem gedruckten Ergebnis.

Die effektive Zeilenbreite ist `PRINTER_WIDTH_CHARS` (Default 48, Font A auf
80 mm), pro Vorlage über `layout.width_chars` in der YAML-Konfiguration
überschreibbar.

## Unterstützte Elemente

| Markdown | IR-Block | ESC/POS-Darstellung |
|---|---|---|
| `# Überschrift` (H1) | `Heading(level=1)` | Zentriert, fett, doppelte Höhe – kleiner als der Auftragstitel (der doppelte Breite **und** Höhe nutzt). |
| `## Überschrift` / `### ...` (H2+) | `Heading(level>=2)` | Zentriert, fett, normale Größe – kleiner als H1 und der Auftragstitel. |
| Absatz | `Paragraph` | Linksbündig (oder gemäß `default_formatting.body.align` der Vorlage), wortumgebrochen auf `width_chars`. |
| `**fett**` | `TextRun(bold=True)` | Fettdruck (ESC/POS Emphasized Mode). |
| `*kursiv*` / `_kursiv_` | `TextRun(italic=True)` | Da ESC/POS-Drucker i. d. R. keinen echten Kursivmodus haben, wird Kursiv- **und** Unterstrichen-Markup als **Unterstrichen** dargestellt. |
| `` `code` `` (inline) | als normaler `TextRun` | Wie normaler Text (kein Monospace-Wechsel). |
| `- Punkt` / `* Punkt` | `ListItem(ordered=False)` | `"- "`-Präfix, hängender Einzug bei Umbruch. |
| `1. Punkt` | `ListItem(ordered=True)` | `"<n>. "`-Präfix mit fortlaufender Nummerierung. |
| `- [ ] Aufgabe` / `- [x] Aufgabe` | `ListItem(checked=False/True)` | Als Bitmap gedruckt: FontAwesome-Icon (`fa-square` / `fa-square-check`) gefolgt vom umgebrochenen Aufgabentext – identisch in Vorschau und Druck (`render_checklist_item`, `app/rendering/text_image.py`). |
| Verschachtelte Listen | `ListItem(level=n)` | Zusätzlicher Einzug von 2 Zeichen pro Ebene (`LIST_INDENT`). |
| Tabelle (`table`-Plugin) | `TableBlock` | Spaltenbreiten proportional zur größten Zellenlänge je Spalte, ggf. proportional auf `width_chars` herunterskaliert (Minimum `MIN_COLUMN_WIDTH=3` Zeichen). Kopfzeile fett, darunter `-`-Trennzeile. Ausrichtung (`:--`, `:-:`, `--:`) wird übernommen. |
| Zeilenumbruch (zwei Leerzeichen / `\` / einfacher Zeilenumbruch im Quelltext) | `TextRun(text="\n")` | Erzwungener Zeilenumbruch innerhalb eines Blocks – jeder Zeilenumbruch, den der Nutzer im Eingabefeld erzeugt, wird 1:1 auf dem Beleg übernommen (kein Zusammenfassen zu einem Leerzeichen). |
| `---` / `***` (Thematic Break) | `ThematicBreak` | Volle Zeile aus `-`-Zeichen (`width_chars` lang). |
| Leere Zeile | – | Wird ignoriert (kein zusätzlicher Leerraum). |

## Degradierte / nicht unterstützte Elemente

ESC/POS-Drucker bieten kein vollständiges Markdown-Rendering. Elemente ohne
sinnvolle Entsprechung werden **nicht** verworfen, sondern auf eine einfachere
Darstellung reduziert, damit ein Druckauftrag nie wegen eines einzelnen
unbekannten Elements fehlschlägt:

| Markdown | Degradiertes Verhalten |
|---|---|
| `[Linktext](url)` | Nur `Linktext` wird gedruckt, die URL entfällt. |
| `![Alt](bild.png)` | Wird zu `[Alt]` (Platzhalter mit Alt-Text); ohne Alt-Text entfällt das Bild komplett. Eingebettete Bilddateien werden nicht geladen/gedruckt. |
| `~~durchgestrichen~~` | Wird als normaler Text gedruckt (keine Durchstreichung auf ESC/POS). |
| Codeblock (```` ``` ````) | Wird als linksbündiger Klartext-Absatz gedruckt (Zeilenumbrüche im Code bleiben erhalten, kein Monospace/Rahmen). |
| `> Zitat` (Block Quote) | Jede enthaltene Zeile (Absatz, Überschrift, Listenpunkt) wird mit `"> "` präfixiert. |
| Unbekannte/zukünftige Markdown-Knoten | Etwaige Kindelemente werden "flach" in den umgebenden Inhalt übernommen; ist auch das nicht möglich, wird der Knoten ohne Fehler verworfen. |

## Limits und Validierung

- **Maximale Länge**: 50.000 Zeichen Markdown-Quelltext
  (`_MAX_MARKDOWN_LENGTH` in `app/rendering/markdown.py`). Längere Eingaben
  führen zu `400 Bad Request` (`InvalidMarkdownError`) – der Job wird gar nicht
  erst angelegt.
- **Parsing-Fehler**: Jeder Fehler von `mistune` oder bei der IR-Konvertierung
  wird zu `InvalidMarkdownError` (→ `400`) – es entsteht kein Job, der garantiert
  in der Warteschlange fehlschlagen würde.

## Icons

Ein optionales Font-Awesome-Icon (`icon`-Feld im Job oder Default aus der
Vorlage) wird **vor** dem Titel zentriert als Bitmap gedruckt (siehe
[`components.md`](components.md) → `app/rendering/icons.py`). Fehlt die
Font-Awesome-Schriftdatei oder ist das Icon unbekannt, wird ein
Platzhalter-Rahmen mit dem (gekürzten) Iconnamen gedruckt – nie ein Fehler.

## Anhänge: Bild-Upload und QR-Code

Ein Druckauftrag kann zusätzlich **ein** Bild (`image_base64`) **oder** einen
QR-Code (`qr_code`) enthalten. Beide werden als `ImageBlock` (Bitmap, Modus
`"1"`) **nach dem Titel und vor dem Markdown-Inhalt** eingefügt
(`app/rendering/builder.py`) und identisch in Vorschau und Druck dargestellt
(`printer.image()`, ESC/POS-Rasterkommando `GS v 0`). Beide Felder gleichzeitig
zu setzen führt zu `400 Bad Request` (`"Bild und QR-Code koennen nicht
gleichzeitig gedruckt werden."`).

| Feld | Inhalt | Verarbeitung (`app/rendering/attachments.py`) |
|---|---|---|
| `image_base64` | Bilddatei als Base64 (optional mit `data:image/...;base64,`-Präfix), max. 5 MB dekodiert. | Wird nach Graustufen konvertiert, proportional auf `PRINTER_WIDTH_PX` skaliert (Höhe auf max. 2000 px begrenzt), gerastert (Floyd-Steinberg, Modus `"1"`) und bei Bedarf auf voller Breite zentriert. |
| `qr_code` | Beliebiger Text (max. 2000 Zeichen): URL, `WIFI:T:...;S:...;P:...;;`, vCard (`BEGIN:VCARD...END:VCARD`) oder `geo:<lat>,<lon>`. | Wird als QR-Code gerendert (zweistufige Größenbestimmung für scharfe Module, max. 384 px Kantenlänge) und zentriert. Leerer Inhalt führt zu `400 Bad Request`. |

Das Frontend (Seite "Neuer Druckauftrag") bietet dafür einen Anhang-Bereich
mit Bild-Upload (liest die Datei per `FileReader` als `data:`-URL) und einem
QR-Code-Generator mit den Untertypen **URL**, **WLAN**, **Kontakt (vCard)** und
**Standort** – die jeweiligen Formularfelder werden clientseitig zum
passenden QR-Inhalt zusammengesetzt.

Wie alle anderen Job-Felder werden auch `image_base64`/`qr_code` beim
Abschluss eines Jobs aus der Datenbank entfernt (`payload_json = NULL`).

## Layout-Parameter pro Vorlage

Jede Vorlage (`backend/config/templates/*.yaml`) kann folgende Werte
überschreiben (sonst gelten die globalen `PRINTER_*`-Einstellungen):

| Feld | Bedeutung |
|---|---|
| `layout.width_chars` | Zeichen pro Zeile (überschreibt `PRINTER_WIDTH_CHARS`). |
| `layout.cut` | Papierschnitt nach dem Druck (`true`/`false`). |
| `layout.feed_lines` | Anzahl Leerzeilen-Vorschub vor dem Schnitt. |
| `default_formatting.title` | Stil des Titels (`align`, `bold`, `underline`, `double_width`, `double_height`). |
| `default_formatting.body` | Standard-Ausrichtung des Fließtexts. |
| `icon` | Standard-Icon, falls der Job selbst keines angibt. |

Siehe `backend/config/templates/freitext.yaml` und `todo.yaml` für vollständige
Beispiele.
