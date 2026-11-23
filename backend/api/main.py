"""API FastAPI: treino assíncrono, métricas, SSE e simulador."""

from __future__ import annotations

import asyncio
import json
import math
import os
import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from functools import lru_cache
from queue import Empty, Queue
from typing import Any

import numpy as np
from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from sqlalchemy import text
from sqlalchemy.orm import Session
from sse_starlette.sse import EventSourceResponse

from api import db, schemas, store, trainer
from api.models import Base
from nn.config import (
    CLASS_NAMES,
    GROUP_CATEGORICAL,
    GROUP_NUMERIC,
    GROUP_ORDER,
    GROUP_RAW_COLUMNS,
    PRESETS,
    TARGETS,
    DataConfig,
    ModelConfig,
    build_configs,
    estimate_seconds,
)
from nn.data import build_target, load_raw
from nn.export import predict_with_json

_sse_queues: dict[str, Queue[dict[str, Any]]] = {}
_sse_history: dict[str, list[dict[str, Any]]] = {}


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    if os.getenv("SKIP_DB_STARTUP") == "1":
        yield
        return
    try:
        db.wait_for_database(retries=5, delay=2.0)
        Base.metadata.create_all(bind=db.get_engine())
    except Exception as exc:  # pragma: no cover - ambiente sem Postgres
        print(f"[startup] banco indisponível: {exc}")
    yield


app = FastAPI(title="TDE Redes Neurais API", lifespan=lifespan)


@app.get("/api/health")
def health() -> dict[str, str]:
    database = "ok"
    try:
        with db.get_engine().connect() as connection:
            connection.execute(text("SELECT 1"))
    except Exception:  # pragma: no cover - ambiente sem Postgres
        database = "unavailable"
    return {"status": "ok" if database == "ok" else "degraded", "database": database}


@lru_cache(maxsize=1)
def _dataset_bundle() -> dict[str, Any]:
    raw = load_raw()
    categories: dict[str, list[str]] = {}
    for group in GROUP_ORDER:
        for column in GROUP_CATEGORICAL[group]:
            if column in raw.columns:
                values = raw[column].dropna().astype(str).unique().tolist()
                categories[column] = sorted(values)

    if "tracado_via" in raw.columns:
        principal = (
            raw["tracado_via"]
            .dropna()
            .astype(str)
            .str.split(";", n=1)
            .str[0]
            .str.strip()
        )
        categories["tracado_principal"] = sorted(
            value for value in principal.unique().tolist() if value
        )

    target_counts: dict[str, list[int]] = {}
    for target in TARGETS:
        labels = build_target(raw, target)
        target_counts[target] = np.bincount(
            labels, minlength=len(CLASS_NAMES[target])
        ).astype(int).tolist()

    return {
        "raw": raw,
        "categories": categories,
        "target_counts": target_counts,
    }


def _dataset_summary() -> dict[str, Any]:
    bundle = _dataset_bundle()
    raw = bundle["raw"]
    return {
        "rows": len(raw),
        "columns": int(raw.shape[1]),
        "targets": {
            target: {
                "class_names": list(CLASS_NAMES[target]),
                "counts": bundle["target_counts"][target],
            }
            for target in TARGETS
        },
        "missing": {
            column: int(count) for column, count in raw.isna().sum().items() if count > 0
        },
        "top_categories": {
            column: raw[column].value_counts().head(10).index.astype(str).tolist()
            for column in ("uf", "causa_acidente", "tipo_acidente", "tracado_via")
            if column in raw.columns
        },
    }


@app.get("/api/meta")
def meta() -> dict[str, Any]:
    bundle = _dataset_bundle()
    return {
        "feature_groups": list(GROUP_ORDER),
        "groups": {
            group: {
                "raw_columns": list(GROUP_RAW_COLUMNS[group]),
                "numeric": list(GROUP_NUMERIC[group]),
                "categorical": list(GROUP_CATEGORICAL[group]),
            }
            for group in GROUP_ORDER
        },
        "categories": bundle["categories"],
        "targets": list(TARGETS),
        "class_names": {target: list(names) for target, names in CLASS_NAMES.items()},
        "defaults": {
            "data": DataConfig().to_dict(),
            "model": ModelConfig().to_dict(),
        },
        "presets": PRESETS,
        "dataset": _dataset_summary(),
    }


@app.get("/api/datasets/summary")
def dataset_summary() -> dict[str, Any]:
    return _dataset_summary()


@app.post("/api/estimate")
def estimate(request: schemas.EstimateRequest) -> dict[str, Any]:
    try:
        data_cfg, model_cfg = build_configs(request.data, request.model)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    rows = data_cfg.max_rows or _dataset_summary()["rows"]
    n_train = max(1, int(rows * (1.0 - data_cfg.val_size - data_cfg.test_size)))
    n_features = 6 + 10 * len(data_cfg.feature_groups)
    seconds = estimate_seconds(n_train, n_features, data_cfg, model_cfg)
    steps = model_cfg.epochs * math.ceil(
        n_train / (model_cfg.batch_size or max(1, n_train))
    )
    warnings: list[str] = []
    if steps > 2_000_000:
        warnings.append("O número de passos excede o guardrail de 2.000.000.")
    if rows > 60_000 and model_cfg.epochs > 300:
        warnings.append("Treino longo para o dataset completo; considere um preset menor.")
    return {
        "seconds": seconds,
        "n_train": n_train,
        "n_features": n_features,
        "steps": steps,
        "warnings": warnings,
    }


