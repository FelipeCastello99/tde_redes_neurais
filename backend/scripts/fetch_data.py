#!/usr/bin/env python3
"""Baixa, extrai e valida o CSV do DATATRAN 2024 da PRF.

O arquivo é publicado pela Polícia Rodoviária Federal na página de dados
abertos e, atualmente, hospedado no Google Drive. Como o link pode mudar,
o script valida o SHA-256 do CSV: se o conteúdo oficial for atualizado,
use ``--allow-hash-mismatch`` e registre a mudança em ``docs/dataset.md``.

Uso (a partir de ``backend/``, ou ``make fetch`` na raiz):
    python scripts/fetch_data.py            # baixa se necessário e valida
    python scripts/fetch_data.py --check    # só valida o arquivo local
    python scripts/fetch_data.py --force    # baixa de novo
    python scripts/fetch_data.py --keep-zip # mantém o .zip baixado

Saída: backend/data/raw/datatran2024.csv
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import shutil
import sys
import urllib.error
import urllib.request
import zipfile
from collections import Counter
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = BACKEND_ROOT / "data" / "raw"
CSV_PATH = DATA_DIR / "datatran2024.csv"
ZIP_PATH = DATA_DIR / "prf_datatran2024.zip"

DRIVE_FILE_ID = "14lB0vqMFkaZj8HZ44b0njYgxs9nAN8KO"
DOWNLOAD_URL = f"https://drive.google.com/uc?export=download&id={DRIVE_FILE_ID}"

# Contrato de integridade do arquivo usado no trabalho (versão de 2026-09-23).
ZIP_SHA256 = "905dac836867297b261e4edefff6cdb470809814e7e1796b3f2f57517099d165"
CSV_SHA256 = "7d26e6f4528c2ca2636a8fea2c5bc8755a0ff6a182d82c238a8793b016e4366d"
EXPECTED_SIZE = 21_365_616
EXPECTED_ROWS = 73_202
EXPECTED_COLS = 30
ENCODING = "latin-1"
SEPARATOR = ";"

EXPECTED_COLUMNS = [
    "id",
    "data_inversa",
    "dia_semana",
    "horario",
    "uf",
    "br",
    "km",
    "municipio",
    "causa_acidente",
    "tipo_acidente",
    "classificacao_acidente",
    "fase_dia",
    "sentido_via",
    "condicao_metereologica",
    "tipo_pista",
    "tracado_via",
    "uso_solo",
    "pessoas",
    "mortos",
    "feridos_leves",
    "feridos_graves",
    "ilesos",
    "ignorados",
    "feridos",
    "veiculos",
    "latitude",
    "longitude",
    "regional",
    "delegacia",
    "uop",
]

CHUNK = 1 << 20


def sha256sum(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(CHUNK), b""):
            digest.update(chunk)
    return digest.hexdigest()


def human_size(num_bytes: int) -> str:
    value = float(num_bytes)
    for unit in ("B", "KB", "MB", "GB"):
        if value < 1024 or unit == "GB":
            return f"{value:.1f} {unit}" if unit != "B" else f"{int(value)} B"
        value /= 1024
    return f"{value:.1f} GB"


def download(url: str, dest: Path) -> None:
    """Baixa ``url`` para ``dest`` de forma atômica (``.part`` → rename)."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    part = dest.with_name(dest.name + ".part")
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "Mozilla/5.0 (compatible; tde-redes-neurais/0.1)"},
    )
    print(f"→ baixando: {url}")
    try:
        with urllib.request.urlopen(request, timeout=180) as response, part.open("wb") as fh:
            total = int(response.headers.get("Content-Length") or 0)
            copied = 0
            while chunk := response.read(CHUNK):
                fh.write(chunk)
                copied += len(chunk)
                if total:
                    pct = 100 * copied / total
                    print(f"\r  {human_size(copied)} / {human_size(total)} ({pct:5.1f}%)", end="")
        print()
    except PermissionError as exc:
        raise SystemExit(
            "sem permissão para escrever em "
            f"{part.parent}.\n"
            "No Docker, ajuste HOST_UID/HOST_GID no .env (use `make env`) "
            "ou rode o serviço data como root em uma VPS.\n"
            f"Detalhe: {exc}"
        ) from exc
    except (urllib.error.URLError, TimeoutError) as exc:
        part.unlink(missing_ok=True)
        raise SystemExit(f"erro no download: {exc}\nVerifique a conexão ou use --url com outro link.") from exc

    # O Google Drive devolve HTML quando o arquivo é grande demais para
    # varredura ou quando o link expira. Detectar aqui evita um zip inválido.
    with part.open("rb") as fh:
        head = fh.read(512).lstrip().lower()
    if head.startswith((b"<!doctype", b"<html")):
        part.unlink(missing_ok=True)
        raise SystemExit(
            "o link devolveu uma página HTML em vez do arquivo.\n"
            "Abra a página oficial da PRF, copie o link atual do CSV de 2024 e rode:\n"
            "  python scripts/fetch_data.py --force --url '<novo-link>'"
        )

    part.replace(dest)


def extract_csv(zip_path: Path, target: Path) -> None:
    try:
        with zipfile.ZipFile(zip_path) as archive:
            members = [name for name in archive.namelist() if name.lower().endswith(".csv")]
            if len(members) != 1:
                raise SystemExit(
                    f"esperava 1 CSV no zip, encontrei {len(members)}: {members}"
                )
            with archive.open(members[0]) as source, target.open("wb") as dest:
                shutil.copyfileobj(source, dest)
    except zipfile.BadZipFile as exc:
        raise SystemExit(f"zip inválido: {exc}") from exc


