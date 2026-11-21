"""Pipeline de dados do TDE: carga, alvo, features, split e pré-processamento.

O fluxo completo é:

1. ``load_raw`` lê o CSV oficial (latin-1, ``;``, decimal com vírgula) e
   descarta o único registro sem alvo.
2. ``build_target`` transforma a gravidade em alvo binário ou de 3 classes.
3. ``feature_frame`` seleciona os grupos de features, deriva variáveis
   temporais e reduz o traçado da via ao seu termo principal.
4. ``split_indices`` separa treino/validação/teste de forma estratificada.
5. ``fit_preprocessor`` aprende **somente com o treino** as categorias
   (agrupando as raras em ``__OUTROS__``), a imputação e a escala.
6. ``transform`` produz a matriz ``float32`` usada pela MLP.

Nenhuma estatística de validação ou teste entra no ``Preprocessor``. Esse é o
invariante que evita vazamento de dados e é coberto por teste.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from nn.config import (
    CLASS_NAMES,
    CLASS_WEIGHT_MODES,
    GROUP_CATEGORICAL,
    GROUP_NUMERIC,
    GROUP_ORDER,
    GROUP_RAW_COLUMNS,
    LEAKAGE_COLUMNS,
    LOG1P_COLUMNS,
    RESERVED_CATEGORY,
    SCALERS,
    TARGETS,
    DataConfig,
)
from nn.utils import DATA_DIR

__all__ = [
    "Dataset",
    "Preprocessor",
    "Splits",
    "build_target",
    "class_weights",
    "dataset_summary",
    "feature_frame",
    "fit_preprocessor",
    "load_raw",
    "prepare_dataset",
    "split",
    "split_indices",
    "target_mask",
    "transform",
]

TARGET_COLUMN = "classificacao_acidente"
TARGET_MAP_3: dict[str, int] = {
    "Sem Vítimas": 0,
    "Com Vítimas Feridas": 1,
    "Com Vítimas Fatais": 2,
}
WEEKEND_DAYS = frozenset({"sábado", "domingo"})
SCHEMA_VERSION = 1
DEFAULT_DATA_PATH = DATA_DIR / "datatran2024.csv"


# ---------------------------------------------------------------------------
# Carga e alvo
# ---------------------------------------------------------------------------


def load_raw(path: str | Path | None = None) -> pd.DataFrame:
    """Lê o CSV do DATATRAN e remove registros sem classificação.

    O arquivo oficial usa ``latin-1``, separador ``;`` e vírgula decimal em
    ``km``, ``latitude`` e ``longitude``. A opção ``decimal=","`` cuida da
    conversão sem precisar de ``str.replace`` em cada coluna.

    Parameters
    ----------
    path:
        Caminho do CSV. Por padrão, ``data/raw/datatran2024.csv``.

    Returns
    -------
    pandas.DataFrame
        Uma linha por ocorrência, com o alvo sempre preenchido.
    """
    csv_path = Path(path) if path is not None else DEFAULT_DATA_PATH
    if not csv_path.exists():
        raise FileNotFoundError(
            f"dataset não encontrado em {csv_path}. Rode `make fetch` para baixá-lo."
        )

    frame = pd.read_csv(
        csv_path,
        sep=";",
        encoding="latin-1",
        decimal=",",
        dtype={"br": "Int64", "km": "float64"},
    )

    if TARGET_COLUMN not in frame.columns:
        raise ValueError(
            f"coluna de alvo ausente ({TARGET_COLUMN!r}); o arquivo não parece ser o DATATRAN."
        )

    # O DATATRAN 2024 tem exatamente 1 registro com classificação "NA".
    # Pandas lê "NA" como valor ausente; descartamos para manter o alvo válido.
    frame = frame.loc[frame[TARGET_COLUMN].notna()].reset_index(drop=True)
    return frame


def _check_target(target: str) -> None:
    if target not in TARGETS:
        raise ValueError(f"target deve ser um de {TARGETS}; recebido {target!r}")


def build_target(frame: pd.DataFrame, target: str) -> np.ndarray:
    """Converte a coluna de gravidade no vetor de alvo inteiro.

    - ``fatal_binario``: 1 se ``mortos > 0``, 0 caso contrário;
    - ``gravidade_3_classes``: 0 sem vítimas, 1 com feridos, 2 com fatais.
    """
    _check_target(target)

    if target == "fatal_binario":
        if "mortos" not in frame.columns:
            raise ValueError("coluna 'mortos' ausente para construir o alvo binário")
        deaths = pd.to_numeric(frame["mortos"], errors="coerce").fillna(0)
        return (deaths > 0).to_numpy(dtype=np.int64)

    labels = frame[TARGET_COLUMN]
    mapped = labels.map(TARGET_MAP_3)
    invalid = mapped.isna()
    if bool(invalid.any()):
        examples = labels.loc[invalid].astype(str).unique()[:5].tolist()
        raise ValueError(
            f"classificações sem mapeamento para o alvo de 3 classes: {examples}"
        )
    return mapped.astype("int64").to_numpy()


def target_mask(frame: pd.DataFrame, target: str) -> np.ndarray:
    """Máscara booleana das linhas com alvo definido para ``target``."""
    _check_target(target)
    if target == "fatal_binario":
        return pd.to_numeric(frame["mortos"], errors="coerce").notna().to_numpy()
    return frame[TARGET_COLUMN].isin(tuple(TARGET_MAP_3)).to_numpy()


# ---------------------------------------------------------------------------
# Features
# ---------------------------------------------------------------------------


def _selected_groups(cfg: DataConfig) -> tuple[str, ...]:
    """Grupos na ordem canônica, independente da ordem enviada pelo formulário."""
    return tuple(group for group in GROUP_ORDER if group in cfg.feature_groups)


def _numeric_columns(cfg: DataConfig) -> tuple[str, ...]:
    return tuple(
        column for group in _selected_groups(cfg) for column in GROUP_NUMERIC[group]
    )


def _categorical_columns(cfg: DataConfig) -> tuple[str, ...]:
    return tuple(
        column for group in _selected_groups(cfg) for column in GROUP_CATEGORICAL[group]
    )


def _string_values(series: pd.Series) -> np.ndarray:
    """Converte uma coluna em ``object`` preservando acentos e tratando nulos."""
    raw = series.to_numpy(dtype=object)
    return np.array(
        [RESERVED_CATEGORY if pd.isna(value) else str(value) for value in raw],
        dtype=object,
    )


def _float_values(series: pd.Series) -> np.ndarray:
    """Converte uma coluna numérica em ``float64`` (NaN quando inválida)."""
    numeric = pd.to_numeric(series, errors="coerce")
    values = np.array(
        numeric.to_numpy(dtype=np.float64, na_value=np.nan),
        dtype=np.float64,
        copy=True,
    )
    values[~np.isfinite(values)] = np.nan
    return values


def _seconds_of_day(series: pd.Series) -> np.ndarray:
    """Segundos desde a meia-noite; horários inválidos viram 0 (meia-noite)."""
    seconds = np.zeros(len(series), dtype=np.float64)
    for index, value in enumerate(series.to_numpy(dtype=object)):
        if pd.isna(value):
            continue
        parts = str(value).strip().split(":")
        try:
            hour = int(parts[0])
            minute = int(parts[1]) if len(parts) > 1 else 0
            second = int(parts[2]) if len(parts) > 2 else 0
        except (ValueError, IndexError):
            continue
        seconds[index] = hour * 3600 + minute * 60 + second
    return np.mod(seconds, 86_400.0)


def _tracado_principal(series: pd.Series) -> np.ndarray:
    """Reduz ``"Curva;Declive;Reta"`` para ``"Curva"``.

    O campo original combina até três geometrias e tem 659 combinações. Ficar
    com o primeiro termo reduz a cardinalidade para 12 sem perder a
    característica dominante do trecho.
    """
    values: list[str] = []
    for value in series.to_numpy(dtype=object):
        if pd.isna(value):
            values.append(RESERVED_CATEGORY)
            continue
        first = str(value).split(";", maxsplit=1)[0].strip()
        values.append(first or RESERVED_CATEGORY)
    return np.array(values, dtype=object)


def feature_frame(frame: pd.DataFrame, cfg: DataConfig) -> pd.DataFrame:
    """Seleciona os grupos configurados e cria as features derivadas.

    A saída é um ``DataFrame`` sem nenhuma coluna de vazamento: as features
    numéricas vêm primeiro e as categóricas depois, sempre na ordem canônica
    de ``GROUP_ORDER``.
    """
    groups = set(_selected_groups(cfg))
    required = [
        column
        for group in GROUP_ORDER
        if group in groups
        for column in GROUP_RAW_COLUMNS[group]
    ]
    missing = sorted(set(required) - set(frame.columns))
    if missing:
        raise ValueError(f"colunas necessárias ausentes para as features: {missing}")

    values: dict[str, np.ndarray] = {}

    if "localizacao" in groups:
        values["br"] = _float_values(frame["br"])
        values["km"] = _float_values(frame["km"])
        values["uf"] = _string_values(frame["uf"])

    if "tempo" in groups:
        seconds = _seconds_of_day(frame["horario"])
        angle = 2.0 * np.pi * seconds / 86_400.0
        values["hora_sin"] = np.sin(angle)
        values["hora_cos"] = np.cos(angle)
        days = frame["dia_semana"].to_numpy(dtype=object)
        values["is_fim_semana"] = np.fromiter(
            (1.0 if day in WEEKEND_DAYS else 0.0 for day in days),
            dtype=np.float64,
            count=len(days),
        )
        values["dia_semana"] = _string_values(frame["dia_semana"])

    if "via" in groups:
        values["tipo_pista"] = _string_values(frame["tipo_pista"])
        values["tracado_principal"] = _tracado_principal(frame["tracado_via"])
        values["uso_solo"] = _string_values(frame["uso_solo"])
        values["sentido_via"] = _string_values(frame["sentido_via"])

    if "circunstancia" in groups:
        values["causa_acidente"] = _string_values(frame["causa_acidente"])
        values["tipo_acidente"] = _string_values(frame["tipo_acidente"])
        values["fase_dia"] = _string_values(frame["fase_dia"])
        values["condicao_metereologica"] = _string_values(
            frame["condicao_metereologica"]
        )

    if "frota" in groups:
        values["veiculos"] = _float_values(frame["veiculos"])

    if "regional" in groups:
        values["regional"] = _string_values(frame["regional"])
        values["delegacia"] = _string_values(frame["delegacia"])
        values["uop"] = _string_values(frame["uop"])

    ordered = {
        column: values[column] for column in _numeric_columns(cfg) + _categorical_columns(cfg)
    }
    features = pd.DataFrame(ordered)

    leaked = sorted(set(features.columns) & LEAKAGE_COLUMNS)
    if leaked:
        raise ValueError(f"colunas de vazamento detectadas nas features: {leaked}")

    return features


# ---------------------------------------------------------------------------
# Split estratificado
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class Splits:
    """Índices posicionais de treino, validação e teste."""

    train: np.ndarray
    val: np.ndarray
    test: np.ndarray

    @property
    def sizes(self) -> dict[str, int]:
        return {
            "train": int(self.train.size),
            "val": int(self.val.size),
            "test": int(self.test.size),
        }

    def to_dict(self) -> dict[str, list[int]]:
        return {
            "train": self.train.tolist(),
            "val": self.val.tolist(),
            "test": self.test.tolist(),
        }


def _class_split(
    indices: np.ndarray,
    cfg: DataConfig,
    rng: np.random.Generator,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Divide os índices de uma classe preservando a proporção configurada."""
    shuffled = rng.permutation(indices)
    total = shuffled.size

    n_test = round(total * cfg.test_size)
    n_val = round(total * cfg.val_size)

    # Classes minúsculas não conseguem alimentar os três conjuntos. Nesse caso,
    # tudo vai para o treino; com 3 exemplos, garantimos 1 em cada conjunto.
    if total >= 3:
        if cfg.test_size > 0:
            n_test = min(max(n_test, 1), total - 2)
        if cfg.val_size > 0:
            n_val = min(max(n_val, 1), total - n_test - 1)
    else:
        n_test = 0
        n_val = 0

    return (
        shuffled[n_test + n_val :],
        shuffled[n_test : n_test + n_val],
        shuffled[:n_test],
    )


