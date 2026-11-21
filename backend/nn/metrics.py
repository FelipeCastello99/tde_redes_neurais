"""Métricas de avaliação e calibração de modelos implementadas em NumPy puro.

Sem dependência de scikit-learn em tempo de execução:
- Matriz de confusão (KxK)
- Acurácia, Precisão, Recall, F1 (por classe, macro e ponderado)
- ROC-AUC via estatística de Mann-Whitney (U de Wilcoxon) e one-vs-rest
- PR-AUC via aproximação trapezoidal
- Log-loss (entropia cruzada multiclasse/binária)
- Brier Score multiclasse
- Expected Calibration Error (ECE) com particionamento em bins
- Varredura de limiares (threshold sweep)
- Histograma de predições calibradas
"""

from __future__ import annotations

from typing import Any

import numpy as np

__all__ = [
    "accuracy",
    "brier_score",
    "calculate_all_metrics",
    "confusion_matrix",
    "expected_calibration_error",
    "log_loss",
    "pr_auc",
    "precision_recall_f1",
    "prediction_histogram",
    "roc_auc",
    "threshold_sweep",
]


def confusion_matrix(
    y_true: np.ndarray, y_pred: np.ndarray, n_classes: int | None = None
) -> np.ndarray:
    """Calcula a matriz de confusão K x K onde linhas=real e colunas=previsto."""
    y_t = np.asarray(y_true, dtype=np.int64)
    y_p = np.asarray(y_pred, dtype=np.int64)
    if y_t.shape != y_p.shape or y_t.ndim != 1:
        raise ValueError("y_true e y_pred devem ser vetores 1D de mesmo tamanho")

    k = (
        n_classes
        if n_classes is not None
        else max(int(np.max(y_t, initial=0)), int(np.max(y_p, initial=0))) + 1
    )
    if k <= 0:
        return np.zeros((0, 0), dtype=np.int64)

    # Vetoriza o binning via K * real + previsto
    cm = np.bincount(k * y_t + y_p, minlength=k * k).reshape((k, k))
    return cm.astype(np.int64)


