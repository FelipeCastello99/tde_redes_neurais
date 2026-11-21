import asyncio
import json
import uuid
from typing import Any, Callable
from fastapi import FastAPI, BackgroundTasks, Depends, HTTPException, Request
from sse_starlette.sse import EventSourceResponse
from sqlalchemy.orm import Session
from api import db, store, schemas, trainer
from nn.config import build_configs

app = FastAPI(title="TDE Redes Neurais API")

# Fila para eventos de progresso SSE
_sse_queues: dict[str, asyncio.Queue[dict[str, Any]]] = {}

@app.get("/api/health")
def health():
    return {"status": "ok", "db": "ok"}

@app.post("/api/runs", response_model=schemas.RunStatus)
async def create_run(
    run_in: schemas.RunCreate,
    background_tasks: BackgroundTasks,
    db_session: Session = Depends(db.get_db),
):
    try:
        data_cfg, model_cfg = build_configs(run_in.data, run_in.model)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

    run = store.create_run(db_session, run_in.name, data_cfg, model_cfg)
    run_id_str = str(run.id)
    _sse_queues[run_id_str] = asyncio.Queue()

    def on_epoch(event: dict[str, Any]):
        # Salva no DB
        db_s = next(db.get_db())
        # Garante o tipo UUID para o store
        store.save_epoch(db_s, uuid.UUID(str(run.id)), event)
        db_s.close()
        # Envia SSE
        _sse_queues[run_id_str].put_nowait(event)

    background_tasks.add_task(
        trainer.run_trainer_worker,
        uuid.UUID(str(run.id)), str(run.name), run_in.data, run_in.model, on_epoch
    )
    
    return {"run_id": run.id, "name": run.name, "status": "queued", "created_at": str(run.created_at)}

@app.get("/api/runs/{run_id}/stream")
async def stream_run(run_id: str):
    if run_id not in _sse_queues:
        raise HTTPException(status_code=404, detail="Run não encontrado ou não está rodando")
    
    async def event_generator():
        queue = _sse_queues[run_id]
        while True:
            event = await queue.get()
            yield {"data": json.dumps(event)}
            if event.get("epoch") == event.get("epochs"):
                break
    
    return EventSourceResponse(event_generator())
