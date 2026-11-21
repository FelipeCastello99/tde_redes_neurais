"""Repositório de runs e artefatos em disco."""

from __future__ import annotations

import shutil
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from api.models import Run, RunEpoch
from nn.utils import ARTIFACTS_DIR

# Garante que o diretório exista em desenvolvimento e em testes.
ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)


def run_dir(run_id: uuid.UUID | str) -> Path:
    return ARTIFACTS_DIR / "runs" / str(run_id)


def get_run(db: Session, run_id: uuid.UUID | str) -> Run | None:
    return db.query(Run).filter(Run.id == uuid.UUID(str(run_id))).first()


def create_run(
    db: Session,
    name: str,
    data_cfg: Any,
    model_cfg: Any,
) -> Run:
    run = Run(
        id=uuid.uuid4(),
        name=name,
        status="queued",
        target=data_cfg.target,
        config={
            "data": data_cfg.to_dict(),
            "model": model_cfg.to_dict(),
        },
    )
    db.add(run)
    db.commit()
    db.refresh(run)

    run_dir(str(run.id)).mkdir(parents=True, exist_ok=True)
    return run


def update_run_status(
    db: Session,
    run_id: uuid.UUID | str,
    status: str,
    error: str | None = None,
) -> None:
    run = get_run(db, run_id)
    if run is None:
        return
    run.status = status  # type: ignore[assignment]
    if error is not None:
        run.error = error  # type: ignore[assignment]
    if status == "running":
        run.started_at = datetime.now(UTC)  # type: ignore[assignment]
    if status in {"done", "failed", "canceled"}:
        run.finished_at = datetime.now(UTC)  # type: ignore[assignment]
    db.commit()


def save_epochs(db: Session, run_id: uuid.UUID | str, events: list[dict[str, Any]]) -> None:
    if not events:
        return
    db.add_all(
        [
            RunEpoch(
                run_id=uuid.UUID(str(run_id)),
                epoch=int(event["epoch"]),
                loss_train=float(event["loss_train"]),
                loss_val=float(event["loss_val"]),
                acc_train=float(event["acc_train"]),
                acc_val=float(event["acc_val"]),
                f1_val=float(event["f1_val"]),
                lr=float(event["lr"]),
                grad_norm=float(event["grad_norm"]),
                seconds=float(event["seconds"]),
            )
            for event in events
        ]
    )
    db.commit()


def save_epoch(db: Session, run_id: uuid.UUID | str, event: dict[str, Any]) -> None:
    save_epochs(db, run_id, [event])


def finish_run(
    db: Session,
    run_id: uuid.UUID | str,
    *,
    metrics: dict[str, Any],
    duration_s: float,
    n_train: int,
    n_val: int,
    n_test: int,
    n_features: int,
    best_epoch: int,
) -> None:
    run = get_run(db, run_id)
    if run is None:
        return
    run.status = "done"  # type: ignore[assignment]
    run.metrics = metrics  # type: ignore[assignment]
    run.duration_s = float(duration_s)  # type: ignore[assignment]
    run.n_train = int(n_train)  # type: ignore[assignment]
    run.n_val = int(n_val)  # type: ignore[assignment]
    run.n_test = int(n_test)  # type: ignore[assignment]
    run.n_features = int(n_features)  # type: ignore[assignment]
    run.best_epoch = int(best_epoch)  # type: ignore[assignment]
    run.finished_at = datetime.now(UTC)  # type: ignore[assignment]
    db.commit()


def list_runs(db: Session, limit: int = 20) -> list[Run]:
    return db.query(Run).order_by(Run.created_at.desc()).limit(limit).all()


def delete_run(db: Session, run_id: uuid.UUID | str) -> bool:
    run = get_run(db, run_id)
    if run is None:
        return False
    db.delete(run)
    db.commit()
    shutil.rmtree(run_dir(run_id), ignore_errors=True)
    return True


def _iso(value: Any) -> str | None:
    return value.isoformat() if value is not None else None


def serialize_run(run: Run, *, include_metrics: bool = True) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "id": str(run.id),
        "run_id": str(run.id),
        "name": run.name,
        "status": run.status,
        "target": run.target,
        "config": run.config,
        "n_features": run.n_features,
        "n_train": run.n_train,
        "n_val": run.n_val,
        "n_test": run.n_test,
        "best_epoch": run.best_epoch,
        "duration_s": run.duration_s,
        "created_at": _iso(run.created_at),
        "started_at": _iso(run.started_at),
        "finished_at": _iso(run.finished_at),
        "error": run.error,
    }
    if include_metrics:
        payload["metrics"] = run.metrics
    return payload
