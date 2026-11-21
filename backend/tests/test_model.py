from __future__ import annotations

import tempfile
from pathlib import Path

import numpy as np
import pytest

from nn.config import (
    ModelConfig,
    build_configs,
    estimate_seconds,
)
from nn.model import NnModel, _softmax


def test_model_config_validations() -> None:
    cfg = ModelConfig()
    assert cfg.hidden_layers == 2
    assert cfg.neurons == (64, 32)

    with pytest.raises(ValueError, match="hidden_layers"):
        ModelConfig(hidden_layers=5, neurons=(64, 32, 16, 8, 4))

    with pytest.raises(ValueError, match=r"len\(neurons\)"):
        ModelConfig(hidden_layers=3, neurons=(64, 32))

    with pytest.raises(ValueError, match="dropout"):
        ModelConfig(dropout=0.8)

    with pytest.raises(ValueError, match="activation"):
        ModelConfig(activation="invalid_act")


def test_presets_and_build_configs() -> None:
    data_cfg, model_cfg = build_configs(preset="rapido")
    assert data_cfg.max_rows == 20000
    assert model_cfg.hidden_layers == 1
    assert model_cfg.neurons == (32,)
    assert model_cfg.batch_size is None

    _data_cfg_p, model_cfg_p = build_configs(preset="profundo")
    assert model_cfg_p.hidden_layers == 3
    assert model_cfg_p.neurons == (128, 64, 32)
    assert model_cfg_p.optimizer == "adamw"

    with pytest.raises(ValueError, match="preset"):
        build_configs(preset="inexistente")


def test_estimate_seconds() -> None:
    data_cfg, model_cfg = build_configs(preset="rapido")
    sec = estimate_seconds(20000, 100, data_cfg, model_cfg)
    assert sec > 0.0


def test_softmax_stability() -> None:
    # Softmax com logits extremos +1000 e -1000 não deve estourar para NaN ou inf
    extreme_logits = np.array([[1000.0, -1000.0, 0.0], [-1000.0, 1000.0, 100.0]])
    probs = _softmax(extreme_logits)

    assert np.isfinite(probs).all()
    assert not np.isnan(probs).any()
    np.testing.assert_allclose(probs.sum(axis=-1), [1.0, 1.0])
    assert probs[0, 0] > 0.999
    assert probs[0, 1] < 1e-10


def test_model_initializations() -> None:
    for init in ("he", "xavier", "normal"):
        cfg = ModelConfig(init=init)
        model = NnModel(n_inputs=10, n_outputs=2, cfg=cfg)
        assert len(model.weights) == 3  # 10->64, 64->32, 32->2
        assert model.weights[0].shape == (10, 64)
        assert model.weights[1].shape == (64, 32)
        assert model.weights[2].shape == (32, 2)
        assert float(np.std(model.weights[0])) > 0.0


def test_dropout_behavior() -> None:
    cfg = ModelConfig(dropout=0.5, seed=42)
    model = NnModel(n_inputs=10, n_outputs=2, cfg=cfg)
    X = np.ones((100, 10))

    # Em modo treino, dropout inativa ~50% dos neurônios (com reescala / 0.5)
    _, cache_tr = model.forward(X, training=True)
    mask = cache_tr[0]["mask"]
    zero_fraction = float(np.mean(mask == 0.0))
    assert 0.3 < zero_fraction < 0.7

    # Em modo eval, dropout fica desligado (todas as máscaras valem 1.0)
    _, cache_eval = model.forward(X, training=False)
    mask_eval = cache_eval[0]["mask"]
    assert np.all(mask_eval == 1.0)


