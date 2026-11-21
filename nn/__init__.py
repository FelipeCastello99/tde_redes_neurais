"""Núcleo de rede neural do TDE, implementado do zero em NumPy.

Módulos:
    config  — dataclasses de configuração, validação e presets
    data    — carga, limpeza, features, encoding, scaler e split
    model   — classe ``NnModel`` (forward, loss, backward, fit)
    metrics — métricas de classificação sem sklearn
    export  — serialização de modelo/preprocessor (JSON e NPZ)

A API FastAPI é a fonte única da verdade: importa estes módulos, e o
notebook do TDE faz o mesmo, exibindo o código-fonte em sala.
"""

__version__ = "0.1.0"