def validate(csv_path: Path, allow_hash_mismatch: bool) -> dict[str, object]:
    """Valida estrutura, volumetria, hash e balanceamento do alvo."""
    problems: list[str] = []
    if not csv_path.exists():
        raise SystemExit(f"arquivo não encontrado: {csv_path}\nRode: make fetch")

    size = csv_path.stat().st_size
    digest = sha256sum(csv_path)

    if size != EXPECTED_SIZE:
        problems.append(f"tamanho {size:,} bytes (esperado {EXPECTED_SIZE:,})".replace(",", "."))
    if digest != CSV_SHA256:
        message = f"SHA-256 {digest} difere do esperado {CSV_SHA256}"
        if allow_hash_mismatch:
            print(f"! aviso: {message} (ignorado por --allow-hash-mismatch)")
        else:
            problems.append(message + " (use --allow-hash-mismatch se o arquivo foi atualizado)")

    rows = 0
    class_counts: Counter[str] = Counter()
    deaths = 0
    null_target = 0

    with csv_path.open(encoding=ENCODING, newline="") as fh:
        reader = csv.reader(fh, delimiter=SEPARATOR)
        try:
            header = next(reader)
        except StopIteration:
            raise SystemExit("arquivo vazio") from None

        if header != EXPECTED_COLUMNS:
            missing = sorted(set(EXPECTED_COLUMNS) - set(header))
            extra = sorted(set(header) - set(EXPECTED_COLUMNS))
            problems.append(
                f"cabeçalho inesperado ({len(header)} colunas); faltando={missing}; extras={extra}"
            )
            return {"problems": problems, "header": header}

        idx_class = header.index("classificacao_acidente")
        idx_deaths = header.index("mortos")

        for row in reader:
            rows += 1
            if len(row) != len(header):
                problems.append(f"linha {rows + 1} tem {len(row)} campos")
                break
            label = row[idx_class].strip() or "NA"
            class_counts[label] += 1
            if label == "NA":
                null_target += 1
            try:
                deaths += int(row[idx_deaths] or 0) > 0
            except ValueError:
                problems.append(f"valor não numérico em mortos na linha {rows + 1}")

    if rows != EXPECTED_ROWS:
        problems.append(f"{rows:,} registros (esperado {EXPECTED_ROWS:,})".replace(",", "."))
    if null_target > 1:
        problems.append(f"{null_target} registros com alvo 'NA' (esperado no máximo 1)")

    return {
        "problems": problems,
        "size": size,
        "sha256": digest,
        "rows": rows,
        "columns": len(header),
        "classes": class_counts,
        "deaths": deaths,
    }


def print_summary(report: dict[str, object]) -> None:
    rows = int(report["rows"])
    deaths = int(report["deaths"])
    print("\nResumo do dataset")
    print(f"  registros : {rows:,}".replace(",", "."))
    print(f"  colunas   : {report['columns']}")
    print(f"  tamanho   : {human_size(int(report['size']))}")
    print(f"  SHA-256   : {report['sha256']}")
    print(f"  fatais    : {deaths:,} ({100 * deaths / rows:.1f}%)".replace(",", "."))
    print("  classes   :")
    for label, count in sorted(report["classes"].items(), key=lambda item: -item[1]):
        print(f"    - {label}: {count:,} ({100 * count / rows:.1f}%)".replace(",", "."))
    print("\nPróximo passo: abra o notebook ou rode `pytest` (Fase 1 em diante).")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--check", action="store_true", help="apenas valida o CSV existente")
    parser.add_argument("--force", action="store_true", help="baixa novamente mesmo se o CSV existir")
    parser.add_argument("--keep-zip", action="store_true", help="mantém o .zip após extrair")
    parser.add_argument("--allow-hash-mismatch", action="store_true", help="aceita CSV com hash diferente")
    parser.add_argument("--url", default=DOWNLOAD_URL, help="URL alternativa do arquivo zip")
    args = parser.parse_args(argv)

    try:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
    except PermissionError as exc:
        raise SystemExit(
            f"sem permissão para criar {DATA_DIR}.\n"
            "No Docker, rode `make env` e suba novamente; em VPS root use HOST_UID=0/HOST_GID=0.\n"
            f"Detalhe: {exc}"
        ) from exc

    need_download = args.force or not CSV_PATH.exists()
    if args.check and need_download and not CSV_PATH.exists():
        raise SystemExit(f"nada para validar: {CSV_PATH} não existe")

    if not args.check and need_download:
        download(args.url, ZIP_PATH)
        zip_digest = sha256sum(ZIP_PATH)
        if zip_digest != ZIP_SHA256:
            print(f"! aviso: SHA-256 do zip difere do registrado ({zip_digest})")
        print("→ extraindo CSV…")
        extract_csv(ZIP_PATH, CSV_PATH)
        if not args.keep_zip:
            ZIP_PATH.unlink(missing_ok=True)

    report = validate(CSV_PATH, args.allow_hash_mismatch)
    problems = report.get("problems", [])

    if problems:
        print("\nFalha na validação:", file=sys.stderr)
        for problem in problems:
            print(f"  ✗ {problem}", file=sys.stderr)
        return 1

    print("✓ arquivo íntegro e compatível com o esperado")
    print_summary(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
