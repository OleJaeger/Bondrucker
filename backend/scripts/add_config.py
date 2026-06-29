#!/usr/bin/env python
"""Interaktiver Helfer, um eine neue Vorlage (Template) oder ein neues
Standarddruckobjekt (Preset) anzulegen.

Legt die YAML-Datei unter ``backend/config/templates/`` bzw.
``backend/config/presets/`` an und ergaenzt den neuen Key automatisch in den
Tests, die alle ausgelieferten Templates/Presets aufzaehlen
(``test_templates.py``, ``test_presets.py``, ``test_presets_api.py``) -
damit ein vergessener Test-Eintrag sofort als fehlschlagender Test auffaellt
statt unbemerkt zu bleiben.

Nutzung (aus dem ``backend``-Verzeichnis):

    .venv/bin/python scripts/add_config.py preset
    .venv/bin/python scripts/add_config.py template
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
PRESETS_DIR = BACKEND_DIR / "config" / "presets"
TEMPLATES_DIR = BACKEND_DIR / "config" / "templates"
TESTS_DIR = BACKEND_DIR / "tests"

KEY_RE = re.compile(r"^[a-z][a-z0-9-]*$")


def prompt(label: str, default: str = "", required: bool = True) -> str:
    suffix = f" [{default}]" if default else ""
    while True:
        value = input(f"{label}{suffix}: ").strip()
        if not value:
            value = default
        if value or not required:
            return value
        print("  -> Pflichtfeld, bitte einen Wert eingeben.")


def prompt_bool(label: str, default: bool) -> bool:
    default_label = "j" if default else "n"
    while True:
        value = input(f"{label} (j/n) [{default_label}]: ").strip().lower()
        if not value:
            return default
        if value in ("j", "y", "ja", "yes"):
            return True
        if value in ("n", "no", "nein"):
            return False
        print("  -> bitte 'j' oder 'n' eingeben.")


def prompt_key(existing: set[str]) -> str:
    while True:
        key = input("Key (Dateiname ohne .yaml, z.B. 'mein-preset'): ").strip()
        if not KEY_RE.match(key):
            print("  -> nur Kleinbuchstaben, Ziffern und '-', muss mit einem Buchstaben beginnen.")
            continue
        if key in existing:
            print(f"  -> '{key}' existiert bereits.")
            continue
        return key


def yaml_str(value: str) -> str:
    """Quoted YAML scalar (sicher fuer Umlaute, Anfuehrungszeichen etc.)."""

    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


# ---------------------------------------------------------------------------
# Preset
# ---------------------------------------------------------------------------


def add_preset() -> str:
    existing = {p.stem for p in PRESETS_DIR.glob("*.yaml")}
    key = prompt_key(existing)
    name = prompt("Name (Anzeigename)")
    description = prompt("Beschreibung")
    icon = prompt("Icon (z.B. fa-star oder svg-logo)")

    template_keys = sorted(p.stem for p in TEMPLATES_DIR.glob("*.yaml"))
    print(f"Verfuegbare Templates: {', '.join(template_keys) or '(keine gefunden)'}")
    template = prompt("Template-Key")
    if template not in template_keys:
        print(f"  Warnung: Template '{template}' existiert nicht in {TEMPLATES_DIR}.")

    title = prompt("Titel (optional)", required=False)
    print_timestamp = prompt_bool("Zeitstempel drucken?", default=True)

    lines = [
        f"# Standarddruckobjekt: {name}",
        "#",
        f"# {description}",
        "",
        f"name: {yaml_str(name)}",
        f"description: {yaml_str(description)}",
        f"icon: {yaml_str(icon)}",
        f"template: {yaml_str(template)}",
        "",
    ]
    if title:
        lines.append(f"title: {yaml_str(title)}")
    lines.append(f"print_timestamp: {str(print_timestamp).lower()}")
    lines += [
        "",
        "# Optional: statischer Markdown-Inhalt (exklusiv zu content_script)",
        '# content: "..."',
        "",
        "# Optional: Python-Modul in app.presets.scripts mit generate() -> str",
        '# content_script: "mein_modul"',
        "",
        "# Optional: Anhang (QR-Code oder Bild)",
        "# attachment:",
        "#   type: qr_code",
        '#   content: "..."',
    ]

    path = PRESETS_DIR / f"{key}.yaml"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Geschrieben: {path.relative_to(BACKEND_DIR)}")
    return key


# ---------------------------------------------------------------------------
# Template
# ---------------------------------------------------------------------------


def add_template() -> str:
    existing = {p.stem for p in TEMPLATES_DIR.glob("*.yaml")}
    key = prompt_key(existing)
    name = prompt("Name (Anzeigename)")
    type_ = prompt("Type", default=key)
    icon = prompt("Standard-Icon (optional, z.B. fa-star)", required=False)

    lines = [
        f"# Vorlage: {name}",
        "",
        f"name: {yaml_str(name)}",
        f"type: {yaml_str(type_)}",
        "",
    ]
    if icon:
        lines.append(f"icon: {yaml_str(icon)}")
        lines.append("")
    lines += [
        "layout:",
        "  width_chars: 48",
        "  cut: true",
        "  feed_lines: 3",
        "",
        "# default_formatting:",
        "#   title:",
        "#     align: center",
        "#     bold: true",
        "#   body:",
        "#     align: left",
        "",
        "# fields:",
        "#   markdown: true",
        "#   attachment: true",
        "",
        '# default_markdown: "..."',
    ]

    path = TEMPLATES_DIR / f"{key}.yaml"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Geschrieben: {path.relative_to(BACKEND_DIR)}")
    return key


# ---------------------------------------------------------------------------
# Test-Updates: neuen Key in die Set-Literale eintragen, die alle
# ausgelieferten Configs aufzaehlen.
# ---------------------------------------------------------------------------


def _insert_into_set_literal(text: str, anchor: re.Pattern[str], new_key: str) -> tuple[str, bool]:
    match = anchor.search(text)
    if not match:
        return text, False

    inside = match.group(1)
    items = re.findall(r'"([^"]+)"', inside)
    if new_key in items:
        return text, False
    items.append(new_key)

    if "\n" in inside:
        indent_match = re.search(r'\n(\s*)"', inside)
        indent = indent_match.group(1) if indent_match else "        "
        closing_indent = indent[:-4] if len(indent) >= 4 else ""
        rendered = "\n" + "".join(f'{indent}"{item}",\n' for item in items) + closing_indent
    else:
        rendered = ", ".join(f'"{item}"' for item in items)

    new_text = text[: match.start(1)] + rendered + text[match.end(1) :]
    return new_text, True


def _apply(path: Path, anchor: re.Pattern[str], key: str) -> None:
    text = path.read_text(encoding="utf-8")
    new_text, changed = _insert_into_set_literal(text, anchor, key)
    rel = path.relative_to(BACKEND_DIR)
    if changed:
        path.write_text(new_text, encoding="utf-8")
        print(f"Aktualisiert: {rel}")
    else:
        print(f"Hinweis: '{key}' war in {rel} bereits enthalten oder die erwartete Stelle wurde nicht gefunden - bitte manuell pruefen.")


def update_preset_tests(key: str) -> None:
    _apply(TESTS_DIR / "test_presets.py", re.compile(r"assert keys == \{([^}]*)\}"), key)
    _apply(TESTS_DIR / "test_presets_api.py", re.compile(r"assert set\(presets\) == \{([^}]*)\}"), key)


def update_template_tests(key: str) -> None:
    _apply(TESTS_DIR / "test_templates.py", re.compile(r"assert keys == \{([^}]*)\}"), key)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("kind", choices=["preset", "template"], help="Was soll angelegt werden?")
    args = parser.parse_args()

    if args.kind == "preset":
        key = add_preset()
        update_preset_tests(key)
    else:
        key = add_template()
        update_template_tests(key)

    print(f"\nFertig. Backend neu starten, damit '{key}' geladen wird.")


if __name__ == "__main__":
    main()
