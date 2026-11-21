"""Utilidades compartilhadas: reprodutibilidade, formatação e caminhos.

O projeto usa ``numpy.random.Generator`` (via ``default_rng``) em vez do
estado global do NumPy. Isso evita que duas chamadas em ordem diferente
alterem o resultado de um treino e facilita reproduzir os experimentos.
"""

from __future__ import annotations

import os
import random
from pathlib import Path

import numpy as np

BACKEND_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = BACKEND_ROOT.parent
DATA_DIR = BACKEND_ROOT / "data" / "raw"
ARTIFACTS_DIR = BACKEND_ROOT / "artifacts"


def set_seed(seed: int) -> np.random.Generator:
    """Fixa as seeds globais e devolve um gerador dedicado.

    Parameters
    ----------
    seed:
        Semente inteira não negativa.

    Returns
    -------
    numpy.random.Generator
        Gerador que deve ser passado explicitamente para as rotinas
        aleatórias (inicialização de pesos, embaralhamento, split).

    Notes
    -----
    ``PYTHONHASHSEED`` só tem efeito se definido *antes* do interpretador
    iniciar; aqui ele é registrado para documentar a intenção e usado pelo
    ``Makefile``/CI. O gerador devolvido é o mecanismo confiável.
    """
    if seed < 0:
        raise ValueError(f"seed deve ser >= 0, recebido {seed}")

    os.environ.setdefault("PYTHONHASHSEED", str(seed))
    random.seed(seed)
    np.random.seed(seed)
    return np.random.default_rng(seed)


def relative_path(path: str | Path) -> str:
    """Devolve o caminho relativo à raiz do backend (para logs legíveis)."""
    path = Path(path)
    try:
        return str(path.resolve().relative_to(BACKEND_ROOT))
    except ValueError:
        return str(path)
