import asyncio
import uuid
from typing import Any, Callable
from sqlalchemy.orm import Session
from api import store, db
from nn.config import DataConfig, ModelConfig
from nn.data import prepare_dataset
from nn.model import NnModel
from nn.export import export_model, export_npz, export_run_manifest

# Fila simples de treino em memória (fila de 1)
# Para produção, usaríamos Celery ou RabbitMQ, mas para o TDE um worker dedicado basta.
_active_run_id: uuid.UUID | None = None
_run_lock = asyncio.Lock()

async def run_trainer_worker(
    run_id: uuid.UUID,
    name: str,
    data_raw: dict[str, Any],
    model_raw: dict[str, Any],
    on_epoch: Callable[[dict[str, Any]], None],
):
    """Worker assíncrono que executa o treinamento."""
    global _active_run_id
    
    session = next(db.get_db())
    try:
        data_cfg = DataConfig.from_dict(data_raw)
        model_cfg = ModelConfig.from_dict(model_raw)
        
        # 1. Pipeline de dados
        dataset = prepare_dataset(cfg=data_cfg)
        
        # 2. Inicializa modelo
        model = NnModel(
            n_inputs=dataset.input_dim,
            n_outputs=dataset.n_classes,
            cfg=model_cfg,
            class_weights=dataset.class_weights
        )
        
        store.update_run_status(session, run_id, "running")
        
        # 3. Treino
        history = model.fit(
            dataset.X_train, dataset.y_train,
            dataset.X_val, dataset.y_val,
            on_epoch=on_epoch
        )
        
        # 4. Avaliação e Exportação
        from nn.metrics import calculate_all_metrics
        probs = model.predict_proba(dataset.X_test)
        metrics = calculate_all_metrics(dataset.y_test, probs, n_classes=dataset.n_classes)
        
        # Salva artefatos
        run_dir = store.ARTIFACTS_DIR / "runs" / str(run_id)
        export_model(model, dataset.preprocessor, model_cfg, data_cfg, metrics, path=run_dir/"model.json")
        export_npz(model, run_dir / "weights.npz")
        export_run_manifest(
            str(run_id), name, "done", data_cfg, model_cfg, metrics,
            duration_s=history.seconds[-1],
            n_train=len(dataset.y_train), n_val=len(dataset.y_val), n_test=len(dataset.y_test),
            n_features=dataset.input_dim, best_epoch=history.best_epoch,
            path=run_dir / "run.json"
        )
        
        store.update_run_status(session, run_id, "done")
        
    except Exception as e:
        store.update_run_status(session, run_id, "failed", error=str(e))
        raise
    finally:
        session.close()
        _active_run_id = None
