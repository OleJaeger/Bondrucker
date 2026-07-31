# Eigene SVG-Icons

Zusätzlich zu den Font-Awesome-Icons (siehe
`backend/assets/fontawesome/README.md`) kann hier ein beliebiges Set eigener
Icons als SVG-Dateien hinterlegt werden.

```
backend/assets/icons/
└── logo.svg   -> Icon-Name "svg-logo"
```

Jede `.svg`-Datei wird unter dem Namen `svg-<dateiname-ohne-endung>`
verfügbar (z.B. `logo.svg` -> `svg-logo`). Der Name erscheint zusammen mit
den Font-Awesome-Icons in `GET /api/icons` und im Icon-Picker des Frontends.

Das Verzeichnis ist über `CUSTOM_ICONS_DIR` konfigurierbar (siehe
`.env.example`), falls ein anderer Ort verwendet werden soll.

## Hinweise

- SVGs sollten ein quadratisches `viewBox` haben und ohne Farbangabe (Default
  schwarz) gezeichnet sein - sie werden für den Druck in Graustufen
  gerendert und auf 1-Bit (schwarz/weiß) reduziert.
- Nach dem Hinzufügen/Ändern einer Datei muss das Backend neu gestartet
  werden, damit die Icon-Liste neu eingelesen wird.
