from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from nn.config import (
    LEAKAGE_COLUMNS,
    RESERVED_CATEGORY,
    DataConfig,
)
from nn.data import (
    Preprocessor,
    build_target,
    class_weights,
    dataset_summary,
    feature_frame,
    fit_preprocessor,
    load_raw,
    prepare_dataset,
    split,
    split_indices,
    target_mask,
    transform,
)
from nn.utils import DATA_DIR

RAW_PATH = DATA_DIR / "datatran2024.csv"

DAYS = (
    "segunda-feira",
    "terça-feira",
    "quarta-feira",
    "quinta-feira",
    "sexta-feira",
    "sábado",
    "domingo",
)
CLASS_LABELS = ("Sem Vítimas", "Com Vítimas Feridas", "Com Vítimas Fatais")


def synthetic_raw(rows: int = 300) -> pd.DataFrame:
    """Base sintética com os mesmos nomes/formatos das colunas usadas."""
    index = np.arange(rows)
    labels = np.where(index < 150, 0, np.where(index < 270, 1, 2))

    frame = pd.DataFrame(
        {
            "id": index + 1,
            "data_inversa": "2024-01-01",
            "dia_semana": [DAYS[value % len(DAYS)] for value in index],
            "horario": [f"{value % 24:02d}:{(value * 7) % 60:02d}:00" for value in index],
            "uf": [("SP", "MG", "BA")[value % 3] for value in index],
            "br": 101 + index % 10,
            "km": index * 0.5,
            "municipio": "Município",
            "causa_acidente": [
                "Causa Rara" if value in (0, 1) else "Ultrapassagem Indevida"
                for value in index
            ],
            "tipo_acidente": [
                ("Colisão frontal", "Saída de leito carroçável", "Colisão lateral")[
                    value % 3
                ]
                for value in index
            ],
            "classificacao_acidente": [CLASS_LABELS[value] for value in labels],
            "fase_dia": [("Pleno dia", "Plena Noite", "Amanhecer")[value % 3] for value in index],
            "sentido_via": [("Crescente", "Decrescente", "Não Informado")[value % 3] for value in index],
            "condicao_metereologica": [("Céu Claro", "Chuva", "Sol")[value % 3] for value in index],
            "tipo_pista": [("Simples", "Dupla", "Múltipla")[value % 3] for value in index],
            "tracado_via": [
                ("Reta", "Curva;Declive", "Aclive;Reta")[value % 3] for value in index
            ],
            "uso_solo": [("Sim", "Não")[value % 2] for value in index],
            "pessoas": 1 + index % 4,
            "mortos": (labels == 2).astype(int),
            "feridos_leves": (labels == 1).astype(int),
            "feridos_graves": 0,
            "ilesos": 0,
            "ignorados": 0,
            "feridos": (labels == 1).astype(int),
            "veiculos": 1 + index % 4,
            "latitude": -20.0,
            "longitude": -45.0,
            "regional": "SPRF-SP",
            "delegacia": "DEL01-SP",
            "uop": "UOP01-DEL01-SP",
        }
    )
    # Uma linha sem alvo, como no CSV oficial.
    frame.loc[len(frame)] = frame.iloc[0]
    frame.loc[len(frame) - 1, "classificacao_acidente"] = None
    frame.loc[len(frame) - 1, "id"] = 9999
    return frame


@pytest.fixture(scope="session")
def raw() -> pd.DataFrame:
    if not RAW_PATH.exists():
        pytest.skip("CSV do DATATRAN ausente; rode `make fetch`")
    return load_raw(RAW_PATH)


@pytest.fixture()
def synthetic() -> pd.DataFrame:
    return synthetic_raw()


def test_load_raw_drops_missing_target(raw: pd.DataFrame) -> None:
    assert raw.shape == (73_201, 30)
    assert raw["classificacao_acidente"].notna().all()
    assert raw["km"].dtype == np.float64
    # "Vítimas" comprova que a leitura em latin-1 preservou os acentos.
    assert "Com Vítimas Fatais" in set(raw["classificacao_acidente"])


def test_target_counts_on_official_dataset(raw: pd.DataFrame) -> None:
    fatal = build_target(raw, "fatal_binario")
    assert fatal.dtype == np.int64
    assert int(fatal.sum()) == 5_225
    np.testing.assert_array_equal(np.bincount(fatal), [67_976, 5_225])

    severity = build_target(raw, "gravidade_3_classes")
    np.testing.assert_array_equal(np.bincount(severity), [11_782, 56_194, 5_225])


def test_target_mask_excludes_missing_classification(synthetic: pd.DataFrame) -> None:
    mask_binary = target_mask(synthetic, "fatal_binario")
    mask_three = target_mask(synthetic, "gravidade_3_classes")
    assert mask_binary.sum() == 301
    assert mask_three.sum() == 300

    with pytest.raises(ValueError, match="classificações sem mapeamento"):
        build_target(synthetic, "gravidade_3_classes")

    cleaned = synthetic.loc[mask_three].reset_index(drop=True)
    assert len(build_target(cleaned, "gravidade_3_classes")) == 300


