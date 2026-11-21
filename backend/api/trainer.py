"""Worker de treino: um único treino ativo por processo."""

from __future__ import annotations

import json
import threading
import uuid
from collections.abc import Callable
from functools import lru_cache
from typing import Any

from api import db, store
from nn.config import DataConfig, ModelConfig
from nn.data import Dataset, prepare_dataset
from nn.export import export_model, export_npz, export_run_manifest
from nn.metrics import calculate_all_metrics
from nn.model import NnModel

# Um treino por vez; os demais ficam "queued" aguardando o lock.
_training_lock = threading.Lock()
CANCEL_REQUESTS: set[uuid.UUID] = set()


@lru_cache(maxsize=3)
def _prepare_cached(cfg: DataConfig) -> Dataset:
    return prepare_dataset(cfg)


def request_cancel(run_id: uuid.UUID | str) -> None:
    CANCEL_REQUESTS.add(uuid.UUID(str(run_id)))


def _write_json(path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, default=float),
        encoding="utf-8",
    )


def run_trainer_worker(
    run_id: uuid.UUID,
    name: str,
    data_raw: dict[str, Any],
    model_raw: dict[str, Any],
    publish: Callable[[dict[str, Any]], None],
) -> None:
    """Executa o pipeline completo em uma thread do BackgroundTasks."""
    session = db.get_session_factory()()
    run_key = uuid.UUID(str(run_id))
    try:
        data_cfg = DataConfig.from_dict(data_raw)
        model_cfg = ModelConfig.from_dict(model_raw)

        with _training_lock:
            if run_key in CANCEL_REQUESTS:
                store.update_run_status(session, run_key, "canceled")
                publish({"type": "canceled", "status": "canceled", "run_id": str(run_key)})
                return

            store.update_run_status(session, run_key, "running")
            publish({"type": "status", "status": "running", "run_id": str(run_key)})

            dataset = _prepare_cached(data_cfg)
            model = NnModel(
                n_inputs=dataset.input_dim,
                n_outputs=dataset.n_classes,
                cfg=model_cfg,
                class_weights=dataset.class_weights,
            )

            buffer: list[dict[str, Any]] = []
            log_lines: list[str] = []

            def on_epoch(event: dict[str, Any]) -> None:
                if run_key in CANCEL_REQUESTS:
                    model.stop()
                log_lines.append(
                    f"epoch={event['epoch']:04d} "
                    f"loss_train={event['loss_train']:.6f} "
                    f"loss_val={event['loss_val']:.6f} "
                    f"f1_val={event['f1_val']:.6f} "
                    f"lr={event['lr']:.6g} "
                    f"seconds={event['seconds']:.3f}"
                )
                buffer.append(event)
                if len(buffer) >= 10:
                    store.save_epochs(session, run_key, buffer)
                    buffer.clear()
                publish({"type": "epoch", **event})

            history = model.fit(
                dataset.X_train,
                dataset.y_train,
                dataset.X_val,
                dataset.y_val,
                on_epoch=on_epoch,
            )
            if buffer:
                store.save_epochs(session, run_key, buffer)

            run_path = store.run_dir(run_key)
            (run_path / "log.txt").write_text(
                "\n".join(log_lines) + ("\n" if log_lines else ""),
                encoding="utf-8",
            )
            _write_json(run_path / "curves.json", history.to_dict())
            _write_json(run_path / "preprocessor.json", dataset.preprocessor.to_dict())

            duration = history.seconds[-1] if history.seconds else 0.0
            canceled = run_key in CANCEL_REQUESTS

            if canceled:
                store.update_run_status(session, run_key, "canceled")
                publish({"type": "canceled", "status": "canceled", "run_id": str(run_key)})
                return

            probabilities = model.predict_proba(dataset.X_test)
            metrics = calculate_all_metrics(
                dataset.y_test,
                probabilities,
                threshold=model_cfg.threshold,
                n_classes=dataset.n_classes,
            )
            _write_json(run_path / "evaluation.json", metrics)

            export_model(
                model,
                dataset.preprocessor,
                model_cfg,
                data_cfg,
                metrics,
                path=run_path / "model.json",
            )
            export_npz(model, run_path / "weights.npz")
            export_run_manifest(
                str(run_key),
                name,
                "done",
                data_cfg,
                model_cfg,
                metrics,
                duration_s=duration,
                n_train=len(dataset.y_train),
                n_val=len(dataset.y_val),
                n_test=len(dataset.y_test),
                n_features=dataset.input_dim,
                best_epoch=history.best_epoch,
                path=run_path / "run.json",
            )

            store.finish_run(
                session,
                run_key,
                metrics=metrics,
                duration_s=duration,
                n_train=len(dataset.y_train),
                n_val=len(dataset.y_val),
                n_test=len(dataset.y_test),
                n_features=dataset.input_dim,
                best_epoch=history.best_epoch,
            )
            publish(
                {
                    "type": "done",
                    "status": "done",
                    "run_id": str(run_key),
                    "best_epoch": history.best_epoch,
                    "seconds": duration,
                }
            )

    except Exception as exc:  # pragma: no cover - depende de dados/ambiente
        store.update_run_status(session, run_key, "failed", error=str(exc))
        publish(
            {
                "type": "failed",
                "status": "failed",
                "run_id": str(run_key),
                "error": str(exc),
            }
        )
    finally:
        CANCEL_REQUESTS.discard(run_key)
        session.close()