@app.post("/api/runs", response_model=schemas.RunStatus)
async def create_run(
    run_in: schemas.RunCreate,
    background_tasks: BackgroundTasks,
    db_session: Session = Depends(db.get_db),  # noqa: B008
) -> schemas.RunStatus:
    try:
        data_cfg, model_cfg = build_configs(run_in.data, run_in.model)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    if sum(model_cfg.neurons) > 1024:
        raise HTTPException(status_code=422, detail="soma de neurônios excede 1024")
    rows = data_cfg.max_rows or _dataset_summary()["rows"]
    n_train = max(1, int(rows * (1.0 - data_cfg.val_size - data_cfg.test_size)))
    steps = model_cfg.epochs * math.ceil(
        n_train / (model_cfg.batch_size or max(1, n_train))
    )
    if steps > 2_000_000:
        raise HTTPException(status_code=422, detail="número de passos excede 2.000.000")

    run = store.create_run(db_session, run_in.name, data_cfg, model_cfg)
    run_key = uuid.UUID(str(run.id))
    queue: Queue[dict[str, Any]] = Queue()
    _sse_queues[str(run_key)] = queue
    _sse_history[str(run_key)] = []

    def publish(event: dict[str, Any]) -> None:
        _sse_history[str(run_key)].append(event)
        queue.put(event)

    background_tasks.add_task(
        trainer.run_trainer_worker,
        run_key,
        str(run.name),
        run_in.data,
        run_in.model,
        publish,
    )
    return schemas.RunStatus(
        run_id=run_key,
        name=str(run.name),
        status="queued",
        created_at=run.created_at.isoformat() if run.created_at else None,
    )


@app.get("/api/runs")
def list_runs(limit: int = Query(default=20, ge=1, le=100)) -> list[dict[str, Any]]:
    with db.get_session_factory()() as session:
        return [store.serialize_run(run) for run in store.list_runs(session, limit)]


@app.get("/api/runs/{run_id}")
def get_run(run_id: uuid.UUID) -> dict[str, Any]:
    with db.get_session_factory()() as session:
        run = store.get_run(session, run_id)
        if run is None:
            raise HTTPException(status_code=404, detail="run não encontrado")
        return store.serialize_run(run)


@app.post("/api/runs/{run_id}/cancel")
def cancel_run(run_id: uuid.UUID) -> dict[str, str]:
    with db.get_session_factory()() as session:
        run = store.get_run(session, run_id)
        if run is None:
            raise HTTPException(status_code=404, detail="run não encontrado")
        if run.status in {"done", "failed", "canceled"}:
            raise HTTPException(status_code=409, detail="run já finalizado")
        trainer.request_cancel(run_id)
    return {"status": "cancel_requested"}


@app.delete("/api/runs/{run_id}")
def delete_run(run_id: uuid.UUID) -> dict[str, str]:
    with db.get_session_factory()() as session:
        run = store.get_run(session, run_id)
        if run is None:
            raise HTTPException(status_code=404, detail="run não encontrado")
        if run.status in {"queued", "running"}:
            raise HTTPException(status_code=409, detail="cancele o run antes de apagar")
        store.delete_run(session, run_id)
    return {"status": "deleted"}


@app.get("/api/runs/{run_id}/export")
def export_run(
    run_id: uuid.UUID,
    format: str = Query(default="json", pattern="^(json|npz|manifest|curves|evaluation|preprocessor)$"),
) -> FileResponse:
    names = {
        "json": ("model.json", "application/json"),
        "npz": ("weights.npz", "application/octet-stream"),
        "manifest": ("run.json", "application/json"),
        "curves": ("curves.json", "application/json"),
        "evaluation": ("evaluation.json", "application/json"),
        "preprocessor": ("preprocessor.json", "application/json"),
    }
    filename, media_type = names[format]
    path = store.run_dir(run_id) / filename
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"artefato {filename} indisponível")
    return FileResponse(path, media_type=media_type, filename=filename)


async def _stream_events(run_id: str) -> AsyncIterator[dict[str, str]]:
    queue = _sse_queues.setdefault(run_id, Queue())
    history = _sse_history.setdefault(run_id, [])
    for past in list(history):
        yield {"data": json.dumps(past, ensure_ascii=False)}
        if past.get("type") in {"done", "failed", "canceled"}:
            return
    while True:
        try:
            event = await asyncio.to_thread(queue.get, True, 15.0)
        except Empty:
            yield {"event": "ping", "data": "{}"}
            continue
        yield {"data": json.dumps(event, ensure_ascii=False)}
        if event.get("type") in {"done", "failed", "canceled"}:
            break


@app.get("/api/runs/{run_id}/stream")
@app.get("/api/runs/{run_id}/events")
async def stream_run(run_id: uuid.UUID) -> EventSourceResponse:
    with db.get_session_factory()() as session:
        run = store.get_run(session, run_id)
        if run is None:
            raise HTTPException(status_code=404, detail="run não encontrado")
        status = run.status
    if status in {"done", "failed", "canceled"}:
        terminal = {"type": "done" if status == "done" else status, "status": status}
        _sse_queues.setdefault(str(run_id), Queue()).put(terminal)
    return EventSourceResponse(_stream_events(str(run_id)))


@app.post("/api/predict")
def predict(request: schemas.PredictRequest) -> dict[str, Any]:
    with db.get_session_factory()() as session:
        run = store.get_run(session, request.run_id)
        if run is None:
            raise HTTPException(status_code=404, detail="run não encontrado")
        if run.status != "done":
            raise HTTPException(status_code=409, detail="o run ainda não foi concluído")

    model_path = store.run_dir(request.run_id) / "model.json"
    if not model_path.exists():
        raise HTTPException(status_code=404, detail="model.json indisponível")
    model_json = json.loads(model_path.read_text(encoding="utf-8"))
    try:
        result = predict_with_json(model_json, request.features)
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"falha na predição: {exc}") from exc
    result["run_id"] = str(request.run_id)
    return result
