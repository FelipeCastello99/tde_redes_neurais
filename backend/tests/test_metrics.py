from __future__ import annotations

import numpy as np
import pytest
from sklearn.metrics import (
    accuracy_score,
    brier_score_loss,
    precision_recall_fscore_support,
    roc_auc_score,
)
from sklearn.metrics import (
    confusion_matrix as sk_confusion_matrix,
)
from sklearn.metrics import (
    log_loss as sk_log_loss,
)

from nn.metrics import (
    accuracy,
    brier_score,
    calculate_all_metrics,
    confusion_matrix,
    expected_calibration_error,
    log_loss,
    pr_auc,
    precision_recall_f1,
    prediction_histogram,
    roc_auc,
    threshold_sweep,
)


@pytest.fixture
def binary_data() -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    rng = np.random.default_rng(42)
    y_true = rng.choice([0, 1], size=200, p=[0.7, 0.3])
    scores = rng.beta(2, 5, size=200)
    # Aumenta score dos positivos
    scores[y_true == 1] = rng.beta(5, 2, size=int(np.sum(y_true == 1)))
    probs = np.column_stack((1.0 - scores, scores))
    y_pred = (scores >= 0.5).astype(int)
    return y_true, y_pred, probs


@pytest.fixture
def multiclass_data() -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    rng = np.random.default_rng(42)
    y_true = rng.choice([0, 1, 2], size=300, p=[0.2, 0.6, 0.2])
    logits = rng.normal(0, 1, size=(300, 3))
    # Favorece acertos
    for i in range(300):
        logits[i, y_true[i]] += 2.0
    exp_l = np.exp(logits - np.max(logits, axis=1, keepdims=True))
    probs = exp_l / np.sum(exp_l, axis=1, keepdims=True)
    y_pred = np.argmax(probs, axis=1)
    return y_true, y_pred, probs


def test_confusion_matrix_parity(
    binary_data: tuple[np.ndarray, np.ndarray, np.ndarray],
    multiclass_data: tuple[np.ndarray, np.ndarray, np.ndarray],
) -> None:
    # Binário
    y_t_b, y_p_b, _ = binary_data
    cm_our_b = confusion_matrix(y_t_b, y_p_b, n_classes=2)
    cm_sk_b = sk_confusion_matrix(y_t_b, y_p_b, labels=[0, 1])
    np.testing.assert_array_equal(cm_our_b, cm_sk_b)

    # Multiclasse K=3
    y_t_m, y_p_m, _ = multiclass_data
    cm_our_m = confusion_matrix(y_t_m, y_p_m, n_classes=3)
    cm_sk_m = sk_confusion_matrix(y_t_m, y_p_m, labels=[0, 1, 2])
    np.testing.assert_array_equal(cm_our_m, cm_sk_m)


def test_accuracy_parity(
    binary_data: tuple[np.ndarray, np.ndarray, np.ndarray],
    multiclass_data: tuple[np.ndarray, np.ndarray, np.ndarray],
) -> None:
    y_t_b, y_p_b, _ = binary_data
    assert abs(accuracy(y_t_b, y_p_b) - accuracy_score(y_t_b, y_p_b)) < 1e-9

    y_t_m, y_p_m, _ = multiclass_data
    assert abs(accuracy(y_t_m, y_p_m) - accuracy_score(y_t_m, y_p_m)) < 1e-9


def test_precision_recall_f1_parity(
    binary_data: tuple[np.ndarray, np.ndarray, np.ndarray],
    multiclass_data: tuple[np.ndarray, np.ndarray, np.ndarray],
) -> None:
    # Binário
    y_t_b, y_p_b, _ = binary_data
    our_b = precision_recall_f1(y_t_b, y_p_b, n_classes=2)
    sk_p, sk_r, sk_f1, _ = precision_recall_fscore_support(
        y_t_b, y_p_b, labels=[0, 1], average=None
    )
    for i in range(2):
        assert abs(our_b["per_class"][i]["precision"] - sk_p[i]) < 1e-9
        assert abs(our_b["per_class"][i]["recall"] - sk_r[i]) < 1e-9
        assert abs(our_b["per_class"][i]["f1"] - sk_f1[i]) < 1e-9

    sk_mac_p, sk_mac_r, sk_mac_f1, _ = precision_recall_fscore_support(
        y_t_b, y_p_b, average="macro"
    )
    assert abs(our_b["macro"]["precision"] - sk_mac_p) < 1e-9
    assert abs(our_b["macro"]["recall"] - sk_mac_r) < 1e-9
    assert abs(our_b["macro"]["f1"] - sk_mac_f1) < 1e-9

    # Multiclasse K=3
    y_t_m, y_p_m, _ = multiclass_data
    our_m = precision_recall_f1(y_t_m, y_p_m, n_classes=3)
    sk_p_m, sk_r_m, sk_f1_m, _ = precision_recall_fscore_support(
        y_t_m, y_p_m, labels=[0, 1, 2], average=None
    )
    for i in range(3):
        assert abs(our_m["per_class"][i]["precision"] - sk_p_m[i]) < 1e-9
        assert abs(our_m["per_class"][i]["recall"] - sk_r_m[i]) < 1e-9
        assert abs(our_m["per_class"][i]["f1"] - sk_f1_m[i]) < 1e-9

    sk_w_p, sk_w_r, sk_w_f1, _ = precision_recall_fscore_support(
        y_t_m, y_p_m, average="weighted"
    )
    assert abs(our_m["weighted"]["precision"] - sk_w_p) < 1e-9
    assert abs(our_m["weighted"]["recall"] - sk_w_r) < 1e-9
    assert abs(our_m["weighted"]["f1"] - sk_w_f1) < 1e-9