def split_indices(y: np.ndarray, cfg: DataConfig) -> Splits:
    """Separa treino/validação/teste, estratificando por classe quando pedido."""
    labels = np.asarray(y)
    if labels.ndim != 1:
        raise ValueError("y deve ser um vetor 1-D")
    if labels.size == 0:
        raise ValueError("não há exemplos para dividir")

    rng = np.random.default_rng(cfg.seed)

    if not cfg.stratify:
        order = rng.permutation(labels.size)
        total = labels.size
        n_test = round(total * cfg.test_size)
        n_val = round(total * cfg.val_size)
        if total >= 3:
            n_test = min(max(n_test, 1), total - 2) if cfg.test_size > 0 else 0
            n_val = (
                min(max(n_val, 1), total - n_test - 1) if cfg.val_size > 0 else 0
            )
        return Splits(
            train=np.sort(order[n_test + n_val :]),
            val=np.sort(order[n_test : n_test + n_val]),
            test=np.sort(order[:n_test]),
        )

    train_parts: list[np.ndarray] = []
    val_parts: list[np.ndarray] = []
    test_parts: list[np.ndarray] = []

    for klass in np.unique(labels):
        class_indices = np.flatnonzero(labels == klass)
        train, val, test = _class_split(class_indices, cfg, rng)
        train_parts.append(train)
        val_parts.append(val)
        test_parts.append(test)

    def _join(parts: list[np.ndarray]) -> np.ndarray:
        joined = np.concatenate(parts) if parts else np.empty(0, dtype=np.int64)
        rng.shuffle(joined)
        return joined

    return Splits(train=_join(train_parts), val=_join(val_parts), test=_join(test_parts))


