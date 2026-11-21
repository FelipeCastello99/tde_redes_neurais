#!/usr/bin/env python3
"""Empacota o código, notebook executado, documento e capturas para entrega."""

from __future__ import annotations

import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DIST = ROOT / "dist"
TARGET = DIST / "TDE_redes_neurais_entrega.zip"
PREFIX = "TDE_redes_neurais_entrega"

EXCLUDED_PARTS = {
    ".git",
    ".venv",
    ".specs",
    ".next",
    "node_modules",
    "test-results",
    "playwright-report",
    "dist",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    "artifacts",
}

EXCLUDED_SUFFIXES = {".pyc", ".pyo", ".zip", ".csv", ".tsbuildinfo"}


def include(path: Path) -> bool:
    relative = path.relative_to(ROOT)
    if any(part in EXCLUDED_PARTS for part in relative.parts):
        return False
    if any(part.endswith(".egg-info") for part in relative.parts):
        return False
    if path.suffix in EXCLUDED_SUFFIXES:
        return False
    return path.name not in {".env"}


def main() -> None:
    DIST.mkdir(exist_ok=True)
    if TARGET.exists():
        TARGET.unlink()

    with zipfile.ZipFile(TARGET, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(ROOT.rglob("*")):
            if not path.is_file() or not include(path):
                continue
            relative = path.relative_to(ROOT)
            archive.write(path, f"{PREFIX}/{relative.as_posix()}")

    size_mb = TARGET.stat().st_size / (1024 * 1024)
    print(f"Pacote: {TARGET} ({size_mb:.1f} MB)")


if __name__ == "__main__":
    main()