def test_roc_auc_parity(
    binary_data: tuple[np.ndarray, np.ndarray, np.ndarray],
    multiclass_data: tuple[np.ndarray, np.ndarray, np.ndarray],
) -> None:
    # Binário
    y_t_b, _, probs_b = binary_data
    our_auc_b = roc_auc(y_t_b, probs_b, n_classes=2)["roc_auc"]
    sk_auc_b = roc_auc_score(y_t_b, probs_b[:, 1])
    assert abs(our_auc_b - sk_auc_b) < 1e-6

    # Multiclasse One-vs-Rest Macro
    y_t_m, _, probs_m = multiclass_data
    our_auc_m = roc_auc(y_t_m, probs_m, n_classes=3)["macro"]
    sk_auc_m = roc_auc_score(y_t_m, probs_m, multi_class="ovr", average="macro")
    assert abs(our_auc_m - sk_auc_m) < 1e-6


def test_log_loss_and_brier_parity(
    binary_data: tuple[np.ndarray, np.ndarray, np.ndarray],
    multiclass_data: tuple[np.ndarray, np.ndarray, np.ndarray],
) -> None:
    # Log loss binária
    y_t_b, _, probs_b = binary_data
    assert abs(log_loss(y_t_b, probs_b) - sk_log_loss(y_t_b, probs_b)) < 1e-9

    # Brier score binário
    assert abs(brier_score(y_t_b, probs_b[:, 1]) - brier_score_loss(y_t_b, probs_b[:, 1])) < 1e-9

    # Log loss multiclasse
    y_t_m, _, probs_m = multiclass_data
    assert abs(log_loss(y_t_m, probs_m) - sk_log_loss(y_t_m, probs_m)) < 1e-9


def test_pr_auc_and_calibration(
    binary_data: tuple[np.ndarray, np.ndarray, np.ndarray],
) -> None:
    y_t_b, _, probs_b = binary_data
    pr_res = pr_auc(y_t_b, probs_b, n_classes=2)
    assert 0.0 <= pr_res["pr_auc"] <= 1.0

    calib = expected_calibration_error(y_t_b, probs_b, n_bins=10)
    assert 0.0 <= calib["ece"] <= 1.0
    assert len(calib["bins"]) == 10

    hist = prediction_histogram(probs_b, n_bins=20)
    assert len(hist["counts"]) == 20
    assert sum(hist["counts"]) == len(y_t_b)


def test_threshold_sweep(
    binary_data: tuple[np.ndarray, np.ndarray, np.ndarray],
) -> None:
    y_t_b, _, probs_b = binary_data
    sweep = threshold_sweep(y_t_b, probs_b, n_points=50)
    assert len(sweep) == 50
    assert sweep[0]["threshold"] == 0.05
    assert sweep[-1]["threshold"] == 0.95
    assert "precision" in sweep[0]
    assert "recall" in sweep[0]
    assert "f1" in sweep[0]


def test_calculate_all_metrics(
    binary_data: tuple[np.ndarray, np.ndarray, np.ndarray],
) -> None:
    y_t_b, _, probs_b = binary_data
    res = calculate_all_metrics(y_t_b, probs_b, threshold=0.5, n_classes=2)

    assert "accuracy" in res
    assert "confusion_matrix" in res
    assert "precision_recall_f1" in res
    assert "roc_auc" in res
    assert "pr_auc" in res
    assert "threshold_sweep" in res
    assert "ece" in res
