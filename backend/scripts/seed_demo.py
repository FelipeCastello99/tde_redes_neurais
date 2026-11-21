#!/usr/bin/env python3
"""Cria um run "Demo" completo para a apresentação.

Treina uma rede pequena no dataset real (subconjunto estratificado), grava os
artefatos em ``backend/artifacts/runs/<id>/`` e registra o run no Postgres.

Uso:
    make seed
    # ou: cd backend && python scripts/seed_demo.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

# Permite executar como script sem instalar o pacote.
BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from api import db, store  # noqa: E402
from api.models import Base, Run  # noqa: E402
from nn.config import DataConfig, ModelConfig  # noqa: E402
from nn.data import prepare_dataset  # noqa: E402
from nn.export import export_model, export_npz, export_run_manifest  # noqa: E402
from nn.metrics import calculate_all_metrics  # noqa: E402
from nn.model import NnModel  # noqa: E402

DEMO_NAME = "Demo — PRF 2024"


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, default=float),
        encoding="utf-8",
    )


def main() -> int:
    db.wait_for_database(retries=5, delay=2.0)
    Base.metadata.create_all(bind=db.get_engine())

    data_cfg = DataConfig(max_rows=3000, target="fatal_binario", seed=42)
    model_cfg = ModelConfig(
        hidden_layers=1,
        neurons=(24,),
        activation="relu",
        optimizer="adam",
        lr=1e-3,
        epochs=15,
        batch_size=256,
        patience=5,
        seed=42,
    )

    with db.get_session_factory()() as session:
        existing = session.query(Run).filter(Run.name == DEMO_NAME).first()
        if existing is not None:
            print(f"Demo já existe: {existing.id}")
            return 0

        print("Preparando dataset…")
        dataset = prepare_dataset(data_cfg)
        print(
            f"Treino: {dataset.X_train.shape} | val: {dataset.X_val.shape} "
            f"| teste: {dataset.X_test.shape}"
        )

        model = NnModel(
            n_inputs=dataset.input_dim,
            n_outputs=dataset.n_classes,
            cfg=model_cfg,
            class_weights=dataset.class_weights,
        )
        print("Treinando modelo de demonstração…")
        history = model.fit(
            dataset.X_train,
            dataset.y_train,
            dataset.X_val,
            dataset.y_val,
        )

        probabilities = model.predict_proba(dataset.X_test)
        metrics = calculate_all_metrics(
            dataset.y_test,
            probabilities,
            threshold=model_cfg.threshold,
            n_classes=dataset.n_classes,
        )

        run = store.create_run(session, DEMO_NAME, data_cfg, model_cfg)
        run_path = store.run_dir(run.id)

        store.save_epochs(
            session,
            run.id,
            [
                {
                    "epoch": epoch,
                    "loss_train": loss_train,
                    "loss_val": loss_val,
                    "acc_train": acc_train,
                    "acc_val": acc_val,
                    "f1_val": f1_val,
                    "grad_norm": grad_norm,
                    "lr": lr,
                    "seconds": seconds,
                }
                for epoch, loss_train, loss_val, acc_train, acc_val, f1_val, grad_norm, lr, seconds in zip(
                    history.epochs,
                    history.loss_train,
                    history.loss_val,
                    history.acc_train,
                    history.acc_val,
                    history.f1_val,
                    history.grad_norm,
                    history.lr,
                    history.seconds,
                    strict=True,
                )
            ],
        )

        duration = history.seconds[-1] if history.seconds else 0.0
        _write_json(run_path / "curves.json", history.to_dict())
        _write_json(run_path / "evaluation.json", metrics)
        _write_json(run_path / "preprocessor.json", dataset.preprocessor.to_dict())
        (run_path / "log.txt").write_text(
            "\n".join(
                f"epoch={epoch:04d} loss_train={loss:.6f} loss_val={val:.6f}"
                for epoch, loss, val in zip(
                    history.epochs,
                    history.loss_train,
                    history.loss_val,
                    strict=True,
                )
            )
            + "\n",
            encoding="utf-8",
        )
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
            str(run.id),
            DEMO_NAME,
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
            run.id,
            metrics=metrics,
            duration_s=duration,
            n_train=len(dataset.y_train),
            n_val=len(dataset.y_val),
            n_test=len(dataset.y_test),
            n_features=dataset.input_dim,
            best_epoch=history.best_epoch,
        )

        print(f"Demo criado: {run.id}")
        print(f"Artefatos: {run_path}")
        print(f"Abra: http://localhost:3000/resultados/{run.id}")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
