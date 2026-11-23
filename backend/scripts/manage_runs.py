#!/usr/bin/env python3
"""Lista, apaga e audita runs treinados (banco + artefatos em disco).

Uso:
    python scripts/manage_runs.py list [--limit 50] [--json]
    python scripts/manage_runs.py delete <id-ou-prefixo> [--yes]
    python scripts/manage_runs.py prune --keep 5 [--status failed,canceled]
                                        [--include-demo] [--dry-run] [--yes]
    python scripts/manage_runs.py doctor [--fix]

O comando sempre usa ``api.store.delete_run``: a linha do Postgres e a pasta
em ``ARTIFACTS_DIR/runs/<id>`` são removidas na mesma operação. Nunca apague
artefatos com ``rm -rf`` sem remover o registro correspondente.
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
import uuid
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from sqlalchemy.exc import SQLAlchemyError  # noqa: E402

from api import db, store  # noqa: E402
from nn.utils import ARTIFACTS_DIR  # noqa: E402

ACTIVE_STATUSES = {"queued", "running"}
MIN_PREFIX = 8
FATAL_CLASS_BY_TARGET = {"gravidade_3_classes": 2}
# Nome exato usado por scripts/seed_demo.py; presets como "Rápido (Demo)" não
# são protegidos, pois são runs comuns de teste.
DEMO_RUN_NAMES = {"demo — prf 2024"}


class RunLookupError(LookupError):
    """Id inexistente, ambíguo ou curto demais."""


@dataclass(frozen=True)
class RunInfo:
    id: uuid.UUID
    name: str
    status: str
    target: str
    created_at: datetime | None
    n_test: int | None
    metrics: dict[str, Any] | None

    @classmethod
    def from_row(cls, run: Any) -> RunInfo:
        return cls(
            id=uuid.UUID(str(run.id)),
            name=str(run.name),
            status=str(run.status),
            target=str(run.target),
            created_at=run.created_at,
            n_test=run.n_test,
            metrics=run.metrics,
        )


@dataclass
class DoctorReport:
    orphans: list[Path] = field(default_factory=list)
    invalid: list[Path] = field(default_factory=list)
    broken: list[uuid.UUID] = field(default_factory=list)
    healthy: int = 0

    @property
    def has_issues(self) -> bool:
        return bool(self.orphans or self.invalid or self.broken)


def normalize_prefix(prefix: str) -> str:
    value = prefix.strip().lower().replace("-", "")
    if len(value) < MIN_PREFIX:
        raise RunLookupError(f"informe ao menos {MIN_PREFIX} caracteres do id")
    if any(char not in "0123456789abcdef" for char in value):
        raise RunLookupError("o prefixo deve conter apenas caracteres hexadecimais")
    return value


def resolve_prefix(prefix: str, ids: Iterable[uuid.UUID]) -> uuid.UUID:
    """Resolve um prefixo para exatamente um id, ou levanta RunLookupError."""
    value = normalize_prefix(prefix)
    matches = [rid for rid in ids if str(rid).lower().replace("-", "").startswith(value)]
    if not matches:
        raise RunLookupError(f"nenhum run encontrado para o prefixo {prefix!r}")
    if len(matches) > 1:
        shown = ", ".join(str(rid)[:MIN_PREFIX] for rid in matches[:6])
        extra = "" if len(matches) <= 6 else f" e mais {len(matches) - 6}"
        raise RunLookupError(f"prefixo ambíguo ({len(matches)} runs): {shown}{extra}")
    return matches[0]


def is_demo_run(run: RunInfo) -> bool:
    return run.name.strip().casefold() in DEMO_RUN_NAMES


def _created_key(run: RunInfo) -> float:
    return run.created_at.timestamp() if run.created_at else 0.0


def select_prune_candidates(
    runs: Sequence[RunInfo],
    keep: int,
    statuses: set[str] | None = None,
    include_demo: bool = False,
) -> list[RunInfo]:
    """Mantém os ``keep`` mais recentes e devolve os demais elegíveis.

    Runs ativos nunca são selecionados; o run Demo é preservado por padrão.
    """
    if keep < 0:
        raise ValueError("--keep não pode ser negativo")
    ordered = sorted(runs, key=_created_key, reverse=True)
    kept = {run.id for run in ordered[:keep]}
    selected: list[RunInfo] = []
    for run in ordered:
        if run.id in kept or run.status in ACTIVE_STATUSES:
            continue
        if statuses is not None and run.status not in statuses:
            continue
        if not include_demo and is_demo_run(run):
            continue
        selected.append(run)
    return selected


def scan_artifacts(runs_dir: Path, known_ids: Iterable[uuid.UUID]) -> DoctorReport:
    """Compara os diretórios de artefatos com os ids registrados no banco."""
    known = set(known_ids)
    present: set[uuid.UUID] = set()
    report = DoctorReport()
    if runs_dir.is_dir():
        for entry in sorted(runs_dir.iterdir()):
            if not entry.is_dir():
                continue
            try:
                run_id = uuid.UUID(entry.name)
            except ValueError:
                report.invalid.append(entry)
                continue
            present.add(run_id)
            if run_id not in known:
                report.orphans.append(entry)
    report.broken = sorted(known - present, key=str)
    report.healthy = len(known & present)
    return report


def directory_size(path: Path) -> int:
    if not path.exists():
        return 0
    total = 0
    for item in path.rglob("*"):
        if item.is_file():
            try:
                total += item.stat().st_size
            except OSError:
                continue
    return total


def format_bytes(value: int) -> str:
    size = float(value)
    for unit in ("B", "KB", "MB", "GB"):
        if size < 1024 or unit == "GB":
            return f"{size:.0f} {unit}" if unit == "B" else f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} GB"


def fatal_f1(run: RunInfo) -> float | None:
    metrics = run.metrics or {}
    per_class = (metrics.get("precision_recall_f1") or {}).get("per_class") or []
    index = FATAL_CLASS_BY_TARGET.get(run.target, 1)
    for entry in per_class:
        if int(entry.get("class_index", -1)) == index:
            value = entry.get("f1")
            return float(value) if value is not None else None
    return None


def format_f1(value: float | None) -> str:
    return "—" if value is None else f"{value:.4f}".replace(".", ",")


def format_date(value: datetime | None) -> str:
    return value.strftime("%Y-%m-%d %H:%M") if value else "—"


def print_table(headers: Sequence[str], rows: Sequence[Sequence[str]]) -> None:
    widths = [len(header) for header in headers]
    for row in rows:
        for index, value in enumerate(row):
            widths[index] = max(widths[index], len(str(value)))
    line = "  ".join(header.ljust(widths[index]) for index, header in enumerate(headers))
    print(line)
    print("  ".join("-" * width for width in widths))
    for row in rows:
        print("  ".join(str(value).ljust(widths[index]) for index, value in enumerate(row)))


def fetch_runs(limit: int = 100_000) -> list[RunInfo]:
    with db.get_session_factory()() as session:
        return [RunInfo.from_row(run) for run in store.list_runs(session, limit=limit)]


def find_run(runs: Sequence[RunInfo], prefix: str) -> RunInfo:
    run_id = resolve_prefix(prefix, [run.id for run in runs])
    for run in runs:
        if run.id == run_id:
            return run
    raise RunLookupError(f"run {run_id} não encontrado")


def confirm(message: str, assume_yes: bool) -> bool:
    if assume_yes:
        return True
    if not sys.stdin.isatty():
        print("Operação não confirmada. Use --yes em modo não interativo.")
        return False
    answer = input(f"{message} [s/N] ").strip().casefold()
    return answer in {"s", "sim", "y", "yes"}


def cmd_list(args: argparse.Namespace) -> int:
    runs = fetch_runs()
    runs.sort(key=_created_key, reverse=True)
    runs = runs[: args.limit]
    if args.json:
        payload = [
            {
                "id": str(run.id),
                "name": run.name,
                "status": run.status,
                "target": run.target,
                "created_at": run.created_at.isoformat() if run.created_at else None,
                "n_test": run.n_test,
                "fatal_f1": fatal_f1(run),
                "size_bytes": directory_size(store.run_dir(run.id)),
            }
            for run in runs
        ]
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0

    if not runs:
        print("Nenhum run encontrado.")
        return 0

    rows = [
        [
            str(run.id)[:MIN_PREFIX],
            format_date(run.created_at),
            run.status,
            run.target,
            "—" if run.n_test is None else str(run.n_test),
            format_f1(fatal_f1(run)),
            format_bytes(directory_size(store.run_dir(run.id))),
        ]
        for run in runs
    ]
    print_table(
        ["ID", "CRIADO EM", "STATUS", "ALVO", "TESTE", "F1 FATAL", "DISCO"],
        rows,
    )
    print(f"\n{len(runs)} run(s) listado(s).")
    return 0


def cmd_delete(args: argparse.Namespace) -> int:
    runs = fetch_runs()
    run = find_run(runs, args.run_id)
    if run.status in ACTIVE_STATUSES:
        print(
            f"erro: o run {str(run.id)[:MIN_PREFIX]} está {run.status}; "
            "cancele antes de apagar.",
            file=sys.stderr,
        )
        return 1
    size = directory_size(store.run_dir(run.id))
    print(f"Run:    {run.name}")
    print(f"ID:     {run.id}")
    print(f"Status: {run.status}")
    print(f"Disco:  {format_bytes(size)}")
    if not confirm("Apagar este run do banco e do disco?", args.yes):
        print("Cancelado.")
        return 1
    with db.get_session_factory()() as session:
        store.delete_run(session, run.id)
    print(f"Run apagado. Espaço liberado: {format_bytes(size)}.")
    return 0


def cmd_prune(args: argparse.Namespace) -> int:
    statuses = (
        {value.strip() for value in args.status.split(",") if value.strip()}
        if args.status
        else None
    )
    runs = fetch_runs()
    candidates = select_prune_candidates(
        runs,
        keep=args.keep,
        statuses=statuses,
        include_demo=args.include_demo,
    )
    if not candidates:
        print("Nada para apagar com os filtros atuais.")
        return 0

    total = sum(directory_size(store.run_dir(run.id)) for run in candidates)
    rows = [
        [
            str(run.id)[:MIN_PREFIX],
            format_date(run.created_at),
            run.status,
            run.name[:36],
            format_bytes(directory_size(store.run_dir(run.id))),
        ]
        for run in candidates
    ]
    print_table(["ID", "CRIADO EM", "STATUS", "NOME", "DISCO"], rows)
    print(
        f"\n{len(candidates)} run(s) serão apagados; "
        f"{len(runs) - len(candidates)} preservado(s); total {format_bytes(total)}."
    )

    if args.dry_run:
        print("Modo --dry-run: nada foi apagado.")
        return 0

    if not confirm("Confirmar exclusão em lote?", args.yes):
        print("Cancelado.")
        return 1

    freed = 0
    failures = 0
    with db.get_session_factory()() as session:
        for run in candidates:
            size = directory_size(store.run_dir(run.id))
            if store.delete_run(session, run.id):
                freed += size
            else:
                failures += 1
                print(f"aviso: run {run.id} já não existia no banco.", file=sys.stderr)
    print(f"Concluído. {len(candidates) - failures} apagado(s), {format_bytes(freed)} liberados.")
    return 1 if failures else 0


def cmd_doctor(args: argparse.Namespace) -> int:
    runs = fetch_runs()
    runs_dir = ARTIFACTS_DIR / "runs"
    report = scan_artifacts(runs_dir, [run.id for run in runs])

    print(f"Diretório: {runs_dir}")
    print(f"Runs no banco: {len(runs)} · saudáveis: {report.healthy}")
    if not report.has_issues:
        print("Nenhum problema encontrado.")
        return 0

    if report.orphans:
        print(f"\nArtefatos órfãos (pasta sem linha no banco): {len(report.orphans)}")
        for path in report.orphans:
            print(f"  - {path.name} ({format_bytes(directory_size(path))})")
    if report.broken:
        print(f"\nRuns quebrados (linha no banco sem pasta): {len(report.broken)}")
        for run_id in report.broken:
            print(f"  - {run_id}")
    if report.invalid:
        print(f"\nDiretórios com nome inválido (ignorados): {len(report.invalid)}")
        for path in report.invalid:
            print(f"  - {path.name}")

    if not args.fix:
        print("\nUse --fix para remover órfãos e linhas quebradas.")
        return 0

    freed = 0
    removed_orphans = 0
    for path in report.orphans:
        size = directory_size(path)
        shutil.rmtree(path, ignore_errors=True)
        if not path.exists():
            freed += size
            removed_orphans += 1

    active = {run.id: run.status for run in runs}
    removed_broken = 0
    with db.get_session_factory()() as session:
        for run_id in report.broken:
            if active.get(run_id) in ACTIVE_STATUSES:
                print(f"aviso: {run_id} está ativo; não será removido.", file=sys.stderr)
                continue
            if store.delete_run(session, run_id):
                removed_broken += 1

    print(
        f"\nCorreção concluída: {removed_orphans} órfão(s), "
        f"{removed_broken} linha(s) quebrada(s), {format_bytes(freed)} liberados."
    )
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Lista, apaga e audita runs treinados (banco + artefatos)."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    list_parser = subparsers.add_parser("list", help="lista os runs")
    list_parser.add_argument("--limit", type=int, default=50, help="máximo de runs (padrão: 50)")
    list_parser.add_argument("--json", action="store_true", help="saída em JSON")
    list_parser.set_defaults(handler=cmd_list)

    delete_parser = subparsers.add_parser("delete", help="apaga um run pelo id ou prefixo")
    delete_parser.add_argument("run_id", help="id completo ou prefixo único (mín. 8 caracteres)")
    delete_parser.add_argument("--yes", action="store_true", help="não pedir confirmação")
    delete_parser.set_defaults(handler=cmd_delete)

    prune_parser = subparsers.add_parser("prune", help="apaga runs antigos mantendo os N recentes")
    prune_parser.add_argument("--keep", type=int, default=5, help="quantos runs manter (padrão: 5)")
    prune_parser.add_argument(
        "--status",
        default=None,
        help="lista de status separada por vírgula (ex.: failed,canceled)",
    )
    prune_parser.add_argument(
        "--include-demo",
        action="store_true",
        help="permite apagar o run Demo criado por `make seed`",
    )
    prune_parser.add_argument("--dry-run", action="store_true", help="apenas mostrar o plano")
    prune_parser.add_argument("--yes", action="store_true", help="não pedir confirmação")
    prune_parser.set_defaults(handler=cmd_prune)

    doctor_parser = subparsers.add_parser("doctor", help="compara banco e artefatos")
    doctor_parser.add_argument("--fix", action="store_true", help="remove órfãos e linhas quebradas")
    doctor_parser.set_defaults(handler=cmd_doctor)

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return int(args.handler(args))
    except RunLookupError as exc:
        print(f"erro: {exc}", file=sys.stderr)
        return 1
    except SQLAlchemyError as exc:
        print(
            "erro: não foi possível acessar o Postgres. "
            "Confira se a stack está no ar (make up) e a DATABASE_URL.",
            file=sys.stderr,
        )
        print(f"detalhe: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