@pytest.mark.parametrize("activation", ["relu", "tanh", "sigmoid", "leaky_relu"])
@pytest.mark.parametrize("loss_type", ["ce", "weighted_ce", "focal"])
def test_numerical_gradient_check(activation: str, loss_type: str) -> None:
    """Valida a precisão dos gradientes analíticos via diferenças finitas."""
    cfg = ModelConfig(
        hidden_layers=2,
        neurons=(8, 6),
        activation=activation,
        init="he",
        dropout=0.0,
        l2=0.0,
        loss=loss_type,
        focal_gamma=2.0 if loss_type == "focal" else 0.0,
        seed=42,
    )
    model = NnModel(n_inputs=5, n_outputs=3, cfg=cfg)

    rng = np.random.default_rng(42)
    X = rng.normal(0, 1, size=(10, 5))
    y = rng.choice([0, 1, 2], size=10)

    probs, cache = model.forward(X, training=False)
    _, dZ_L = model.loss(probs, y)
    analytical_grads = model.backward(dZ_L, cache)

    eps = 1e-6
    for layer_idx, W in enumerate(model.weights, start=1):
        dW_analytical = analytical_grads[f"dW{layer_idx}"]
        dW_numerical = np.zeros_like(W)

        # Checa gradiente elemento por elemento nos pesos W
        for i in range(W.shape[0]):
            for j in range(W.shape[1]):
                orig = W[i, j]

                W[i, j] = orig + eps
                probs_plus, _ = model.forward(X, training=False)
                loss_plus, _ = model.loss(probs_plus, y)

                W[i, j] = orig - eps
                probs_minus, _ = model.forward(X, training=False)
                loss_minus, _ = model.loss(probs_minus, y)

                W[i, j] = orig
                dW_numerical[i, j] = (loss_plus - loss_minus) / (2 * eps)

        diff = np.abs(dW_analytical - dW_numerical)
        denom = np.maximum(1e-5, np.abs(dW_analytical) + np.abs(dW_numerical))
        rel_error = np.max(diff / denom)

        assert rel_error < 1e-4, (
            f"Falha no gradiente para {activation}/{loss_type} na camada {layer_idx}: "
            f"erro relativo {rel_error:.2e}"
        )


@pytest.mark.parametrize("optimizer", ["sgd", "momentum", "adam", "adamw"])
def test_xor_convergence(optimizer: str) -> None:
    """Verifica se a MLP aprende a função lógica XOR (problema não-linear clássico)."""
    X_xor = np.array([[0.0, 0.0], [0.0, 1.0], [1.0, 0.0], [1.0, 1.0]])
    y_xor = np.array([0, 1, 1, 0])

    lr = 0.2 if optimizer == "sgd" else (0.1 if optimizer == "momentum" else 0.05)
    cfg = ModelConfig(
        hidden_layers=1,
        neurons=(8,),
        activation="tanh",
        init="xavier",
        dropout=0.0,
        l2=0.0,
        loss="ce",
        optimizer=optimizer,
        lr=lr,
        batch_size=None,
        epochs=500,
        patience=0,
        seed=42,
    )
    model = NnModel(n_inputs=2, n_outputs=2, cfg=cfg)

    history = model.fit(X_xor, y_xor, X_xor, y_xor)
    final_loss = history.loss_train[-1]
    preds = model.predict(X_xor)

    assert final_loss < 0.05, f"Otimizador {optimizer} falhou em convergir no XOR: loss={final_loss:.4f}"
    np.testing.assert_array_equal(preds, y_xor)


def test_reproducibility() -> None:
    """Dois modelos com a mesma semente devem gerar pesos e métricas idênticos."""
    rng = np.random.default_rng(123)
    X = rng.normal(0, 1, size=(50, 8))
    y = rng.choice([0, 1], size=50)

    cfg = ModelConfig(seed=42, epochs=20, batch_size=16)

    m1 = NnModel(n_inputs=8, n_outputs=2, cfg=cfg)
    h1 = m1.fit(X, y, X, y)

    m2 = NnModel(n_inputs=8, n_outputs=2, cfg=cfg)
    h2 = m2.fit(X, y, X, y)

    np.testing.assert_array_equal(h1.loss_train, h2.loss_train)
    np.testing.assert_array_equal(h1.loss_val, h2.loss_val)

    for w1, w2 in zip(m1.weights, m2.weights, strict=True):
        np.testing.assert_array_equal(w1, w2)


