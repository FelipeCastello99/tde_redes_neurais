from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient

os.environ.setdefault("SKIP_DB_STARTUP", "1")

from api.main import app
from nn.utils import DATA_DIR

client = TestClient(app)
RAW_PATH = DATA_DIR / "datatran2024.csv"


@pytest.fixture(autouse=True)
def _require_dataset() -> None:
    if not RAW_PATH.exists():
        pytest.skip("CSV do DATATRAN ausente; rode `make fetch`")


def test_meta_contract() -> None:
    response = client.get("/api/meta")
    assert response.status_code == 200
    payload = response.json()
    assert "feature_groups" in payload
    assert "categories" in payload
    assert payload["targets"] == ["fatal_binario", "gravidade_3_classes"]
    assert "uf" in payload["categories"]
    assert "tracado_principal" in payload["categories"]
    assert "Curva" in payload["categories"]["tracado_principal"]
    assert payload["defaults"]["data"]["target"] == "fatal_binario"


def test_dataset_summary() -> None:
    response = client.get("/api/datasets/summary")
    assert response.status_code == 200
    payload = response.json()
    assert payload["rows"] == 73_201
    assert payload["columns"] == 30
    assert payload["targets"]["fatal_binario"]["counts"] == [67_976, 5_225]
    assert payload["targets"]["gravidade_3_classes"]["counts"] == [11_782, 56_194, 5_225]


def test_estimate_defaults() -> None:
    response = client.post("/api/estimate", json={"data": {}, "model": {}})
    assert response.status_code == 200
    payload = response.json()
    assert payload["seconds"] > 0
    assert payload["n_train"] > 0
    assert payload["n_features"] > 0


def test_estimate_rejects_invalid_target() -> None:
    response = client.post(
        "/api/estimate",
        json={"data": {"target": "invalido"}, "model": {}},
    )
    assert response.status_code == 422


def test_openapi_exposes_core_routes() -> None:
    response = client.get("/openapi.json")
    assert response.status_code == 200
    paths = response.json()["paths"]
    for path in (
        "/api/meta",
        "/api/estimate",
        "/api/runs",
        "/api/runs/{run_id}",
        "/api/runs/{run_id}/stream",
        "/api/runs/{run_id}/cancel",
        "/api/runs/{run_id}/export",
        "/api/predict",
        "/api/datasets/summary",
    ):
        assert path in paths