def split(frame: pd.DataFrame, y: np.ndarray, cfg: DataConfig) -> Splits:
    """Alias de ``split_indices`` que valida o alinhamento entre frame e alvo."""
    if len(frame) != len(y):
        raise ValueError("frame e y devem ter o mesmo número de linhas")
    return split_indices(y, cfg)


def _stratified_subsample(
    y: np.ndarray,
    max_rows: int,
    rng: np.random.Generator,
) -> np.ndarray:
    """Amostra ``max_rows`` mantendo a proporção das classes."""
    total = y.size
    if max_rows >= total:
        return np.arange(total)

    classes, counts = np.unique(y, return_counts=True)
    quota = counts * (max_rows / total)
    take = np.floor(quota).astype(np.int64)

    # Toda classe presente deve aparecer na amostra (max_rows é validado >= 100).
    short = take < 1
    take[short] = 1

    # Se os mínimos estouraram o orçamento, reduz das classes maiores.
    while int(take.sum()) > max_rows:
        largest = int(np.argmax(take))
        if take[largest] <= 1:
            break
        take[largest] -= 1

    # Distribui as sobras pelas maiores partes fracionárias.
    leftover = max_rows - int(take.sum())
    remainders = quota - np.floor(quota)
    order = np.argsort(-remainders, kind="stable")
    cursor = 0
    while leftover > 0 and order.size:
        index = int(order[cursor % order.size])
        if take[index] < counts[index]:
            take[index] += 1
            leftover -= 1
        cursor += 1
        if cursor > order.size * (max_rows + 1):
            break

    chosen: list[np.ndarray] = []
    for klass, amount in zip(classes, take, strict=True):
        indices = np.flatnonzero(y == klass)
        if amount >= indices.size:
            chosen.append(indices)
        else:
            chosen.append(rng.choice(indices, size=int(amount), replace=False))
    return np.sort(np.concatenate(chosen))