def test_feature_derivations(synthetic: pd.DataFrame) -> None:
    frame = synthetic.iloc[:7].copy()
    frame.loc[0, "tracado_via"] = "Curva;Declive;Reta"
    frame.loc[0, "horario"] = "06:00:00"
    frame.loc[0, "dia_semana"] = "sábado"
    frame.loc[1, "horario"] = "12:00:00"
    frame.loc[1, "dia_semana"] = "segunda-feira"

    features = feature_frame(frame, DataConfig())

    assert features.loc[0, "tracado_principal"] == "Curva"
    assert features.loc[0, "is_fim_semana"] == 1.0
    assert features.loc[1, "is_fim_semana"] == 0.0
    np.testing.assert_allclose(features.loc[0, "hora_sin"], 1.0, atol=1e-12)
    np.testing.assert_allclose(features.loc[0, "hora_cos"], 0.0, atol=1e-12)
    np.testing.assert_allclose(features.loc[1, "hora_sin"], 0.0, atol=1e-12)
    np.testing.assert_allclose(features.loc[1, "hora_cos"], -1.0, atol=1e-12)


def test_feature_frame_has_no_leakage(synthetic: pd.DataFrame) -> None:
    config = DataConfig(
        feature_groups=("localizacao", "tempo", "via", "circunstancia", "frota", "regional")
    )
    features = feature_frame(synthetic, config)
    assert not set(features.columns) & LEAKAGE_COLUMNS
    assert "classificacao_acidente" not in features.columns
    assert "mortos" not in features.columns
    assert "id" not in features.columns


def test_split_is_stratified(raw: pd.DataFrame) -> None:
    y = build_target(raw, "gravidade_3_classes")
    config = DataConfig()
    splits = split_indices(y, config)

    sizes = splits.sizes
    assert set(sizes) == {"train", "val", "test"}
    assert sizes["train"] + sizes["val"] + sizes["test"] == len(y)

    all_indices = np.concatenate([splits.train, splits.val, splits.test])
    assert np.array_equal(np.sort(all_indices), np.arange(len(y)))
    assert np.intersect1d(splits.train, splits.val).size == 0
    assert np.intersect1d(splits.train, splits.test).size == 0

    overall = np.bincount(y) / len(y)
    for part, target_fraction in (
        (splits.train, 0.6),
        (splits.val, 0.2),
        (splits.test, 0.2),
    ):
        assert len(part) / len(y) == pytest.approx(target_fraction, abs=0.01)
        proportions = np.bincount(y[part], minlength=3) / len(part)
        np.testing.assert_allclose(proportions, overall, atol=0.01)


def test_split_rejects_misaligned_frame(raw: pd.DataFrame, synthetic: pd.DataFrame) -> None:
    with pytest.raises(ValueError, match="mesmo número de linhas"):
        split(synthetic, np.zeros(len(raw), dtype=int), DataConfig())


def test_preprocessor_uses_only_training_statistics(synthetic: pd.DataFrame) -> None:
    config = DataConfig()
    features = feature_frame(synthetic.iloc[:300], config)
    train = features.iloc[:180]
    validation = features.iloc[180:]

    prep_train = fit_preprocessor(train, config)
    prep_all = fit_preprocessor(pd.concat([train, validation]), config)

    # br/km da validação têm médias diferentes; se entrassem no fit, os
    # centros mudariam.
    assert prep_train.numeric_center != prep_all.numeric_center

    km_index = prep_train.numeric_columns.index("km")
    expected = np.mean(np.log1p(train["km"].to_numpy(dtype=np.float64)))
    assert prep_train.numeric_center[km_index] == pytest.approx(expected)

    # A categoria "Causa Rara" só aparece nas duas primeiras linhas do treino;
    # mesmo assim o vocabulário é aprendido do treino e não do restante.
    vocabulary = prep_train.categories["causa_acidente"]
    assert vocabulary[-1] == RESERVED_CATEGORY
    assert "Ultrapassagem Indevida" in vocabulary


def test_transform_single_row_equals_matrix_row(synthetic: pd.DataFrame) -> None:
    config = DataConfig()
    features = feature_frame(synthetic.iloc[:120], config)
    prep = fit_preprocessor(features.iloc[:80], config)
    matrix = transform(features, prep)

    assert matrix.dtype == np.float32
    assert matrix.shape == (len(features), prep.input_dim)

    for row in (0, 1, 57, len(features) - 1):
        single = transform(features.iloc[[row]], prep)
        np.testing.assert_array_equal(single[0], matrix[row])


def test_outros_groups_rare_and_unseen_categories(synthetic: pd.DataFrame) -> None:
    config = DataConfig(rare_min_count=30)
    features = feature_frame(synthetic.iloc[:300], config)
    # "Causa Rara" aparece 2 vezes no treino, abaixo do limite de 30.
    prep = fit_preprocessor(features, config)
    vocabulary = prep.categories["causa_acidente"]
    assert "Causa Rara" not in vocabulary
    assert RESERVED_CATEGORY in vocabulary

    rare_row = features.iloc[[0]].copy()
    rare_row.loc[rare_row.index[0], "causa_acidente"] = "Categoria Nunca Vista"
    matrix = transform(rare_row, prep)
    column = prep.feature_names.index(f"causa_acidente={RESERVED_CATEGORY}")
    assert matrix[0, column] == 1.0


