"""Teste de integração real da API (requer Postgres de teste).

Execução:
    TEST_DATABASE_URL=postgresql+psycopg://tde:tde@localhost:55432/tde \\
        pytest tests/test_api_integration.py -q
"""

from __future__ import annotations

import json
import os
import time

import pytest

TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL")
if TEST_DATABASE_URL:
    os.environ["DATABASE_URL"] = TEST_DATABASE_URL

pytestmark = pytest.mark.skipif(
    not TEST_DATABASE_URL,
    reason="defina TEST_DATABASE_URL para rodar a integração com Postgres",
)

if TEST_DATABASE_URL:
    from fastapi.testclient import TestClient

    from api import store
    from api.main import app


def test_run_lifecycle_with_sse(tmp_path) -> None:  # type: ignore[no-untyped-def]
    if not TEST_DATABASE_URL:
        pytest.skip("sem Postgres de teste")
    store.ARTIFACTS_DIR = tmp_path

    payload = {
        "name": "Integração SSE",
        "data": {"max_rows": 150, "target": "fatal_binario", "seed": 42},
        "model": {
            "hidden_layers": 1,
            "neurons": [8],
            "epochs": 2,
            "batch_size": None,
            "patience": 0,
            "seed": 42,
        },
    }

    with TestClient(app) as client:
        response = client.post("/api/runs", json=payload)
        assert response.status_code == 200, response.text
        run_id = response.json()["run_id"]

        events: list[dict] = []
        with client.stream("GET", f"/api/runs/{run_id}/stream") as stream:
            for line in stream.iter_lines():
                if not line.startswith("data:"):
                    continue
                events.append(json.loads(line[5:].strip()))
                if events[-1].get("type") in {"done", "failed", "canceled"}:
                    break

        assert any(event.get("type") == "epoch" for event in events)
        assert any(event.get("type") == "done" for event in events)

        detail = client.get(f"/api/runs/{run_id}")
        assert detail.status_code == 200
        assert detail.json()["status"] == "done"
        assert detail.json()["metrics"]["accuracy"] >= 0

        prediction = client.post(
            "/api/predict",
            json={
                "run_id": run_id,
                "features": {
                    "uf": "SP",
                    "br": 101,
                    "km": 10.0,
                    "dia_semana": "segunda-feira",
                    "horario": "10:00:00",
                    "tipo_pista": "Simples",
                    "tracado_via": "Reta",
                    "uso_solo": "Não",
                    "sentido_via": "Crescente",
                    "causa_acidente": "Ultrapassagem Indevida",
                    "tipo_acidente": "Colisão frontal",
                    "fase_dia": "Pleno dia",
                    "condicao_metereologica": "Céu Claro",
                    "veiculos": 2,
                },
            },
        )
        assert prediction.status_code == 200, prediction.text
        assert "probabilities" in prediction.json()
        assert "contributions" in prediction.json()

        export = client.get(f"/api/runs/{run_id}/export?format=json")
        assert export.status_code == 200
        assert export.headers["content-type"].startswith("application/json")

        # Pequena pausa para o BackgroundTasks finalizar antes da limpeza.
        for _ in range(50):
            if client.get(f"/api/runs/{run_id}").json()["status"] == "done":
                break
            time.sleep(0.1)
        assert client.delete(f"/api/runs/{run_id}").status_code == 200