# ---------------------------------------------------------------------------
# Pré-processador
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class Preprocessor:
    """Estado aprendido no treino: vocabulário, imputação e escala.

    Guardar esse estado em JSON permite que o simulador da API transforme uma
    única linha exatamente como o treino fez, sem recalcular estatísticas.
    """

    target: str
    scaler: str
    log1p_numeric: bool
    numeric_columns: tuple[str, ...]
    categorical_columns: tuple[str, ...]
    numeric_fill: tuple[float, ...]
    numeric_center: tuple[float, ...]
    numeric_scale: tuple[float, ...]
    categories: dict[str, tuple[str, ...]] = field(default_factory=dict)
    schema_version: int = SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.schema_version != SCHEMA_VERSION:
            raise ValueError(
                f"schema_version {self.schema_version!r} incompatível; esperado {SCHEMA_VERSION}"
            )
        _check_target(self.target)
        if self.scaler not in SCALERS:
            raise ValueError(f"scaler deve ser um de {SCALERS}")
        if len(self.numeric_columns) != len(self.numeric_fill):
            raise ValueError("numeric_fill incompatível com numeric_columns")
        if len(self.numeric_columns) != len(self.numeric_center):
            raise ValueError("numeric_center incompatível com numeric_columns")
        if len(self.numeric_columns) != len(self.numeric_scale):
            raise ValueError("numeric_scale incompatível com numeric_columns")

        overlap = set(self.numeric_columns) & set(self.categorical_columns)
        if overlap:
            raise ValueError(f"colunas repetidas entre numéricas e categóricas: {overlap}")
        leaked = (set(self.numeric_columns) | set(self.categorical_columns)) & LEAKAGE_COLUMNS
        if leaked:
            raise ValueError(f"colunas de vazamento no preprocessor: {sorted(leaked)}")

        if set(self.categories) != set(self.categorical_columns):
            raise ValueError("categories deve ter exatamente uma entrada por coluna categórica")
        for column, vocabulary in self.categories.items():
            if not vocabulary:
                raise ValueError(f"vocabulário vazio para a coluna {column!r}")
            if vocabulary[-1] != RESERVED_CATEGORY:
                raise ValueError(
                    f"o vocabulário de {column!r} deve terminar com {RESERVED_CATEGORY!r}"
                )
            if len(set(vocabulary)) != len(vocabulary):
                raise ValueError(f"categorias repetidas em {column!r}")

        scales = np.asarray(self.numeric_scale, dtype=np.float64)
        if np.any(~np.isfinite(scales)) or np.any(scales <= 0):
            raise ValueError("numeric_scale deve conter valores finitos e positivos")
        for name in ("numeric_fill", "numeric_center"):
            values = np.asarray(getattr(self, name), dtype=np.float64)
            if np.any(~np.isfinite(values)):
                raise ValueError(f"{name} deve conter apenas valores finitos")

    @property
    def feature_names(self) -> tuple[str, ...]:
        names = list(self.numeric_columns)
        for column in self.categorical_columns:
            names.extend(f"{column}={value}" for value in self.categories[column])
        return tuple(names)

    @property
    def input_dim(self) -> int:
        return len(self.feature_names)

    @property
    def schema_hash(self) -> str:
        """Hash estável da ordem/nomes das colunas (invariante do contrato)."""
        payload = json.dumps(self.feature_names, ensure_ascii=False).encode("utf-8")
        return hashlib.sha256(payload).hexdigest()[:16]

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "target": self.target,
            "scaler": self.scaler,
            "log1p_numeric": self.log1p_numeric,
            "numeric_columns": list(self.numeric_columns),
            "categorical_columns": list(self.categorical_columns),
            "numeric_fill": [float(value) for value in self.numeric_fill],
            "numeric_center": [float(value) for value in self.numeric_center],
            "numeric_scale": [float(value) for value in self.numeric_scale],
            "categories": {
                column: list(vocabulary) for column, vocabulary in self.categories.items()
            },
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, sort_keys=True)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Preprocessor:
        required = {
            "schema_version",
            "target",
            "scaler",
            "log1p_numeric",
            "numeric_columns",
            "categorical_columns",
            "numeric_fill",
            "numeric_center",
            "numeric_scale",
            "categories",
        }
        missing = sorted(required - set(data))
        if missing:
            raise ValueError(f"campos ausentes no preprocessor: {missing}")

        return cls(
            schema_version=int(data["schema_version"]),
            target=str(data["target"]),
            scaler=str(data["scaler"]),
            log1p_numeric=bool(data["log1p_numeric"]),
            numeric_columns=tuple(str(value) for value in data["numeric_columns"]),
            categorical_columns=tuple(str(value) for value in data["categorical_columns"]),
            numeric_fill=tuple(float(value) for value in data["numeric_fill"]),
            numeric_center=tuple(float(value) for value in data["numeric_center"]),
            numeric_scale=tuple(float(value) for value in data["numeric_scale"]),
            categories={
                str(column): tuple(str(value) for value in values)
                for column, values in data["categories"].items()
            },
        )

    @classmethod
    def from_json(cls, text: str) -> Preprocessor:
        payload = json.loads(text)
        if not isinstance(payload, dict):
            raise ValueError("JSON do preprocessor deve ser um objeto")
        return cls.from_dict(payload)


