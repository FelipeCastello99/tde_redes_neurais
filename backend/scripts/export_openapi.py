"""Gera o contrato OpenAPI consumido pelo frontend.

Uso (a partir de `backend/`):
    python scripts/export_openapi.py
"""

from __future__ import annotations

import json
from pathlib import Path

from api.main import app

PROJECT_ROOT = Path(__file__).resolve().parents[2]
TARGET = PROJECT_ROOT / "frontend" / "lib" / "openapi.json"


def main() -> None:
    TARGET.parent.mkdir(parents=True, exist_ok=True)
    TARGET.write_text(
        json.dumps(app.openapi(), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"OpenAPI escrito em {TARGET}")


if __name__ == "__main__":
    main()