def accuracy(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    """Acurácia global."""
    y_t = np.asarray(y_true, dtype=np.int64)
    y_p = np.asarray(y_pred, dtype=np.int64)
    if len(y_t) == 0:
        return 0.0
    return float(np.mean(y_t == y_p))


def precision_recall_f1(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    n_classes: int | None = None,
) -> dict[str, Any]:
    """Calcula Precisão, Recall e F1 por classe, além de médias Macro e Weighted."""
    cm = confusion_matrix(y_true, y_pred, n_classes=n_classes)
    k = cm.shape[0]
    if k == 0:
        return {
            "per_class": [],
            "macro": {"precision": 0.0, "recall": 0.0, "f1": 0.0},
            "weighted": {"precision": 0.0, "recall": 0.0, "f1": 0.0},
        }

    tp = np.diag(cm).astype(np.float64)
    fp = np.sum(cm, axis=0).astype(np.float64) - tp
    fn = np.sum(cm, axis=1).astype(np.float64) - tp
    support = np.sum(cm, axis=1).astype(np.float64)
    total_support = float(np.sum(support))

    precision = np.zeros(k, dtype=np.float64)
    recall = np.zeros(k, dtype=np.float64)
    f1 = np.zeros(k, dtype=np.float64)

    for i in range(k):
        # Precisão = TP / (TP + FP)
        p_denom = tp[i] + fp[i]
        precision[i] = tp[i] / p_denom if p_denom > 0 else 0.0

        # Recall = TP / (TP + FN)
        r_denom = tp[i] + fn[i]
        recall[i] = tp[i] / r_denom if r_denom > 0 else 0.0

        # F1 = 2 * (P * R) / (P + R) = 2*TP / (2*TP + FP + FN)
        f_denom = 2 * tp[i] + fp[i] + fn[i]
        f1[i] = (2 * tp[i]) / f_denom if f_denom > 0 else 0.0

    macro_p = float(np.mean(precision))
    macro_r = float(np.mean(recall))
    macro_f1 = float(np.mean(f1))

    if total_support > 0:
        weighted_p = float(np.sum(precision * support) / total_support)
        weighted_r = float(np.sum(recall * support) / total_support)
        weighted_f1 = float(np.sum(f1 * support) / total_support)
    else:
        weighted_p, weighted_r, weighted_f1 = 0.0, 0.0, 0.0

    per_class = [
        {
            "class_index": i,
            "precision": float(precision[i]),
            "recall": float(recall[i]),
            "f1": float(f1[i]),
            "support": int(support[i]),
        }
        for i in range(k)
    ]

    return {
        "per_class": per_class,
        "macro": {"precision": macro_p, "recall": macro_r, "f1": macro_f1},
        "weighted": {"precision": weighted_p, "recall": weighted_r, "f1": weighted_f1},
    }


def _binary_roc_auc_mann_whitney(y_binary: np.ndarray, score: np.ndarray) -> float:
    """Calcula ROC-AUC binário de forma exata via estatística U de Mann-Whitney.

    AUC = (sum(ranks_pos) - n_pos * (n_pos + 1) / 2) / (n_pos * n_neg)
    Trata empates (ties) atribuindo postos médios.
    """
    pos_mask = y_binary == 1
    n_pos = int(np.sum(pos_mask))
    n_neg = len(y_binary) - n_pos

    if n_pos == 0 or n_neg == 0:
        return 0.5  # Indefinido com uma única classe

    # Atribui postos médios para empates
    order = np.argsort(score)
    ranks = np.empty(len(score), dtype=np.float64)
    ranks[order] = np.arange(1, len(score) + 1, dtype=np.float64)

    # Identifica e corrige empates de scores
    sorted_scores = score[order]
    unique_vals, inverse_indices, counts = np.unique(
        sorted_scores, return_inverse=True, return_counts=True
    )

    if len(unique_vals) < len(score):
        # Há empates
        cum_counts = np.cumsum(counts)
        start_indices = np.concatenate(([0], cum_counts[:-1]))
        mean_ranks = (start_indices + 1 + cum_counts) / 2.0
        ranks = mean_ranks[inverse_indices[np.argsort(order)]]

    pos_rank_sum = float(np.sum(ranks[pos_mask]))
    u_stat = pos_rank_sum - (n_pos * (n_pos + 1)) / 2.0
    return float(u_stat / (n_pos * n_neg))


def roc_auc(
    y_true: np.ndarray,
    probs: np.ndarray,
    n_classes: int | None = None,
) -> dict[str, Any]:
    """Calcula ROC-AUC binário ou multiclasse One-vs-Rest com média macro."""
    y_t = np.asarray(y_true, dtype=np.int64)
    probs_arr = np.asarray(probs, dtype=np.float64)

    if probs_arr.ndim == 1:
        probs_arr = np.column_stack((1.0 - probs_arr, probs_arr))

    k = n_classes if n_classes is not None else probs_arr.shape[1]

    if k == 2:
        score = probs_arr[:, 1]
        auc_val = _binary_roc_auc_mann_whitney((y_t == 1).astype(int), score)
        return {
            "roc_auc": auc_val,
            "per_class": [auc_val],
            "macro": auc_val,
        }

    # One-vs-Rest para multiclasse
    class_aucs: list[float] = []
    for i in range(k):
        y_bin = (y_t == i).astype(int)
        score_i = probs_arr[:, i]
        auc_i = _binary_roc_auc_mann_whitney(y_bin, score_i)
        class_aucs.append(auc_i)

    macro_auc = float(np.mean(class_aucs)) if class_aucs else 0.5
    return {
        "roc_auc": macro_auc,
        "per_class": class_aucs,
        "macro": macro_auc,
    }


def _binary_pr_auc_trapezoid(y_binary: np.ndarray, score: np.ndarray) -> float:
    """Calcula PR-AUC binário integrando precisão e recall via regra do trapézio."""
    pos_mask = y_binary == 1
    n_pos = int(np.sum(pos_mask))
    if n_pos == 0:
        return 0.0

    # Ordena decrescente por score
    desc_order = np.argsort(-score)
    y_sorted = y_binary[desc_order]
    scores_sorted = score[desc_order]

    # Encontra os pontos onde o threshold muda para evitar degraus redundantes
    distinct_mask = np.concatenate(([True], np.diff(scores_sorted) != 0, [True]))

    # Curvas acumuladas de TP e FP
    tp_cum = np.concatenate(([0], np.cumsum(y_sorted)))
    fp_cum = np.concatenate(([0], np.cumsum(1 - y_sorted)))

    tp_points = tp_cum[distinct_mask]
    fp_points = fp_cum[distinct_mask]

    tp_f = tp_points.astype(np.float64)
    fp_f = fp_points.astype(np.float64)
    recalls = tp_f / n_pos
    denom = tp_f + fp_f
    precisions = np.where(denom > 0, np.divide(tp_f, denom, out=np.ones_like(tp_f), where=denom > 0), 1.0)

    # Integração trapezoidal reversa: recall de 0 a 1
    # PR-AUC = sum( (R[i] - R[i-1]) * (P[i] + P[i-1]) / 2 )
    pr_auc_val = float(np.sum(np.diff(recalls) * (precisions[:-1] + precisions[1:]) / 2.0))
    return max(0.0, min(1.0, pr_auc_val))


def pr_auc(
    y_true: np.ndarray,
    probs: np.ndarray,
    n_classes: int | None = None,
) -> dict[str, Any]:
    """Calcula PR-AUC binário ou multiclasse One-vs-Rest com média macro."""
    y_t = np.asarray(y_true, dtype=np.int64)
    probs_arr = np.asarray(probs, dtype=np.float64)

    if probs_arr.ndim == 1:
        probs_arr = np.column_stack((1.0 - probs_arr, probs_arr))

    k = n_classes if n_classes is not None else probs_arr.shape[1]

    if k == 2:
        auc_val = _binary_pr_auc_trapezoid((y_t == 1).astype(int), probs_arr[:, 1])
        return {
            "pr_auc": auc_val,
            "per_class": [auc_val],
            "macro": auc_val,
        }

    class_aucs: list[float] = []
    for i in range(k):
        auc_i = _binary_pr_auc_trapezoid((y_t == i).astype(int), probs_arr[:, i])
        class_aucs.append(auc_i)

    macro_auc = float(np.mean(class_aucs)) if class_aucs else 0.0
    return {
        "pr_auc": macro_auc,
        "per_class": class_aucs,
        "macro": macro_auc,
    }


def log_loss(y_true: np.ndarray, probs: np.ndarray, eps: float = 1e-15) -> float:
    """Calcula a Log-Loss (entropia cruzada empírica) média."""
    y_t = np.asarray(y_true, dtype=np.int64)
    probs_arr = np.clip(np.asarray(probs, dtype=np.float64), eps, 1.0 - eps)

    N = len(y_t)
    if N == 0:
        return 0.0

    if probs_arr.ndim == 1:
        probs_arr = np.column_stack((1.0 - probs_arr, probs_arr))

    # Pega a probabilidade atribuída à classe verdadeira de cada amostra
    p_true = probs_arr[np.arange(N), y_t]
    return float(-np.mean(np.log(p_true)))


def brier_score(y_true: np.ndarray, probs: np.ndarray) -> float:
    """Calcula o Brier Score.

    Para caso binário 1D (vetor de probabilidades da classe positiva):
        (1/N) * sum_i (p_i1 - y_i)^2
    Para formato 2D multiclasse / one-hot:
        (1/N) * sum_i sum_k (p_ik - y_ik)^2
    """
    y_t = np.asarray(y_true, dtype=np.int64)
    probs_arr = np.asarray(probs, dtype=np.float64)
    N = len(y_t)
    if N == 0:
        return 0.0

    if probs_arr.ndim == 1:
        return float(np.mean((probs_arr - y_t) ** 2))

    K = probs_arr.shape[1]
    y_one_hot = np.zeros((N, K), dtype=np.float64)
    y_one_hot[np.arange(N), y_t] = 1.0

    return float(np.mean(np.sum((probs_arr - y_one_hot) ** 2, axis=1)))


def expected_calibration_error(
    y_true: np.ndarray,
    probs: np.ndarray,
    n_bins: int = 10,
) -> dict[str, Any]:
    """Calcula o Expected Calibration Error (ECE) e os pontos da curva de calibração."""
    y_t = np.asarray(y_true, dtype=np.int64)
    probs_arr = np.asarray(probs, dtype=np.float64)

    if probs_arr.ndim == 1:
        confidences = np.where(probs_arr >= 0.5, probs_arr, 1.0 - probs_arr)
        preds = (probs_arr >= 0.5).astype(np.int64)
    else:
        confidences = np.max(probs_arr, axis=1)
        preds = np.argmax(probs_arr, axis=1)

    correct = (preds == y_t).astype(np.float64)
    N = len(y_t)
    if N == 0:
        return {"ece": 0.0, "bins": []}

    bin_boundaries = np.linspace(0.0, 1.0, n_bins + 1)
    ece_val = 0.0
    bins_info: list[dict[str, Any]] = []

    for b in range(n_bins):
        b_low = bin_boundaries[b]
        b_high = bin_boundaries[b + 1]

        # Inclusão da borda superior no último bin
        if b == n_bins - 1:
            in_bin = (confidences >= b_low) & (confidences <= b_high)
        else:
            in_bin = (confidences >= b_low) & (confidences < b_high)

        count = int(np.sum(in_bin))
        if count > 0:
            bin_acc = float(np.mean(correct[in_bin]))
            bin_conf = float(np.mean(confidences[in_bin]))
            weight = count / N
            ece_val += weight * abs(bin_acc - bin_conf)
        else:
            bin_acc = 0.0
            bin_conf = float((b_low + b_high) / 2.0)

        bins_info.append(
            {
                "bin_idx": b,
                "bin_lower": float(b_low),
                "bin_upper": float(b_high),
                "accuracy": bin_acc,
                "confidence": bin_conf,
                "count": count,
            }
        )

    return {
        "ece": float(ece_val),
        "bins": bins_info,
    }


def threshold_sweep(
    y_true: np.ndarray,
    probs: np.ndarray,
    n_points: int = 50,
) -> list[dict[str, Any]]:
    """Gera varredura de limiares (0.05 a 0.95) para avaliação de métricas binárias."""
    y_t = np.asarray(y_true, dtype=np.int64)
    probs_arr = np.asarray(probs, dtype=np.float64)
    scores = probs_arr[:, 1] if probs_arr.ndim == 2 else probs_arr

    thresholds = np.linspace(0.05, 0.95, n_points)
    points: list[dict[str, Any]] = []

    for t in thresholds:
        preds = (scores >= t).astype(np.int64)
        cm = confusion_matrix(y_t, preds, n_classes=2)

        tp = float(cm[1, 1])
        fp = float(cm[0, 1])
        fn = float(cm[1, 0])
        tn = float(cm[0, 0])

        prec = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        rec = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1_val = (2 * prec * rec) / (prec + rec) if (prec + rec) > 0 else 0.0
        acc_val = (tp + tn) / len(y_t) if len(y_t) > 0 else 0.0

        points.append(
            {
                "threshold": float(round(t, 4)),
                "precision": float(round(prec, 4)),
                "recall": float(round(rec, 4)),
                "f1": float(round(f1_val, 4)),
                "accuracy": float(round(acc_val, 4)),
                "tp": int(tp),
                "fp": int(fp),
                "fn": int(fn),
                "tn": int(tn),
            }
        )

    return points


def prediction_histogram(
    probs: np.ndarray,
    n_bins: int = 20,
) -> dict[str, Any]:
    """Histograma da distribuição das probabilidades de predição."""
    probs_arr = np.asarray(probs, dtype=np.float64)
    scores = probs_arr[:, 1] if probs_arr.ndim == 2 and probs_arr.shape[1] == 2 else probs_arr

    # Flattens if multidimensional
    flat_scores = scores.ravel()
    counts, bin_edges = np.histogram(flat_scores, bins=n_bins, range=(0.0, 1.0))

    return {
        "counts": counts.tolist(),
        "bin_edges": [float(round(e, 4)) for e in bin_edges],
    }


def calculate_all_metrics(
    y_true: np.ndarray,
    probs: np.ndarray,
    threshold: float = 0.5,
    n_classes: int | None = None,
) -> dict[str, Any]:
    """Calcula o pacote consolidado de métricas completas para teste/avaliação."""
    y_t = np.asarray(y_true, dtype=np.int64)
    probs_arr = np.asarray(probs, dtype=np.float64)
    if probs_arr.ndim == 1:
        probs_arr = np.column_stack((1.0 - probs_arr, probs_arr))

    k = n_classes if n_classes is not None else probs_arr.shape[1]

    if k == 2:
        y_pred = (probs_arr[:, 1] >= threshold).astype(np.int64)
    else:
        y_pred = np.argmax(probs_arr, axis=1).astype(np.int64)

    cm = confusion_matrix(y_t, y_pred, n_classes=k)
    acc = accuracy(y_t, y_pred)
    prf1 = precision_recall_f1(y_t, y_pred, n_classes=k)
    roc = roc_auc(y_t, probs_arr, n_classes=k)
    pr = pr_auc(y_t, probs_arr, n_classes=k)
    ll = log_loss(y_t, probs_arr)
    brier = brier_score(y_t, probs_arr)
    calib = expected_calibration_error(y_t, probs_arr, n_bins=10)
    hist = prediction_histogram(probs_arr, n_bins=20)

    res: dict[str, Any] = {
        "accuracy": acc,
        "confusion_matrix": cm.tolist(),
        "precision_recall_f1": prf1,
        "roc_auc": roc["roc_auc"],
        "roc_auc_details": roc,
        "pr_auc": pr["pr_auc"],
        "pr_auc_details": pr,
        "log_loss": ll,
        "brier_score": brier,
        "ece": calib["ece"],
        "calibration_bins": calib["bins"],
        "prediction_histogram": hist,
    }

    if k == 2:
        res["threshold_sweep"] = threshold_sweep(y_t, probs_arr, n_points=50)

    return res