def _numeric_values(
    frame: pd.DataFrame,
    columns: tuple[str, ...],
    *,
    log1p: bool,
) -> np.ndarray:
    """Matriz numérica com ``log1p`` opcional e contagens não negativas."""
    matrix = np.full((len(frame), len(columns)), np.nan, dtype=np.float64)
    for index, column in enumerate(columns):
        values = _float_values(frame[column])
        if log1p and column in LOG1P_COLUMNS:
            # km, br e veiculos são contagens/extensões: log1p comprime caudas
            # longas sem alterar a ordem nem criar valores negativos.
            values = np.log1p(np.maximum(values, 0.0))
        matrix[:, index] = values
    return matrix


def _fit_categories(series: pd.Series, rare_min_count: int) -> tuple[str, ...]:
    """Vocabulário da coluna, agrupando categorias raras em ``__OUTROS__``."""
    values = _string_values(series)
    names, counts = np.unique(values, return_counts=True)
    frequent = sorted(
        str(name)
        for name, count in zip(names.tolist(), counts.tolist(), strict=True)
        if str(name) != RESERVED_CATEGORY and count >= rare_min_count
    )
    # __OUTROS__ sempre existe para absorver categorias não vistas no treino
    # (importante no simulador) e as raras.
    return (*frequent, RESERVED_CATEGORY)


