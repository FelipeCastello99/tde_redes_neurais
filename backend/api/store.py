import os
import uuid
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from api.models import Run, RunEpoch
from nn.config import DataConfig, ModelConfig

ARTIFACTS_DIR = Path(os.getenv("ARTIFACTS_DIR", "backend/artifacts"))

def create_run(db: Session, name: str, data_cfg: DataConfig, model_cfg: ModelConfig) -> Run:
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
    
    # Cria diretório de artefatos
    run_dir = ARTIFACTS_DIR / "runs" / str(run.id)
    run_dir.mkdir(parents=True, exist_ok=True)
    return run

def update_run_status(db: Session, run_id: uuid.UUID, status: str, error: str | None = None) -> None:
    run = db.query(Run).filter(Run.id == run_id).first()
    if run:
        run.status = status  # type: ignore
        if error:
            run.error = error  # type: ignore
        db.commit()

def save_epoch(db: Session, run_id: uuid.UUID, epoch_data: dict[str, Any]) -> None:
    epoch = RunEpoch(
        run_id=run_id,
        epoch=int(epoch_data["epoch"]),
        loss_train=float(epoch_data["loss_train"]),
        loss_val=float(epoch_data["loss_val"]),
        acc_train=float(epoch_data["acc_train"]),
        acc_val=float(epoch_data["acc_val"]),
        f1_val=float(epoch_data["f1_val"]),
        lr=float(epoch_data["lr"]),
        grad_norm=float(epoch_data["grad_norm"]),
        seconds=float(epoch_data["seconds"]),
    )
    db.add(epoch)
    db.commit()
