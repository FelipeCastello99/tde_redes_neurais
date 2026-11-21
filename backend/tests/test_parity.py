from __future__ import annotations

import tempfile
from pathlib import Path

import numpy as np
from test_data import synthetic_raw

from nn.config import DataConfig, ModelConfig
from nn.data import fit_preprocessor, transform
from nn.export import export_model, export_npz, export_run_manifest, predict_with_json
from nn.model import NnModel


def test_export_and_single_row_prediction_parity() -> None:
    """Verifica paridade exata de predição entre NumPy em lote e predict_with_json."""
    raw_df = synthetic_raw(100)
    data_cfg = DataConfig(target="fatal_binario", rare_min_count=5)
    model_cfg = ModelConfig(hidden_layers=1, neurons=(16,), activation="relu", seed=42)

    # Prepara features e treina modelo rápido
    from nn.data import build_target, feature_frame

    feats = feature_frame(raw_df, data_cfg)
    y = build_target(raw_df, data_cfg.target)
    prep = fit_preprocessor(feats, data_cfg)
    X = transform(feats, prep)

    model = NnModel(n_inputs=X.shape[1], n_outputs=2, cfg=model_cfg)
    # Roda apenas 5 épocas para ajustar pesos
    model.fit(X, y, X, y)

    # Predição direta no modelo NumPy
    numpy_probs = model.predict_proba(X)
    numpy_preds = model.predict(X, threshold=model_cfg.threshold)

    # Exporta para JSON
    with tempfile.TemporaryDirectory() as tmpdir:
        json_path = Path(tmpdir) / "model.json"
        npz_path = Path(tmpdir) / "weights.npz"
        manifest_path = Path(tmpdir) / "run.json"

        model_json = export_model(model, prep, model_cfg, data_cfg, path=json_path)
        export_npz(model, npz_path)
        manifest = export_run_manifest(
            run_id="test-run-123",
            name="Run Teste",
            status="done",
            data_cfg=data_cfg,
            model_cfg=model_cfg,
            path=manifest_path,
        )

        assert json_path.exists()
        assert npz_path.exists()
        assert manifest_path.exists()
        assert manifest["run_id"] == "test-run-123"

        # Compara a predição linha por linha em 100 amostras
        for i in range(100):
            raw_row = raw_df.iloc[i].to_dict()
            json_pred = predict_with_json(model_json, raw_row)

            # Classe predita deve ser idêntica
            assert json_pred["predicted_class_index"] == numpy_preds[i]

            # Probabilidades devem bater até a 4ª casa decimal
            p_class_1 = json_pred["probabilities"]["vitima_fatal"]
            np.testing.assert_allclose(p_class_1, numpy_probs[i, 1], atol=1e-3)


def test_export_multiclass_prediction_parity() -> None:
    """Verifica paridade de predição para classificação em 3 classes."""
    from nn.data import target_mask

    raw_all = synthetic_raw(60)
    # Descarta linhas com target NaN simuladas para o teste do mask
    raw_df = raw_all.loc[target_mask(raw_all, "gravidade_3_classes")].reset_index(drop=True)

    data_cfg = DataConfig(target="gravidade_3_classes", rare_min_count=5)
    model_cfg = ModelConfig(hidden_layers=1, neurons=(12,), activation="tanh", seed=42)

    from nn.data import build_target, feature_frame

    feats = feature_frame(raw_df, data_cfg)
    y = build_target(raw_df, data_cfg.target)
    prep = fit_preprocessor(feats, data_cfg)
    X = transform(feats, prep)

    model = NnModel(n_inputs=X.shape[1], n_outputs=3, cfg=model_cfg)
    model.fit(X, y, X, y)

    numpy_preds = model.predict(X)
    model_json = export_model(model, prep, model_cfg, data_cfg)

    for i in range(30):
        raw_row = raw_df.iloc[i].to_dict()
        json_pred = predict_with_json(model_json, raw_row)

        assert json_pred["predicted_class_index"] == numpy_preds[i]
        assert json_pred["predicted_class"] in model_json["class_names"]
