"""Rede Neural Multi-Layer Perceptron (MLP) implementada do zero em NumPy.

Este módulo contém a classe ``NnModel``, as funções de ativação, inicializadores,
métodos de cálculo de loss, otimizadores e histórico de treino.

A API FastAPI importa este módulo para executar treinamentos e servir predições,
e o notebook do TDE exibe este código com ``inspect.getsource(NnModel)`` durante
a apresentação.
"""

from __future__ import annotations

import itertools
import json
import time
from collections.abc import Callable
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

import numpy as np

from nn.config import ModelConfig

__all__ = [
    "History",
    "NnModel",
]


# ---------------------------------------------------------------------------
# Estrutura do Histórico de Treino
# ---------------------------------------------------------------------------


@dataclass
class History:
    """Histórico de métricas coletadas ao fim de cada época."""

    epochs: list[int] = field(default_factory=list)
    loss_train: list[float] = field(default_factory=list)
    loss_val: list[float] = field(default_factory=list)
    acc_train: list[float] = field(default_factory=list)
    acc_val: list[float] = field(default_factory=list)
    f1_val: list[float] = field(default_factory=list)
    grad_norm: list[float] = field(default_factory=list)
    lr: list[float] = field(default_factory=list)
    seconds: list[float] = field(default_factory=list)
    best_epoch: int = 0
    stopped_early: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


# ---------------------------------------------------------------------------
# Funções de Ativação e Derivadas
# ---------------------------------------------------------------------------


def _relu(z: np.ndarray) -> np.ndarray:
    return np.maximum(0.0, z)


def _d_relu(z: np.ndarray) -> np.ndarray:
    return (z > 0.0).astype(np.float64)


def _tanh(z: np.ndarray) -> np.ndarray:
    return np.tanh(z)


def _d_tanh(a: np.ndarray) -> np.ndarray:
    return 1.0 - a**2


def _sigmoid(z: np.ndarray) -> np.ndarray:
    z_clipped = np.clip(z, -50.0, 50.0)
    return np.where(
        z_clipped >= 0,
        1.0 / (1.0 + np.exp(-z_clipped)),
        np.exp(z_clipped) / (1.0 + np.exp(z_clipped)),
    )


def _d_sigmoid(a: np.ndarray) -> np.ndarray:
    return a * (1.0 - a)


def _leaky_relu(z: np.ndarray, alpha: float = 0.01) -> np.ndarray:
    return np.where(z > 0.0, z, alpha * z)


def _d_leaky_relu(z: np.ndarray, alpha: float = 0.01) -> np.ndarray:
    return np.where(z > 0.0, 1.0, alpha)


def _softmax(z: np.ndarray) -> np.ndarray:
    """Softmax numericamente estável subtraindo o valor máximo da linha."""
    z_max = np.max(z, axis=-1, keepdims=True)
    exp_z = np.exp(z - z_max)
    return exp_z / np.sum(exp_z, axis=-1, keepdims=True)


def _init_weights(
    fan_in: int, fan_out: int, method: str, rng: np.random.Generator
) -> np.ndarray:
    """Inicialização de pesos He, Xavier ou Normal."""
    if method == "he":
        # He / Kaiming normal: std = sqrt(2 / fan_in) (recomendado para ReLU)
        std = np.sqrt(2.0 / fan_in)
        return rng.normal(0.0, std, size=(fan_in, fan_out)).astype(np.float64)
    if method == "xavier":
        # Xavier / Glorot normal: std = sqrt(1 / fan_in) (recomendado para tanh/sigmoid)
        std = np.sqrt(1.0 / fan_in)
        return rng.normal(0.0, std, size=(fan_in, fan_out)).astype(np.float64)
    if method == "normal":
        return rng.normal(0.0, 0.01, size=(fan_in, fan_out)).astype(np.float64)
    raise ValueError(f"método de inicialização desconhecido: {method!r}")


