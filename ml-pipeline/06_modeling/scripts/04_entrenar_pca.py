# -*- coding: utf-8 -*-
"""
Modeling 04 | Entrenamiento PCA

Este script entrena PCA sobre la matriz escalada del flujo seleccionado.

Hace lo siguiente:
- Lee la matriz escalada generada en Modeling 03.
- Lee los IDs y columnas de perfilado.
- Entrena PCA.
- Calcula varianza explicada individual y acumulada.
- Guarda scores, loadings, reporte de varianza y modelo PCA.
"""

from pathlib import Path
import pandas as pd
import numpy as np
from sklearn.decomposition import PCA
import joblib


# ============================================================
# CONFIGURACIÓN
# ============================================================

BASE_DIR = Path(r"C:\Users\Hp\OneDrive\Documentos\PT_Analisis")

FLUJO = "entidad_dia"

INPUT_SCALED = BASE_DIR / "06_modeling" / "datasets" / FLUJO / f"modeling_{FLUJO}_scaled.csv"
INPUT_IDS = BASE_DIR / "06_modeling" / "datasets" / FLUJO / f"modeling_{FLUJO}_ids.csv"

OUT_RESULTS = BASE_DIR / "06_modeling" / "results" / FLUJO / "pca"
OUT_MODELS = BASE_DIR / "06_modeling" / "models" / FLUJO / "pca"

OUT_RESULTS.mkdir(parents=True, exist_ok=True)
OUT_MODELS.mkdir(parents=True, exist_ok=True)

OUT_SCORES = OUT_RESULTS / "pca_scores.csv"
OUT_VARIANCE = OUT_RESULTS / "pca_explained_variance.csv"
OUT_LOADINGS = OUT_RESULTS / "pca_loadings.csv"
OUT_FEATURE_CONTRIBUTIONS = OUT_RESULTS / "pca_feature_contributions.csv"
OUT_MODEL = OUT_MODELS / "pca_model.joblib"


# ============================================================
# PARÁMETROS PCA
# ============================================================

RANDOM_STATE = 42

# None conserva todos los componentes posibles.
# Después elegimos cuántos usar con varianza acumulada.
N_COMPONENTS = None


# ============================================================
# FUNCIONES AUXILIARES
# ============================================================

def validate_numeric_matrix(df: pd.DataFrame) -> None:
    if df.empty:
        raise ValueError("La matriz escalada está vacía.")

    nulls = int(df.isna().sum().sum())
    if nulls > 0:
        raise ValueError(f"La matriz escalada contiene {nulls:,} nulos.")

    arr = df.to_numpy()

    if np.isinf(arr).sum() > 0:
        raise ValueError("La matriz escalada contiene valores infinitos.")

    non_numeric = [
        col for col in df.columns
        if not pd.api.types.is_numeric_dtype(df[col])
    ]

    if non_numeric:
        raise ValueError(f"Hay columnas no numéricas en la matriz escalada: {non_numeric}")


def build_variance_report(pca: PCA) -> pd.DataFrame:
    explained = pca.explained_variance_ratio_
    cumulative = np.cumsum(explained)

    return pd.DataFrame({
        "component": [f"PC{i+1}" for i in range(len(explained))],
        "component_number": list(range(1, len(explained) + 1)),
        "explained_variance_ratio": explained,
        "explained_variance_pct": explained * 100,
        "cumulative_variance_ratio": cumulative,
        "cumulative_variance_pct": cumulative * 100,
        "eigenvalue": pca.explained_variance_,
    })


def build_loadings(pca: PCA, feature_names: list[str]) -> pd.DataFrame:
    loadings = pd.DataFrame(
        pca.components_.T,
        index=feature_names,
        columns=[f"PC{i+1}" for i in range(pca.components_.shape[0])]
    )

    loadings = loadings.reset_index().rename(columns={"index": "feature"})
    return loadings