def test_preprocessor_json_round_trip(synthetic: pd.DataFrame) -> None:
    config = DataConfig()
    features = feature_frame(synthetic.iloc[:200], config)
    prep = fit_preprocessor(features.iloc[:140], config)

    payload = prep.to_json()
    restored = Preprocessor.from_json(payload)

    assert restored.to_json() == payload
    assert restored.feature_names == prep.feature_names
    assert restored.schema_hash == prep.schema_hash
    np.testing.assert_array_equal(
        transform(features.iloc[140:], restored),
        transform(features.iloc[140:], prep),
    )


def test_class_weights_modes() -> None:
    y = np.array([0, 0, 0, 1])
    np.testing.assert_allclose(class_weights(y, "balanced"), [2 / 3, 2.0])
    np.testing.assert_allclose(class_weights(y, "none"), [1.0, 1.0])
    np.testing.assert_allclose(
        class_weights(y, "custom", custom_weights=(1.0, 3.0)), [1.0, 3.0]
    )

    with pytest.raises(ValueError, match="custom_weights"):
        class_weights(y, "custom")
    with pytest.raises(ValueError, match="custom_weights deve ter"):
        class_weights(y, "custom", custom_weights=(1.0,))


def test_scalers() -> None:
    features = pd.DataFrame(
        {
            "br": [100.0, 110.0, 120.0, 130.0],
            "km": [0.0, 10.0, 20.0, 30.0],
            "veiculos": [1.0, 1.0, 2.0, 2.0],
            "hora_sin": [0.0, 1.0, 0.0, 1.0],
            "hora_cos": [1.0, 0.0, 1.0, 0.0],
            "is_fim_semana": [0.0, 1.0, 0.0, 1.0],
            "uf": ["SP", "MG", "BA", "SP"],
            "dia_semana": ["segunda-feira", "sábado", "domingo", "sexta-feira"],
        }
    )
    groups = ("localizacao", "tempo", "frota")

    standard = fit_preprocessor(features, DataConfig(feature_groups=groups))
    standard_matrix = transform(features, standard)
    n_numeric = len(standard.numeric_columns)
    np.testing.assert_allclose(
        standard_matrix[:, :n_numeric].mean(axis=0), 0.0, atol=1e-6
    )
    np.testing.assert_allclose(
        standard_matrix[:, :n_numeric].std(axis=0), 1.0, atol=1e-6
    )

    minmax = fit_preprocessor(
        features, DataConfig(feature_groups=groups, scaler="minmax")
    )
    minmax_matrix = transform(features, minmax)[:, :n_numeric]
    np.testing.assert_allclose(minmax_matrix.min(axis=0), 0.0, atol=1e-6)
    np.testing.assert_allclose(minmax_matrix.max(axis=0), 1.0, atol=1e-6)

    none = fit_preprocessor(
        features, DataConfig(feature_groups=groups, scaler="none")
    )
    none_matrix = transform(features, none)
    np.testing.assert_allclose(
        none_matrix[:, none.numeric_columns.index("km")],
        np.log1p(features["km"].to_numpy()),
    )


def test_prepare_dataset_pipeline(synthetic: pd.DataFrame) -> None:
    dataset = prepare_dataset(DataConfig(target="gravidade_3_classes"), synthetic)

    assert dataset.used_rows == 300
    assert dataset.X_train.shape == (180, dataset.input_dim)
    assert dataset.X_val.shape[0] == 60
    assert dataset.X_test.shape[0] == 60
    assert dataset.X_train.dtype == np.float32
    assert np.isfinite(dataset.X_train).all()
    assert dataset.class_weights.shape == (3,)
    np.testing.assert_array_equal(dataset.feature_names, dataset.preprocessor.feature_names)

    summary = dataset_summary(dataset)
    assert summary["target"] == "gravidade_3_classes"
    assert summary["split_sizes"] == {"train": 180, "val": 60, "test": 60}
    assert summary["class_counts"]["train"] == [90, 72, 18]
    assert summary["n_features"] == dataset.input_dim
    assert len(summary["feature_schema_hash"]) == 16


def test_max_rows_is_stratified(raw: pd.DataFrame) -> None:
    config = DataConfig(target="gravidade_3_classes", max_rows=1_200)
    dataset = prepare_dataset(config, raw)

    assert dataset.used_rows == 1_200
    assert len(dataset.y_train) + len(dataset.y_val) + len(dataset.y_test) == 1_200

    overall = np.bincount(build_target(raw, "gravidade_3_classes")) / len(raw)
    counts = np.bincount(
        np.concatenate([dataset.y_train, dataset.y_val, dataset.y_test]),
        minlength=3,
    )
    np.testing.assert_allclose(counts / counts.sum(), overall, atol=0.01)