def fit_preprocessor(train: pd.DataFrame, cfg: DataConfig) -> Preprocessor:
    """Aprende vocabulário, imputação e escala **usando apenas o treino**."""
    if len(train) == 0:
        raise ValueError("não é possível ajustar o preprocessor com treino vazio")

    numeric_columns = _numeric_columns(cfg)
    categorical_columns = _categorical_columns(cfg)
    missing = sorted(
        (set(numeric_columns) | set(categorical_columns)) - set(train.columns)
    )
    if missing:
        raise ValueError(f"colunas ausentes no treino: {missing}")

    numeric = _numeric_values(train, numeric_columns, log1p=cfg.log1p_numeric)

    fill = np.zeros(len(numeric_columns), dtype=np.float64)
    for index in range(len(numeric_columns)):
        column = numeric[:, index]
        valid = np.isfinite(column)
        fill[index] = float(np.median(column[valid])) if bool(valid.any()) else 0.0

    filled = np.where(np.isnan(numeric), fill, numeric)

    if filled.shape[1] == 0:
        center = np.empty(0, dtype=np.float64)
        scale = np.empty(0, dtype=np.float64)
    elif cfg.scaler == "standard":
        center = filled.mean(axis=0)
        scale = filled.std(axis=0)
    elif cfg.scaler == "minmax":
        center = filled.min(axis=0)
        scale = filled.max(axis=0) - center
    else:
        center = np.zeros(fill.shape, dtype=np.float64)
        scale = np.ones(fill.shape, dtype=np.float64)

    scale = np.where((~np.isfinite(scale)) | (scale <= 0), 1.0, scale)
    center = np.where(np.isfinite(center), center, 0.0)
    fill = np.where(np.isfinite(fill), fill, 0.0)

    categories = {
        column: _fit_categories(train[column], cfg.rare_min_count)
        for column in categorical_columns
    }

    return Preprocessor(
        target=cfg.target,
        scaler=cfg.scaler,
        log1p_numeric=cfg.log1p_numeric,
        numeric_columns=numeric_columns,
        categorical_columns=categorical_columns,
        numeric_fill=tuple(float(value) for value in fill),
        numeric_center=tuple(float(value) for value in center),
        numeric_scale=tuple(float(value) for value in scale),
        categories=categories,
    )


