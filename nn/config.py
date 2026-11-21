"""Configurações do pipeline de dados.

Este módulo concentra os nomes canônicos de alvos, grupos de features e as
validações da ``DataConfig``. Ele é importado tanto pelo notebook quanto pela
API, garantindo que os dois lados falem a mesma língua.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, fields
from typing import Any

# ---------------------------------------------------------------------------
# Constantes canônicas
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
        # Normaliza listas para tuplas (o formulário envia listas).
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