def test_early_stopping_restores_best_checkpoint() -> None:
    """Early stopping deve interromper o treino e restaurar o melhor peso da validação."""
    rng = np.random.default_rng(42)
    X_tr = rng.normal(0, 1, size=(100, 5))
    y_tr = rng.choice([0, 1], size=100)

    # Conjunto de validação difícil que causará overfitting na loss
    X_v = rng.normal(5, 1, size=(50, 5))
    y_v = rng.choice([0, 1], size=50)

    cfg = ModelConfig(epochs=100, patience=5, lr=0.01, seed=42)
    model = NnModel(n_inputs=5, n_outputs=2, cfg=cfg)

    history = model.fit(X_tr, y_tr, X_v, y_v)

    assert history.stopped_early
    assert len(history.epochs) < 100
    assert history.best_epoch > 0
    assert history.best_epoch <= len(history.epochs)

    # Verifica que a loss de validação no best_epoch é <= à da última época
    best_loss = history.loss_val[history.best_epoch - 1]
    assert best_loss <= history.loss_val[-1] + 1e-6


def test_cooperative_cancellation() -> None:
    """Verifica se a chamada de stop() cancela o treinamento no loop."""
    rng = np.random.default_rng(42)
    X = rng.normal(0, 1, size=(100, 5))
    y = rng.choice([0, 1], size=100)

    cfg = ModelConfig(epochs=100, patience=0)
    model = NnModel(n_inputs=5, n_outputs=2, cfg=cfg)

    def cancel_on_epoch(event: dict) -> None:
        if event["epoch"] == 5:
            model.stop()

    history = model.fit(X, y, X, y, on_epoch=cancel_on_epoch)
    assert history.stopped_early
    assert len(history.epochs) == 5


def test_predict_and_thresholds() -> None:
    rng = np.random.default_rng(42)
    X = rng.normal(0, 1, size=(20, 4))

    # Binary classification
    m_bin = NnModel(n_inputs=4, n_outputs=2, cfg=ModelConfig(threshold=0.7))
    probs_bin = m_bin.predict_proba(X)
    preds_default = m_bin.predict(X)
    preds_low_thresh = m_bin.predict(X, threshold=0.1)

    np.testing.assert_array_equal(preds_default, probs_bin[:, 1] >= 0.7)
    np.testing.assert_array_equal(preds_low_thresh, probs_bin[:, 1] >= 0.1)

    # Multiclass classification
    m_multi = NnModel(n_inputs=4, n_outputs=3, cfg=ModelConfig())
    probs_multi = m_multi.predict_proba(X)
    preds_multi = m_multi.predict(X)

    np.testing.assert_array_equal(preds_multi, np.argmax(probs_multi, axis=1))


def test_save_and_load_round_trip() -> None:
    cfg = ModelConfig(hidden_layers=2, neurons=(16, 8), activation="tanh", seed=42)
    model = NnModel(n_inputs=10, n_outputs=3, cfg=cfg)

    X = np.random.default_rng(42).normal(0, 1, size=(15, 10))
    orig_probs = model.predict_proba(X)

    with tempfile.TemporaryDirectory() as tmpdir:
        save_path = Path(tmpdir) / "model_test.npz"
        model.save(save_path)

        loaded_model = NnModel.load(save_path)
        loaded_probs = loaded_model.predict_proba(X)

        assert loaded_model.cfg.hidden_layers == cfg.hidden_layers
        assert loaded_model.cfg.neurons == cfg.neurons
        assert loaded_model.cfg.activation == cfg.activation
        np.testing.assert_allclose(loaded_probs, orig_probs, atol=1e-12)