def transform(frame: pd.DataFrame, prep: Preprocessor) -> np.ndarray:
    """One-hot + escala, com ordem de colunas idêntica à do treino.

    A transformação de uma linha isolada é exatamente a linha correspondente
    da matriz completa — não há padronização por lote. Isso mantém o
    simulador consistente com o treino.
    """
    required = set(prep.numeric_columns) | set(prep.categorical_columns)
    missing = sorted(required - set(frame.columns))
    if missing:
        raise ValueError(f"colunas ausentes para transform: {missing}")

    numeric = _numeric_values(
        frame, prep.numeric_columns, log1p=prep.log1p_numeric
    )
    fill = np.asarray(prep.numeric_fill, dtype=np.float64)
    center = np.asarray(prep.numeric_center, dtype=np.float64)
    scale = np.asarray(prep.numeric_scale, dtype=np.float64)

    numeric = np.where(np.isnan(numeric), fill, numeric)
    numeric = (numeric - center) / scale
    blocks = [numeric.astype(np.float32, copy=False)]

    for column in prep.categorical_columns:
        vocabulary = prep.categories[column]
        index = {value: position for position, value in enumerate(vocabulary)}
        reserved = index[RESERVED_CATEGORY]
        values = _string_values(frame[column])
        positions = np.fromiter(
            (index.get(str(value), reserved) for value in values),
            dtype=np.int64,
            count=len(values),
        )
        block = np.zeros((len(frame), len(vocabulary)), dtype=np.float32)
        block[np.arange(len(frame)), positions] = 1.0
        blocks.append(block)

    if len(blocks) == 1:
        return blocks[0]
    return np.concatenate(blocks, axis=1)


# ---------------------------------------------------------------------------
# Pesos de classe e dataset final
# ---------------------------------------------------------------------------


def class_weights(
    y: np.ndarray,
    mode: str = "balanced",
    custom_weights: tuple[float, ...] | list[float] | None = None,
    *,
    n_classes: int | None = None,
) -> np.ndarray:
    """Pesos por classe para a loss ponderada.

    ``balanced`` usa ``n / (k * bincount(y))``, de modo que cada classe
    contribui igualmente para a loss mesmo com 7% de casos fatais. Classes
    ausentes recebem peso 1 (não aparecem no treino, então o valor é inócuo).
    """
    labels = np.asarray(y, dtype=np.int64)
    if labels.ndim != 1:
        raise ValueError("y deve ser um vetor 1-D")
    if labels.size == 0:
        raise ValueError("y não pode ser vazio")

    classes = int(n_classes) if n_classes is not None else int(labels.max()) + 1
    if classes <= 0:
        raise ValueError("n_classes deve ser positivo")
    if int(labels.max()) >= classes:
        raise ValueError(
            f"y contém classe {int(labels.max())}, incompatível com n_classes={classes}"
        )
    if mode not in CLASS_WEIGHT_MODES:
        raise ValueError(f"mode deve ser um de {CLASS_WEIGHT_MODES}; recebido {mode!r}")

    counts = np.bincount(labels, minlength=classes).astype(np.float64)

    if mode == "none":
        return np.ones(classes, dtype=np.float64)

    if mode == "balanced":
        weights = np.ones(classes, dtype=np.float64)
        present = counts > 0
        weights[present] = labels.size / (classes * counts[present])
        return weights

    if custom_weights is None:
        raise ValueError("class_weight='custom' exige custom_weights")
    weights = np.asarray(custom_weights, dtype=np.float64)
    if weights.shape != (classes,):
        raise ValueError(
            f"custom_weights deve ter {classes} valores; recebido {weights.shape}"
        )
    if np.any(weights < 0) or weights.sum() <= 0:
        raise ValueError("custom_weights deve ser não negativo com soma positiva")
    return weights


