"""Exportação de modelos, manifestos de execução e inferência autocontida.

Módulos de exportação para servir o simulador da API e persistir artefatos:
- ``export_model``: gera o ``model.json`` autocontido com preprocessor e pesos
- ``export_npz``: salva os arrays dos pesos em formato compacto
- ``export_run_manifest``: manifesto completo com configs, status, métricas e timestamps
- ``predict_with_json``: realiza a inferência de uma única linha pura (dict) usando apenas o model.json
"""

from __future__ import annotations

import datetime
import json
from pathlib import Path
from typing import Any

import numpy as np

from nn.config import CLASS_NAMES, DataConfig, ModelConfig
from nn.data import Preprocessor, transform
from nn.model import NnModel

__all__ = [
    "export_model",
    "export_npz",
    "export_run_manifest",
    "predict_with_json",
]


def export_model(
    model: NnModel,
    prep: Preprocessor,
    model_cfg: ModelConfig,
    data_cfg: DataConfig,
    metrics: dict[str, Any] | None = None,
    path: str | Path | None = None,
) -> dict[str, Any]:
    """Exporta o modelo e seu pré-processador para um dicionário/JSON autocontido."""
    layers_data: list[dict[str, Any]] = []
    for i, (W, b) in enumerate(zip(model.weights, model.biases, strict=True)):
        layers_data.append(
            {
                "layer_index": i + 1,
                "shape": list(W.shape),
                "W": W.tolist(),
                "b": b.tolist(),
            }
        )

    export_payload: dict[str, Any] = {
        "schema_version": 1,
        "created_at": datetime.datetime.now(datetime.UTC).isoformat(),
        "target": data_cfg.target,
        "class_names": list(CLASS_NAMES[data_cfg.target]),
        "feature_names": list(prep.feature_names),
        "preprocessor": prep.to_dict(),
        "layers": layers_data,
        "activation": model_cfg.activation,
        "threshold": model_cfg.threshold,
        "metrics": metrics or {},
    }

    if path is not None:
        filepath = Path(path)
        filepath.parent.mkdir(parents=True, exist_ok=True)
        with filepath.open("w", encoding="utf-8") as f:
            json.dump(export_payload, f, ensure_ascii=False, indent=2)

    return export_payload


def export_npz(
    model: NnModel,
    path: str | Path,
) -> None:
    """Salva os pesos e biases do modelo em um arquivo compacto .npz."""
    model.save(path)


def export_run_manifest(
    run_id: str,
    name: str,
    status: str,
    data_cfg: DataConfig,
    model_cfg: ModelConfig,
    metrics: dict[str, Any] | None = None,
    duration_s: float = 0.0,
    n_train: int = 0,
    n_val: int = 0,
    n_test: int = 0,
    n_features: int = 0,
    best_epoch: int = 0,
    path: str | Path | None = None,
) -> dict[str, Any]:
    """Cria o manifesto run.json detalhando toda a execução."""
    manifest = {
        "run_id": run_id,
        "name": name,
        "status": status,
        "target": data_cfg.target,
        "config": {
            "data": data_cfg.to_dict(),
            "model": model_cfg.to_dict(),
        },
        "metrics": metrics or {},
        "duration_s": duration_s,
        "n_train": n_train,
        "n_val": n_val,
        "n_test": n_test,
        "n_features": n_features,
        "best_epoch": best_epoch,
        "exported_at": datetime.datetime.now(datetime.UTC).isoformat(),
    }

    if path is not None:
        filepath = Path(path)
        filepath.parent.mkdir(parents=True, exist_ok=True)
        with filepath.open("w", encoding="utf-8") as f:
            json.dump(manifest, f, ensure_ascii=False, indent=2)

    return manifest


def predict_with_json(
    model_json: dict[str, Any],
    raw_row: dict[str, Any],
) -> dict[str, Any]:
    """Realiza a inferência em tempo real para uma única amostra pura (dict).

    Usa exatamente os mesmos dados e pesos presentes no JSON do modelo, sem
    necessitar das classes originais carregadas em memória.
    """
    import pandas as pd

    from nn.data import feature_frame

    # Reconstrói a DataConfig com base no JSON exportado
    prep_data = model_json["preprocessor"]
    prep = Preprocessor.from_dict(prep_data)
    data_cfg = DataConfig(
        target=model_json["target"],
        scaler=prep.scaler,
        log1p_numeric=prep.log1p_numeric,
    )

    # Converte o dicionário raw em um DataFrame de uma linha
    df_single = pd.DataFrame([raw_row])
    # Aplica engenharia de features de forma pura
    feat_df = feature_frame(df_single, data_cfg)
    # Executa pré-processamento idêntico ao do treinamento
    X_mat = transform(feat_df, prep)

    # Forward pass usando os pesos do JSON
    activation_name = model_json["activation"]

    def act_fn(z: np.ndarray) -> np.ndarray:
        if activation_name == "relu":
            return np.maximum(0.0, z)
        if activation_name == "tanh":
            return np.tanh(z)
        if activation_name == "sigmoid":
            z_c = np.clip(z, -50.0, 50.0)
            return np.where(z_c >= 0, 1.0 / (1.0 + np.exp(-z_c)), np.exp(z_c) / (1.0 + np.exp(z_c)))
        if activation_name == "leaky_relu":
            return np.where(z > 0.0, z, 0.01 * z)
        raise ValueError(f"ativação desconhecida: {activation_name!r}")

    def softmax_fn(z: np.ndarray) -> np.ndarray:
        z_max = np.max(z, axis=-1, keepdims=True)
        exp_z = np.exp(z - z_max)
        return exp_z / np.sum(exp_z, axis=-1, keepdims=True)

    A = np.asarray(X_mat, dtype=np.float64)
    layers = model_json["layers"]
    num_layers = len(layers)

    for i, layer_info in enumerate(layers):
        W = np.asarray(layer_info["W"], dtype=np.float64)
        b = np.asarray(layer_info["b"], dtype=np.float64)
        Z = A @ W + b

        A = act_fn(Z) if i < num_layers - 1 else softmax_fn(Z)

    probs = A[0]
    class_names = model_json["class_names"]
    threshold = float(model_json.get("threshold", 0.5))

    pred_label_idx = int(probs[1] >= threshold) if len(class_names) == 2 else int(np.argmax(probs))

    predicted_class = class_names[pred_label_idx]

    probabilities_dict = {
        name: float(round(prob, 4))
        for name, prob in zip(class_names, probs, strict=True)
    }

    return {
        "predicted_class_index": pred_label_idx,
        "predicted_class": predicted_class,
        "probabilities": probabilities_dict,
        "threshold_used": threshold if len(class_names) == 2 else None,
    }