def _quick_f1_macro(y_true: np.ndarray, y_pred: np.ndarray, n_classes: int) -> float:
    """Métrica F1 Macro vetorizada em NumPy para acompanhamento de épocas."""
    f1s: list[float] = []
    for k in range(n_classes):
        tp = float(np.sum((y_true == k) & (y_pred == k)))
        fp = float(np.sum((y_true != k) & (y_pred == k)))
        fn = float(np.sum((y_true == k) & (y_pred != k)))
        denom = 2.0 * tp + fp + fn
        if denom > 0:
            f1s.append(2.0 * tp / denom)
        else:
            f1s.append(1.0 if tp == 0 and fp == 0 and fn == 0 else 0.0)
    return float(np.mean(f1s))


# ---------------------------------------------------------------------------
# Classe NnModel
# ---------------------------------------------------------------------------


class NnModel:
    """Rede Neural Multi-Layer Perceptron (MLP) totalmente em NumPy.

    Implementa forward pass com cache, derivadas analíticas em forma fechada,
    inverted dropout, L2 regularization, gradient clipping por norma global,
    e otimizadores SGD, Momentum, Adam e AdamW.
    """

    def __init__(
        self,
        n_inputs: int,
        n_outputs: int,
        cfg: ModelConfig | None = None,
        class_weights: np.ndarray | None = None,
    ) -> None:
        self.n_inputs = n_inputs
        self.n_outputs = n_outputs
        self.cfg = cfg if cfg is not None else ModelConfig()

        if class_weights is not None:
            weights_arr = np.asarray(class_weights, dtype=np.float64)
            if weights_arr.shape != (n_outputs,):
                raise ValueError(
                    f"class_weights deve ter formato ({n_outputs},); recebido {weights_arr.shape}"
                )
            self.class_weights = weights_arr
        else:
            self.class_weights = np.ones(n_outputs, dtype=np.float64)

        self.rng = np.random.default_rng(self.cfg.seed)
        self.weights: list[np.ndarray] = []
        self.biases: list[np.ndarray] = []

        # Define o tamanho de cada camada: [inputs, hidden_1, ..., hidden_L, outputs]
        layer_sizes = [n_inputs, *self.cfg.neurons, n_outputs]
        for l_in, l_out in itertools.pairwise(layer_sizes):
            W = _init_weights(l_in, l_out, self.cfg.init, self.rng)
            b = np.zeros((1, l_out), dtype=np.float64)
            self.weights.append(W)
            self.biases.append(b)

        # Estado do otimizador para Momentum / Adam / AdamW
        self._opt_m_w: list[np.ndarray] = [np.zeros_like(w) for w in self.weights]
        self._opt_v_w: list[np.ndarray] = [np.zeros_like(w) for w in self.weights]
        self._opt_m_b: list[np.ndarray] = [np.zeros_like(b) for b in self.biases]
        self._opt_v_b: list[np.ndarray] = [np.zeros_like(b) for b in self.biases]
        self._t: int = 0

        # Flag para solicitação de interrupção cooperativa
        self._stop_requested: bool = False

    def _activate(self, z: np.ndarray) -> np.ndarray:
        act = self.cfg.activation
        if act == "relu":
            return _relu(z)
        if act == "tanh":
            return _tanh(z)
        if act == "sigmoid":
            return _sigmoid(z)
        if act == "leaky_relu":
            return _leaky_relu(z)
        raise ValueError(f"ativação desconhecida: {act!r}")

    def forward(
        self, X: np.ndarray, training: bool = False
    ) -> tuple[np.ndarray, list[dict[str, np.ndarray]]]:
        """Executa o forward pass através de todas as camadas.

        Retorna (probs, cache) onde cache guarda as entradas, ativações e
        máscaras de dropout por camada.
        """
        A = np.asarray(X, dtype=np.float64)
        cache: list[dict[str, np.ndarray]] = []
        L = len(self.weights)

        for i in range(L):
            W = self.weights[i]
            b = self.biases[i]
            Z = A @ W + b

            if i < L - 1:
                # Camada oculta com ativação configurada
                A_next = self._activate(Z)
                mask = np.ones_like(A_next)
                if training and self.cfg.dropout > 0.0:
                    keep_prob = 1.0 - self.cfg.dropout
                    mask = (
                        (self.rng.random(A_next.shape) < keep_prob).astype(np.float64)
                        / keep_prob
                    )
                    A_next = A_next * mask
                cache.append({"A_prev": A, "Z": Z, "A": A_next, "mask": mask})
                A = A_next
            else:
                # Camada de saída com Softmax
                A_next = _softmax(Z)
                cache.append({"A_prev": A, "Z": Z, "A": A_next})
                A = A_next

        return A, cache

    def loss(self, probs: np.ndarray, y: np.ndarray) -> tuple[float, np.ndarray]:
        """Calcula a loss escalar e o gradiente das logits em forma fechada.

        Suporta 'ce', 'weighted_ce' e 'focal'.
        Retorna (scalar_loss, dZ_L).
        """
        N = len(y)
        if N == 0:
            return 0.0, np.zeros_like(probs)

        probs_clip = np.clip(probs, 1e-15, 1.0 - 1e-15)
        y_arr = np.asarray(y, dtype=np.int64)

        Y = np.zeros_like(probs_clip)
        Y[np.arange(N), y_arr] = 1.0

        sample_weights = self.class_weights[y_arr]
        p_true = probs_clip[np.arange(N), y_arr]

        weight_sum = float(np.sum(sample_weights))
        if weight_sum <= 0:
            weight_sum = float(N)

        if self.cfg.loss == "ce":
            sample_losses = -np.log(p_true)
            scalar_loss = float(np.mean(sample_losses))
            dZ_L = (probs_clip - Y) / N

        elif self.cfg.loss == "weighted_ce":
            sample_losses = -sample_weights * np.log(p_true)
            scalar_loss = float(np.sum(sample_losses) / weight_sum)
            w_col = (sample_weights / weight_sum)[:, np.newaxis]
            dZ_L = w_col * (probs_clip - Y)

        elif self.cfg.loss == "focal":
            gamma = self.cfg.focal_gamma
            focal_factor = (1.0 - p_true) ** gamma
            sample_losses = -sample_weights * focal_factor * np.log(p_true)
            scalar_loss = float(np.sum(sample_losses) / weight_sum)

            # Gradiente fechado da Focal Loss w.r.t logits Z:
            term = (1.0 - p_true) - gamma * p_true * np.log(p_true)
            factor_i = sample_weights * ((1.0 - p_true) ** (gamma - 1.0)) * term
            factor_col = (factor_i / weight_sum)[:, np.newaxis]
            dZ_L = factor_col * (probs_clip - Y)

        else:
            raise ValueError(f"loss desconhecida: {self.cfg.loss!r}")

        # L2 Regularization adicionada à loss (exceto para AdamW que desacopla o weight decay)
        if self.cfg.l2 > 0.0 and self.cfg.optimizer != "adamw":
            l2_sum = sum(float(np.sum(w**2)) for w in self.weights)
            scalar_loss += 0.5 * self.cfg.l2 * l2_sum

        return scalar_loss, dZ_L

    def backward(
        self,
        dZ_L_or_cache: np.ndarray | list[dict[str, np.ndarray]],
        cache_or_y: list[dict[str, np.ndarray]] | np.ndarray | None = None,
    ) -> dict[str, np.ndarray]:
        """Passagem para trás (backpropagation) por regra da cadeia.

        Aceita tanto ``backward(dZ_L, cache)`` quanto ``backward(cache, y)``.
        Retorna dicionário de gradientes dW1, db1, dW2, db2, ...
        """
        if isinstance(dZ_L_or_cache, list):
            cache = dZ_L_or_cache
            y = np.asarray(cache_or_y, dtype=np.int64)
            probs = cache[-1]["A"]
            _, dZ_L = self.loss(probs, y)
        else:
            dZ_L = np.asarray(dZ_L_or_cache, dtype=np.float64)
            if not isinstance(cache_or_y, list):
                raise ValueError("cache deve ser uma lista de dicionários")
            cache = cache_or_y

        grads: dict[str, np.ndarray] = {}
        L = len(self.weights)
        dZ = dZ_L

        for i in reversed(range(L)):
            layer_idx = i + 1
            A_prev = cache[i]["A_prev"]
            W = self.weights[i]

            dW = A_prev.T @ dZ
            db = np.sum(dZ, axis=0, keepdims=True)

            if self.cfg.l2 > 0.0 and self.cfg.optimizer != "adamw":
                dW = dW + self.cfg.l2 * W

            grads[f"dW{layer_idx}"] = dW
            grads[f"db{layer_idx}"] = db

            if i > 0:
                dA_prev = dZ @ W.T
                mask = cache[i - 1].get("mask", None)
                if mask is not None:
                    dA_prev = dA_prev * mask

                Z_prev = cache[i - 1]["Z"]
                A_prev_val = cache[i - 1]["A"]
                act = self.cfg.activation

                if act == "relu":
                    dZ_prev = dA_prev * _d_relu(Z_prev)
                elif act == "tanh":
                    dZ_prev = dA_prev * _d_tanh(A_prev_val)
                elif act == "sigmoid":
                    dZ_prev = dA_prev * _d_sigmoid(A_prev_val)
                elif act == "leaky_relu":
                    dZ_prev = dA_prev * _d_leaky_relu(Z_prev)
                else:
                    raise ValueError(f"ativação desconhecida: {act!r}")

                dZ = dZ_prev

        return grads

    def _compute_grad_norm(self, grads: dict[str, np.ndarray]) -> float:
        total_sq = sum(float(np.sum(g**2)) for g in grads.values())
        return float(np.sqrt(total_sq))

    def step(self, grads: dict[str, np.ndarray], lr: float | None = None) -> float:
        """Aplica gradient clipping por norma global e atualiza os parâmetros.

        Retorna a norma escalar dos gradientes antes do clipping.
        """
        current_lr = lr if lr is not None else self.cfg.lr
        grad_norm = self._compute_grad_norm(grads)

        # Gradient clipping por norma global
        clipped_grads = grads
        if self.cfg.grad_clip > 0.0 and grad_norm > self.cfg.grad_clip:
            scale = self.cfg.grad_clip / (grad_norm + 1e-8)
            clipped_grads = {k: v * scale for k, v in grads.items()}

        self._t += 1
        t = self._t
        opt = self.cfg.optimizer
        L = len(self.weights)

        for i in range(L):
            layer_idx = i + 1
            dW = clipped_grads[f"dW{layer_idx}"]
            db = clipped_grads[f"db{layer_idx}"]
            W = self.weights[i]
            b = self.biases[i]

            if opt == "sgd":
                W -= current_lr * dW
                b -= current_lr * db

            elif opt == "momentum":
                beta = 0.9
                self._opt_m_w[i] = beta * self._opt_m_w[i] + dW
                self._opt_m_b[i] = beta * self._opt_m_b[i] + db
                W -= current_lr * self._opt_m_w[i]
                b -= current_lr * self._opt_m_b[i]

            elif opt in ("adam", "adamw"):
                b1, b2, eps = 0.9, 0.999, 1e-8
                if opt == "adamw" and self.cfg.l2 > 0.0:
                    W -= current_lr * self.cfg.l2 * W

                self._opt_m_w[i] = b1 * self._opt_m_w[i] + (1.0 - b1) * dW
                self._opt_m_b[i] = b1 * self._opt_m_b[i] + (1.0 - b1) * db
                self._opt_v_w[i] = b2 * self._opt_v_w[i] + (1.0 - b2) * (dW**2)
                self._opt_v_b[i] = b2 * self._opt_v_b[i] + (1.0 - b2) * (db**2)

                m_w_hat = self._opt_m_w[i] / (1.0 - b1**t)
                m_b_hat = self._opt_m_b[i] / (1.0 - b1**t)
                v_w_hat = self._opt_v_w[i] / (1.0 - b2**t)
                v_b_hat = self._opt_v_b[i] / (1.0 - b2**t)

                W -= current_lr * m_w_hat / (np.sqrt(v_w_hat) + eps)
                b -= current_lr * m_b_hat / (np.sqrt(v_b_hat) + eps)

        return grad_norm

    def _compute_lr(self, epoch_idx: int) -> float:
        lr_0 = self.cfg.lr
        decay = self.cfg.lr_decay
        if decay == "none":
            return lr_0
        if decay == "step":
            steps = epoch_idx // self.cfg.decay_every
            return lr_0 * (self.cfg.decay_rate**steps)
        if decay == "cosine":
            T_max = max(1, self.cfg.epochs)
            lr_min = 1e-6
            return lr_min + 0.5 * (lr_0 - lr_min) * (
                1.0 + np.cos(np.pi * epoch_idx / T_max)
            )
        return lr_0

    def stop(self) -> None:
        """Solicita interrupção cooperativa do treinamento."""
        self._stop_requested = True

    def fit(
        self,
        X_train: np.ndarray,
        y_train: np.ndarray,
        X_val: np.ndarray,
        y_val: np.ndarray,
        on_epoch: Callable[[dict[str, Any]], None] | None = None,
    ) -> History:
        """Executa o treinamento da MLP com minibatches, early stopping e callbacks.

        Retorna o histórico com métricas detalhadas por época.
        """
        self._stop_requested = False
        t_start = time.time()

        history = History()
        best_val_loss = float("inf")
        best_epoch = 0
        best_weights = [w.copy() for w in self.weights]
        best_biases = [b.copy() for b in self.biases]
        patience_counter = 0

        N_train = len(y_train)
        if N_train == 0:
            raise ValueError("y_train não pode ser vazio")

        batch_size = (
            self.cfg.batch_size if self.cfg.batch_size is not None else N_train
        )
        batch_size = min(max(1, batch_size), N_train)

        epoch_rng = np.random.default_rng(self.cfg.seed)

        for epoch in range(1, self.cfg.epochs + 1):
            if self._stop_requested:
                history.stopped_early = True
                break

            current_lr = self._compute_lr(epoch - 1)
            indices = epoch_rng.permutation(N_train)
            last_grad_norm = 0.0

            for start_idx in range(0, N_train, batch_size):
                batch_idx = indices[start_idx : start_idx + batch_size]
                X_batch = X_train[batch_idx]
                y_batch = y_train[batch_idx]

                probs_batch, cache = self.forward(X_batch, training=True)
                _, dZ_L = self.loss(probs_batch, y_batch)
                grads = self.backward(dZ_L, cache)
                last_grad_norm = self.step(grads, lr=current_lr)

            # Métricas do fim da época
            probs_tr, _ = self.forward(X_train, training=False)
            loss_tr, _ = self.loss(probs_tr, y_train)
            preds_tr = self.predict(X_train, threshold=self.cfg.threshold)
            acc_tr = float(np.mean(preds_tr == y_train))

            probs_v, _ = self.forward(X_val, training=False)
            loss_v, _ = self.loss(probs_v, y_val)
            preds_v = self.predict(X_val, threshold=self.cfg.threshold)
            acc_v = float(np.mean(preds_v == y_val))
            f1_v = _quick_f1_macro(y_val, preds_v, self.n_outputs)

            elapsed = float(round(time.time() - t_start, 3))

            history.epochs.append(epoch)
            history.loss_train.append(float(loss_tr))
            history.loss_val.append(float(loss_v))
            history.acc_train.append(acc_tr)
            history.acc_val.append(acc_v)
            history.f1_val.append(f1_v)
            history.grad_norm.append(float(last_grad_norm))
            history.lr.append(float(current_lr))
            history.seconds.append(elapsed)

            # Early stopping por loss de validação
            if loss_v < best_val_loss - 1e-7:
                best_val_loss = float(loss_v)
                best_epoch = epoch
                best_weights = [w.copy() for w in self.weights]
                best_biases = [b.copy() for b in self.biases]
                patience_counter = 0
            else:
                patience_counter += 1

            history.best_epoch = best_epoch

            if on_epoch is not None:
                event = {
                    "epoch": epoch,
                    "epochs": self.cfg.epochs,
                    "loss_train": float(loss_tr),
                    "loss_val": float(loss_v),
                    "acc_train": acc_tr,
                    "acc_val": acc_v,
                    "f1_val": f1_v,
                    "grad_norm": float(last_grad_norm),
                    "lr": float(current_lr),
                    "seconds": elapsed,
                    "best_epoch": best_epoch,
                }
                on_epoch(event)

            if self.cfg.patience > 0 and patience_counter >= self.cfg.patience:
                history.stopped_early = True
                break

        # Restaura o melhor ponto verificado na validação
        self.weights = best_weights
        self.biases = best_biases
        return history

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        """Retorna as probabilidades calculadas pelo modelo (N, n_outputs)."""
        probs, _ = self.forward(X, training=False)
        return probs

    def predict(self, X: np.ndarray, threshold: float | None = None) -> np.ndarray:
        """Retorna os rótulos de classe previstos.

        Para 2 saídas (binário), usa a probabilidade da classe 1 com o threshold.
        Para > 2 saídas (multiclasse), escolhe a classe de maior probabilidade (argmax).
        """
        probs = self.predict_proba(X)
        if self.n_outputs == 2:
            thresh = threshold if threshold is not None else self.cfg.threshold
            return (probs[:, 1] >= thresh).astype(np.int64)
        return np.argmax(probs, axis=-1).astype(np.int64)

    def save(self, path: str | Path) -> None:
        """Salva a configuração e os pesos em um arquivo .npz."""
        filepath = Path(path)
        filepath.parent.mkdir(parents=True, exist_ok=True)
        config_json = json.dumps(self.cfg.to_dict())
        weights_dict = {f"W_{i}": w for i, w in enumerate(self.weights)}
        biases_dict = {f"b_{i}": b for i, b in enumerate(self.biases)}
        arrays: dict[str, Any] = {
            "config_json": config_json,
            "n_inputs": self.n_inputs,
            "n_outputs": self.n_outputs,
            "class_weights": self.class_weights,
        }
        arrays.update(weights_dict)
        arrays.update(biases_dict)
        np.savez(filepath, **arrays)

    @classmethod
    def load(cls, path: str | Path) -> NnModel:
        """Carrega uma instância de NnModel salva em .npz."""
        filepath = Path(path)
        if not filepath.exists():
            raise FileNotFoundError(f"modelo não encontrado em {filepath}")
        with np.load(filepath) as archive:
            config_dict = json.loads(str(archive["config_json"]))
            cfg = ModelConfig.from_dict(config_dict)
            n_inputs = int(archive["n_inputs"])
            n_outputs = int(archive["n_outputs"])
            class_weights = archive["class_weights"]

            model = cls(n_inputs, n_outputs, cfg, class_weights=class_weights)
            model.weights = [archive[f"W_{i}"] for i in range(len(model.weights))]
            model.biases = [archive[f"b_{i}"] for i in range(len(model.biases))]
            return model