@dataclass(frozen=True, slots=True)
class Dataset:
    """Matrizes prontas para a MLP, com o preprocessor e a configuração."""

    X_train: np.ndarray
    y_train: np.ndarray
    X_val: np.ndarray
    y_val: np.ndarray
    X_test: np.ndarray
    y_test: np.ndarray
    preprocessor: Preprocessor
    config: DataConfig
    class_weights: np.ndarray
    splits: Splits
    raw_rows: int
    used_rows: int

    @property
    def input_dim(self) -> int:
        return int(self.X_train.shape[1])

    @property
    def n_classes(self) -> int:
        return len(CLASS_NAMES[self.config.target])

    @property
    def feature_names(self) -> tuple[str, ...]:
        return self.preprocessor.feature_names


def prepare_dataset(
    cfg: DataConfig | None = None,
    frame: pd.DataFrame | None = None,
) -> Dataset:
    """Executa o pipeline completo e devolve as matrizes de treino/val/teste."""
    config = cfg if cfg is not None else DataConfig()

    raw = frame if frame is not None else load_raw()
    raw_rows = len(raw)

    if config.drop_duplicates:
        raw = raw.loc[~raw.duplicated()].reset_index(drop=True)

    mask = target_mask(raw, config.target)
    if not bool(mask.any()):
        raise ValueError(f"nenhuma linha com alvo válido para {config.target!r}")
    raw = raw.loc[mask].reset_index(drop=True)
    y_all = build_target(raw, config.target)

    if config.max_rows is not None and len(raw) > config.max_rows:
        rng = np.random.default_rng(config.seed)
        selected = _stratified_subsample(y_all, config.max_rows, rng)
        raw = raw.iloc[selected].reset_index(drop=True)
        y_all = y_all[selected]

    features = feature_frame(raw, config)
    splits = split_indices(y_all, config)
    prep = fit_preprocessor(features.iloc[splits.train], config)

    X_train = transform(features.iloc[splits.train], prep)
    X_val = transform(features.iloc[splits.val], prep)
    X_test = transform(features.iloc[splits.test], prep)

    weights = class_weights(
        y_all[splits.train],
        config.class_weight,
        config.custom_weights,
        n_classes=len(CLASS_NAMES[config.target]),
    )

    return Dataset(
        X_train=X_train,
        y_train=y_all[splits.train],
        X_val=X_val,
        y_val=y_all[splits.val],
        X_test=X_test,
        y_test=y_all[splits.test],
        preprocessor=prep,
        config=config,
        class_weights=weights,
        splits=splits,
        raw_rows=raw_rows,
        used_rows=len(y_all),
    )


def dataset_summary(dataset: Dataset) -> dict[str, Any]:
    """Resumo serializável para o notebook e para o painel da API."""
    k = dataset.n_classes

    def counts(values: np.ndarray) -> list[int]:
        return np.bincount(values, minlength=k).astype(int).tolist()

    return {
        "target": dataset.config.target,
        "class_names": list(CLASS_NAMES[dataset.config.target]),
        "raw_rows": dataset.raw_rows,
        "used_rows": dataset.used_rows,
        "split_sizes": dataset.splits.sizes,
        "class_counts": {
            "all": counts(np.concatenate([dataset.y_train, dataset.y_val, dataset.y_test])),
            "train": counts(dataset.y_train),
            "val": counts(dataset.y_val),
            "test": counts(dataset.y_test),
        },
        "class_weights": [float(weight) for weight in dataset.class_weights],
        "n_features": dataset.input_dim,
        "n_numeric_features": len(dataset.preprocessor.numeric_columns),
        "n_categorical_columns": len(dataset.preprocessor.categorical_columns),
        "feature_schema_hash": dataset.preprocessor.schema_hash,
        "scaler": dataset.config.scaler,
        "log1p_numeric": dataset.config.log1p_numeric,
        "rare_min_count": dataset.config.rare_min_count,
        "max_rows": dataset.config.max_rows,
    }
