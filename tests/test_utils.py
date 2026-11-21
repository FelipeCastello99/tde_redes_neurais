from __future__ import annotations

import numpy as np
import pytest

from nn.utils import relative_path, set_seed


def test_set_seed_is_reproducible() -> None:
    first = set_seed(42).random(10)
    second = set_seed(42).random(10)
    np.testing.assert_array_equal(first, second)


def test_set_seed_changes_with_seed() -> None:
    first = set_seed(1).random(10)
    second = set_seed(2).random(10)
    assert not np.array_equal(first, second)


def test_set_seed_rejects_negative() -> None:
    with pytest.raises(ValueError, match="seed"):
        set_seed(-1)


def test_relative_path_inside_project() -> None:
    assert relative_path(__file__) == "tests/test_utils.py"
