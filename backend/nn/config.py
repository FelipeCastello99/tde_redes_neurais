"""Configurações do pipeline de dados e da rede neural.

Este módulo concentra os nomes canônicos de alvos, grupos de features,
hiperparâmetros da MLP, presets e validações de ``DataConfig`` e ``ModelConfig``.
Ele é importado tanto pelo notebook quanto pela API, garantindo que os dois
lados falem a mesma língua.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, fields
from typing import Any

# ---------------------------------------------------------------------------
# Constantes canônicas de Dados
# ---------------------------------------------------------------------------

TARGETS: tuple[str, ...] = ("fatal_binario", "gravidade_3_classes")

CLASS_NAMES: dict[str, tuple[str, ...]] = {
    "fatal_binario": ("sem_vitima_fatal", "vitima_fatal"),
    "gravidade_3_classes": ("Sem Vítimas", "Com Vítimas Feridas", "Com Vítimas Fatais"),
}

GROUP_ORDER: tuple[str, ...] = (
    "localizacao",
    "tempo",
    "via",
    "circunstancia",
    "frota",
    "regional",
)

#: Colunas de origem necessárias para cada grupo (usadas em ``feature_frame``).
GROUP_RAW_COLUMNS: dict[str, tuple[str, ...]] = {
    "localizacao": ("uf", "br", "km"),
    "tempo": ("dia_semana", "horario"),
    "via": ("tipo_pista", "tracado_via", "uso_solo", "sentido_via"),
    "circunstancia": ("causa_acidente", "tipo_acidente", "fase_dia", "condicao_metereologica"),
    "frota": ("veiculos",),
    "regional": ("regional", "delegacia", "uop"),
}

#: Features numéricas produzidas por grupo (ordem canônica).
GROUP_NUMERIC: dict[str, tuple[str, ...]] = {
    "localizacao": ("br", "km"),
    "tempo": ("hora_sin", "hora_cos", "is_fim_semana"),
    "via": (),
    "circunstancia": (),
    "frota": ("veiculos",),
    "regional": (),
}

#: Features categóricas produzidas por grupo (ordem canônica).
GROUP_CATEGORICAL: dict[str, tuple[str, ...]] = {
    "localizacao": ("uf",),
    "tempo": ("dia_semana",),
    "via": ("tipo_pista", "tracado_principal", "uso_solo", "sentido_via"),
    "circunstancia": (
        "causa_acidente",
        "tipo_acidente",
        "fase_dia",
        "condicao_metereologica",
    ),
    "frota": (),
    "regional": ("regional", "delegacia", "uop"),
}

SCALERS: tuple[str, ...] = ("standard", "minmax", "none")
CLASS_WEIGHT_MODES: tuple[str, ...] = ("none", "balanced", "custom")

#: Categorias agrupadas quando aparecem menos que ``rare_min_count`` no treino.
RESERVED_CATEGORY = "__OUTROS__"

#: Colunas que nunca podem entrar como feature (vazamento de alvo ou metadado).
LEAKAGE_COLUMNS: frozenset[str] = frozenset(
    {
        "id",
        "data_inversa",
        "classificacao_acidente",
        "mortos",
        "feridos",
        "feridos_leves",
        "feridos_graves",
        "ilesos",
        "ignorados",
        "pessoas",
        "latitude",
        "longitude",
    }
)

#: ``log1p`` só faz sentido em contagens não negativas.
LOG1P_COLUMNS: frozenset[str] = frozenset({"br", "km", "veiculos"})


# ---------------------------------------------------------------------------
# Constantes canônicas de Modelo
# ---------------------------------------------------------------------------

ACTIVATIONS: tuple[str, ...] = ("relu", "tanh", "sigmoid", "leaky_relu")
INITS: tuple[str, ...] = ("he", "xavier", "normal")
LOSSES: tuple[str, ...] = ("ce", "weighted_ce", "focal")
OPTIMIZERS: tuple[str, ...] = ("sgd", "momentum", "adam", "adamw")
LR_DECAYS: tuple[str, ...] = ("none", "step", "cosine")


# ---------------------------------------------------------------------------
# DataConfig
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class DataConfig:
    """Configuração de dados, split e pré-processamento.

    Os campos espelham exatamente o que o formulário do frontend expõe.
    """

    target: str = "fatal_binario"
    feature_groups: tuple[str, ...] = (
        "localizacao",
        "tempo",
        "via",
        "circunstancia",
        "frota",
    )
    max_rows: int | None = None
    val_size: float = 0.2
    test_size: float = 0.2
    stratify: bool = True
    seed: int = 42
    rare_min_count: int = 30
    scaler: str = "standard"
    log1p_numeric: bool = True
    class_weight: str = "balanced"
    custom_weights: tuple[float, ...] | None = None
    drop_duplicates: bool = True

    def __post_init__(self) -> None:
        object.__setattr__(self, "feature_groups", tuple(self.feature_groups))
        if self.custom_weights is not None:
            object.__setattr__(self, "custom_weights", tuple(self.custom_weights))

        if self.target not in TARGETS:
            raise ValueError(f"target deve ser um de {TARGETS}; recebido {self.target!r}")

        if not self.feature_groups:
            raise ValueError("selecione pelo menos um grupo de features")
        unknown = [group for group in self.feature_groups if group not in GROUP_ORDER]
        if unknown:
            raise ValueError(f"grupos desconhecidos: {unknown}; válidos: {list(GROUP_ORDER)}")
        if len(set(self.feature_groups)) != len(self.feature_groups):
            raise ValueError("feature_groups contém grupos repetidos")

        if not 0.0 < self.test_size < 1.0:
            raise ValueError(f"test_size deve estar em (0, 1); recebido {self.test_size}")
        if not 0.0 <= self.val_size < 1.0:
            raise ValueError(f"val_size deve estar em [0, 1); recebido {self.val_size}")
        if self.test_size + self.val_size >= 1.0:
            raise ValueError("test_size + val_size deve ser menor que 1")

        if self.max_rows is not None and self.max_rows < 100:
            raise ValueError("max_rows deve ser >= 100 ou None")
        if self.seed < 0:
            raise ValueError(f"seed deve ser >= 0; recebido {self.seed}")
        if self.rare_min_count < 0:
            raise ValueError("rare_min_count deve ser >= 0")
        if self.scaler not in SCALERS:
            raise ValueError(f"scaler deve ser um de {SCALERS}")
        if self.class_weight not in CLASS_WEIGHT_MODES:
            raise ValueError(f"class_weight deve ser um de {CLASS_WEIGHT_MODES}")

        if self.class_weight == "custom":
            if not self.custom_weights:
                raise ValueError("class_weight='custom' exige custom_weights")
            if any(weight < 0 for weight in self.custom_weights):
                raise ValueError("custom_weights não pode conter valores negativos")
            if sum(self.custom_weights) <= 0:
                raise ValueError("custom_weights precisa de pelo menos um valor positivo")
        elif self.custom_weights is not None:
            raise ValueError("custom_weights só pode ser usado com class_weight='custom'")

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["feature_groups"] = list(self.feature_groups)
        if self.custom_weights is not None:
            data["custom_weights"] = list(self.custom_weights)
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> DataConfig:
        allowed = {field.name for field in fields(cls)}
        unknown = set(data) - allowed
        if unknown:
            raise ValueError(f"campos desconhecidos em DataConfig: {sorted(unknown)}")
        return cls(**data)


DEFAULT_DATA_CONFIG = DataConfig()


# ---------------------------------------------------------------------------
# ModelConfig
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class ModelConfig:
    """Configuração da rede neural (arquitetura, otimizador, regularização).

    Os campos espelham exatamente o que o formulário do frontend expõe.
    """

    hidden_layers: int = 2
    neurons: tuple[int, ...] = (64, 32)
    activation: str = "relu"
    init: str = "he"
    dropout: float = 0.0
    l2: float = 0.0
    loss: str = "weighted_ce"
    focal_gamma: float = 2.0
    optimizer: str = "adam"
    lr: float = 1e-3
    lr_decay: str = "none"
    decay_rate: float = 0.5
    decay_every: int = 50
    batch_size: int | None = 256
    epochs: int = 200
    patience: int = 15
    grad_clip: float = 5.0
    threshold: float = 0.5
    seed: int = 42

    def __post_init__(self) -> None:
        object.__setattr__(self, "neurons", tuple(self.neurons))

        if not 1 <= self.hidden_layers <= 4:
            raise ValueError(f"hidden_layers deve estar em [1, 4]; recebido {self.hidden_layers}")
        if len(self.neurons) != self.hidden_layers:
            raise ValueError(
                f"len(neurons) ({len(self.neurons)}) deve ser igual a hidden_layers ({self.hidden_layers})"
            )
        if any(n < 1 for n in self.neurons):
            raise ValueError("número de neurônios por camada deve ser >= 1")

        if self.activation not in ACTIVATIONS:
            raise ValueError(f"activation deve ser um de {ACTIVATIONS}; recebido {self.activation!r}")
        if self.init not in INITS:
            raise ValueError(f"init deve ser um de {INITS}; recebido {self.init!r}")
        if not 0.0 <= self.dropout <= 0.5:
            raise ValueError(f"dropout deve estar em [0.0, 0.5]; recebido {self.dropout}")
        if not 0.0 <= self.l2 <= 0.1:
            raise ValueError(f"l2 deve estar em [0.0, 0.1]; recebido {self.l2}")
        if self.loss not in LOSSES:
            raise ValueError(f"loss deve ser um de {LOSSES}; recebido {self.loss!r}")
        if self.focal_gamma < 0.0:
            raise ValueError(f"focal_gamma deve ser >= 0.0; recebido {self.focal_gamma}")
        if self.optimizer not in OPTIMIZERS:
            raise ValueError(f"optimizer deve ser um de {OPTIMIZERS}; recebido {self.optimizer!r}")
        if not 0.0 < self.lr <= 1.0:
            raise ValueError(f"lr deve estar em (0.0, 1.0]; recebido {self.lr}")
        if self.lr_decay not in LR_DECAYS:
            raise ValueError(f"lr_decay deve ser um de {LR_DECAYS}; recebido {self.lr_decay!r}")
        if not 0.0 < self.decay_rate < 1.0:
            raise ValueError(f"decay_rate deve estar em (0.0, 1.0); recebido {self.decay_rate}")
        if self.decay_every < 1:
            raise ValueError(f"decay_every deve ser >= 1; recebido {self.decay_every}")
        if self.batch_size is not None and self.batch_size < 1:
            raise ValueError("batch_size deve ser >= 1 ou None")
        if not 1 <= self.epochs <= 2000:
            raise ValueError(f"epochs deve estar em [1, 2000]; recebido {self.epochs}")
        if self.patience < 0:
            raise ValueError(f"patience deve ser >= 0; recebido {self.patience}")
        if self.grad_clip < 0.0:
            raise ValueError(f"grad_clip deve ser >= 0.0; recebido {self.grad_clip}")
        if not 0.05 <= self.threshold <= 0.95:
            raise ValueError(f"threshold deve estar em [0.05, 0.95]; recebido {self.threshold}")
        if self.seed < 0:
            raise ValueError(f"seed deve ser >= 0; recebido {self.seed}")

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["neurons"] = list(self.neurons)
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ModelConfig:
        allowed = {field.name for field in fields(cls)}
        unknown = set(data) - allowed
        if unknown:
            raise ValueError(f"campos desconhecidos em ModelConfig: {sorted(unknown)}")
        return cls(**data)


DEFAULT_MODEL_CONFIG = ModelConfig()


# ---------------------------------------------------------------------------
# Presets e Auxiliares
# ---------------------------------------------------------------------------

PRESETS: dict[str, dict[str, Any]] = {
    "rapido": {
        "data": {
            "max_rows": 20000,
        },
        "model": {
            "hidden_layers": 1,
            "neurons": (32,),
            "batch_size": None,
            "lr": 3e-3,
            "epochs": 80,
        },
    },
    "equilibrado": {
        "data": {},
        "model": {},
    },
    "profundo": {
        "data": {},
        "model": {
            "hidden_layers": 3,
            "neurons": (128, 64, 32),
            "dropout": 0.1,
            "l2": 1e-4,
            "optimizer": "adamw",
            "lr_decay": "cosine",
            "epochs": 300,
        },
    },
}


def build_configs(
    data_raw: dict[str, Any] | None = None,
    model_raw: dict[str, Any] | None = None,
    preset: str | None = None,
) -> tuple[DataConfig, ModelConfig]:
    """Cria instâncias de DataConfig e ModelConfig aplicando preset e dicionários.

    Se preset for informado ('rapido', 'equilibrado', 'profundo'), seus valores
    são usados como base antes da aplicação de data_raw e model_raw.
    """
    data_dict: dict[str, Any] = {}
    model_dict: dict[str, Any] = {}

    if preset is not None:
        if preset not in PRESETS:
            raise ValueError(f"preset deve ser um de {list(PRESETS)}; recebido {preset!r}")
        data_dict.update(PRESETS[preset]["data"])
        model_dict.update(PRESETS[preset]["model"])

    if data_raw:
        data_dict.update(data_raw)
    if model_raw:
        model_dict.update(model_raw)

    return DataConfig.from_dict(data_dict), ModelConfig.from_dict(model_dict)


def estimate_seconds(
    n_train: int,
    n_features: int,
    data_cfg: DataConfig,
    model_cfg: ModelConfig,
    ms_per_sample_epoch: float = 1.2e-4,
) -> float:
    """Estima os segundos necessários para o treinamento.

    Mede a complexidade proporcional a:
      n_train * total_neurons * epochs.
    """
    total_neurons = sum(model_cfg.neurons) + n_features
    work_units = n_train * total_neurons * model_cfg.epochs
    estimated_ms = work_units * (ms_per_sample_epoch / 50.0)
    return max(0.1, round(estimated_ms / 1000.0, 2))
