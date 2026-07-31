#!/usr/bin/env python
"""Export the FastAPI app's OpenAPI schema to ``docs/openapi.yaml``.

The schema is generated from the running application definition (routes,
Pydantic models, docstrings) so it can never drift from the actual API.

Usage (from the ``backend`` directory):

    .venv/bin/python scripts/export_openapi.py
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import yaml

BACKEND_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKEND_DIR.parent
OUTPUT_PATH = REPO_ROOT / "docs" / "openapi.yaml"


def main() -> None:
    sys.path.insert(0, str(BACKEND_DIR))

    # Settings.api_key has no default - provide a placeholder so the app can
    # be imported without a real .env file. This value is never used.
    os.environ.setdefault("API_KEY", "export-openapi-placeholder")
    os.environ.setdefault("TEMPLATES_DIR", str(BACKEND_DIR / "config" / "templates"))
    os.environ.setdefault("PRESETS_DIR", str(BACKEND_DIR / "config" / "presets"))

    from app.main import app

    schema = app.openapi()

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_PATH.open("w", encoding="utf-8") as fh:
        yaml.safe_dump(schema, fh, sort_keys=False, allow_unicode=True)

    print(f"Wrote OpenAPI schema to {OUTPUT_PATH.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    main()