def build_feature_contributions(loadings: pd.DataFrame) -> pd.DataFrame:
    pc_cols = [c for c in loadings.columns if c.startswith("PC")]

    rows = []

    for pc in pc_cols:
        temp = loadings[["feature", pc]].copy()
        temp["component"] = pc
        temp["loading"] = temp[pc]
        temp["abs_loading"] = temp[pc].abs()
        temp = temp.drop(columns=[pc])
        temp = temp.sort_values("abs_loading", ascending=False)
        temp["rank_abs_loading"] = range(1, len(temp) + 1)
        rows.append(temp)

    return pd.concat(rows, ignore_index=True)


def suggest_components(df_variance: pd.DataFrame) -> dict:
    suggestions = {}

    for threshold in [0.70, 0.80, 0.85, 0.90, 0.95]:
        mask = df_variance["cumulative_variance_ratio"] >= threshold
        if mask.any():
            suggestions[f"n_components_{int(threshold * 100)}pct"] = int(
                df_variance.loc[mask, "component_number"].iloc[0]
            )
        else:
            suggestions[f"n_components_{int(threshold * 100)}pct"] = None

    return suggestions


# ============================================================
# PIPELINE PRINCIPAL
# ============================================================

def main():
    print("\nModeling 04 | Entrenamiento PCA")
    print(f"Flujo: {FLUJO}")

    if not INPUT_SCALED.exists():
        raise FileNotFoundError(f"No existe matriz escalada: {INPUT_SCALED}")

    if not INPUT_IDS.exists():
        raise FileNotFoundError(f"No existe archivo de IDs: {INPUT_IDS}")

    print(f"\nLeyendo matriz escalada:")
    print(f"- {INPUT_SCALED}")

    X = pd.read_csv(INPUT_SCALED, encoding="utf-8-sig", low_memory=False)

    print(f"Filas X: {len(X):,}")
    print(f"Columnas X: {len(X.columns):,}")

    validate_numeric_matrix(X)

    print(f"\nLeyendo IDs:")
    print(f"- {INPUT_IDS}")

    ids = pd.read_csv(INPUT_IDS, encoding="utf-8-sig", low_memory=False)

    if len(ids) != len(X):
        raise ValueError(
            f"IDs y matriz escalada no tienen el mismo número de filas: "
            f"{len(ids):,} vs {len(X):,}"
        )

    print("\nEntrenando PCA...")

    pca = PCA(n_components=N_COMPONENTS, random_state=RANDOM_STATE)
    scores_array = pca.fit_transform(X)

    n_components_final = scores_array.shape[1]

    print(f"Componentes generados: {n_components_final:,}")

    pc_cols = [f"PC{i+1}" for i in range(n_components_final)]

    scores = pd.DataFrame(
        scores_array,
        columns=pc_cols,
        index=X.index,
    )

    scores_out = pd.concat([ids, scores], axis=1)

    variance_report = build_variance_report(pca)
    loadings = build_loadings(pca, X.columns.tolist())
    feature_contributions = build_feature_contributions(loadings)

    suggestions = suggest_components(variance_report)

    print("\nSugerencia de componentes por varianza acumulada:")
    for k, v in suggestions.items():
        print(f"- {k}: {v}")

    # Guardar
    scores_out.to_csv(OUT_SCORES, index=False, encoding="utf-8-sig")
    variance_report.to_csv(OUT_VARIANCE, index=False, encoding="utf-8-sig")
    loadings.to_csv(OUT_LOADINGS, index=False, encoding="utf-8-sig")
    feature_contributions.to_csv(OUT_FEATURE_CONTRIBUTIONS, index=False, encoding="utf-8-sig")
    joblib.dump(pca, OUT_MODEL)

    print(f"\nArchivos generados:")
    print(f"- {OUT_SCORES}")
    print(f"- {OUT_VARIANCE}")
    print(f"- {OUT_LOADINGS}")
    print(f"- {OUT_FEATURE_CONTRIBUTIONS}")
    print(f"- {OUT_MODEL}")

    print("\nPrimeros 10 componentes:")
    print(
        variance_report.head(10)[
            [
                "component",
                "explained_variance_pct",
                "cumulative_variance_pct",
                "eigenvalue",
            ]
        ].to_string(index=False)
    )

    print("\nProceso terminado.")


if __name__ == "__main__":
    main()