# -*- coding: utf-8 -*-
"""
Modeling 04 | Entrenamiento PCA incremental municipio-día

Este script entrena PCA para municipio-día usando IncrementalPCA por chunks.

Hace lo siguiente:
- Lee la matriz escalada municipio-día por chunks.
- Lee el reporte de features generado en Modeling 03.
- Entrena IncrementalPCA sin cargar todo en memoria.
- Calcula varianza explicada, varianza acumulada, loadings y contribuciones.
- Guarda el modelo PCA entrenado.
"""

from pathlib import Path
import numpy as np
import pandas as pd
import joblib
from sklearn.decomposition import IncrementalPCA


# ============================================================
# CONFIGURACIÓN
# ============================================================

BASE_DIR = Path(r"C:\Users\Hp\OneDrive\Documentos\PT_Analisis")

FLUJO = "municipio_dia"

CHUNKSIZE = 300_000
N_COMPONENTS = 65

INPUT_SCALED = BASE_DIR / "06_modeling" / "datasets" / FLUJO / f"modeling_{FLUJO}_scaled.csv"
INPUT_FEATURES = BASE_DIR / "06_modeling" / "reports" / f"modeling_03_features_{FLUJO}.csv"

OUT_RESULTS = BASE_DIR / "06_modeling" / "results" / FLUJO / "pca"
OUT_MODELS = BASE_DIR / "06_modeling" / "models" / FLUJO / "pca"

OUT_RESULTS.mkdir(parents=True, exist_ok=True)
OUT_MODELS.mkdir(parents=True, exist_ok=True)

OUT_VARIANCE = OUT_RESULTS / "pca_explained_variance.csv"
OUT_LOADINGS = OUT_RESULTS / "pca_loadings.csv"
OUT_CONTRIBUTIONS = OUT_RESULTS / "pca_feature_contributions.csv"
OUT_MODEL = OUT_MODELS / "pca_model.joblib"


# ============================================================
# FUNCIONES AUXILIARES
# ============================================================

def ensure_file(path: Path, label: str) -> None:
    if not path.exists():
        raise FileNotFoundError(f"No existe {label}: {path}")


def validate_numeric_chunk(chunk: pd.DataFrame, chunk_id: int) -> None:
    nulls = int(chunk.isna().sum().sum())
    if nulls > 0:
        raise ValueError(f"Chunk {chunk_id}: contiene {nulls:,} nulos.")

    arr = chunk.to_numpy(dtype=np.float64)

    if np.isinf(arr).sum() > 0:
        raise ValueError(f"Chunk {chunk_id}: contiene infinitos.")


def read_feature_names() -> list[str]:
    features = pd.read_csv(INPUT_FEATURES, encoding="utf-8-sig")

    if "feature" not in features.columns:
        raise ValueError("El reporte de features no contiene columna 'feature'.")

    return features["feature"].astype(str).tolist()


def build_variance_df(pca: IncrementalPCA) -> pd.DataFrame:
    rows = []

    explained = pca.explained_variance_ratio_
    eigenvalues = pca.explained_variance_

    cumulative = np.cumsum(explained)

    for i, (evr, cum, eig) in enumerate(zip(explained, cumulative, eigenvalues), start=1):
        rows.append({
            "component_number": i,
            "component": f"PC{i}",
            "explained_variance_pct": float(evr * 100),
            "cumulative_variance_pct": float(cum * 100),
            "eigenvalue": float(eig),
        })

    return pd.DataFrame(rows)


def build_loadings_df(pca: IncrementalPCA, feature_names: list[str]) -> pd.DataFrame:
    rows = []

    for i, component_vector in enumerate(pca.components_, start=1):
        for feature, loading in zip(feature_names, component_vector):
            rows.append({
                "component_number": i,
                "component": f"PC{i}",
                "feature": feature,
                "loading": float(loading),
                "abs_loading": float(abs(loading)),
            })

    return pd.DataFrame(rows)


def build_contributions_df(loadings: pd.DataFrame) -> pd.DataFrame:
    out = loadings.copy()

    out["squared_loading"] = out["loading"] ** 2

    total_by_pc = out.groupby("component")["squared_loading"].transform("sum")

    out["contribution_pct_within_pc"] = np.where(
        total_by_pc != 0,
        out["squared_loading"] / total_by_pc * 100,
        np.nan,
    )

    out = out.sort_values(
        by=["component_number", "contribution_pct_within_pc"],
        ascending=[True, False],
    )

    return out


# ============================================================
# PIPELINE PRINCIPAL
# ============================================================

def main():
    print("\nModeling 04 | Entrenamiento PCA incremental")
    print(f"Flujo: {FLUJO}")

    ensure_file(INPUT_SCALED, "matriz escalada")
    ensure_file(INPUT_FEATURES, "reporte de features")

    feature_names = read_feature_names()

    print(f"\nFeatures esperadas: {len(feature_names):,}")
    print(f"Componentes PCA solicitados: {N_COMPONENTS:,}")

    if N_COMPONENTS > len(feature_names):
        raise ValueError(
            f"N_COMPONENTS={N_COMPONENTS} no puede ser mayor que features={len(feature_names)}."
        )

    print(f"\nLeyendo matriz escalada por chunks:")
    print(f"- {INPUT_SCALED}")

    pca = IncrementalPCA(n_components=N_COMPONENTS)

    total_rows = 0

    print("\nEntrenando IncrementalPCA...")

    for i, chunk in enumerate(
        pd.read_csv(
            INPUT_SCALED,
            encoding="utf-8-sig",
            chunksize=CHUNKSIZE,
            low_memory=False,
        ),
        start=1,
    ):
        if list(chunk.columns) != feature_names:
            raise ValueError(
                f"Chunk {i}: las columnas no coinciden con modeling_03_features."
            )

        validate_numeric_chunk(chunk, i)

        X = chunk.to_numpy(dtype=np.float64)

        pca.partial_fit(X)

        total_rows += len(chunk)

        print(f"- PCA chunk {i:,}: filas acumuladas {total_rows:,}")

    variance = build_variance_df(pca)
    loadings = build_loadings_df(pca, feature_names)
    contributions = build_contributions_df(loadings)

    variance.to_csv(OUT_VARIANCE, index=False, encoding="utf-8-sig")
    loadings.to_csv(OUT_LOADINGS, index=False, encoding="utf-8-sig")
    contributions.to_csv(OUT_CONTRIBUTIONS, index=False, encoding="utf-8-sig")

    joblib.dump(pca, OUT_MODEL)

    thresholds = {
        "n_components_70pct": int(variance.loc[variance["cumulative_variance_pct"] >= 70, "component_number"].iloc[0]),
        "n_components_80pct": int(variance.loc[variance["cumulative_variance_pct"] >= 80, "component_number"].iloc[0]),
        "n_components_85pct": int(variance.loc[variance["cumulative_variance_pct"] >= 85, "component_number"].iloc[0]),
        "n_components_90pct": int(variance.loc[variance["cumulative_variance_pct"] >= 90, "component_number"].iloc[0]),
        "n_components_95pct": int(variance.loc[variance["cumulative_variance_pct"] >= 95, "component_number"].iloc[0]),
    }

    print("\nSugerencia de componentes por varianza acumulada:")
    for k, v in thresholds.items():
        print(f"- {k}: {v}")

    print("\nPrimeros 10 componentes:")
    print(
        variance.head(10)[
            [
                "component",
                "explained_variance_pct",
                "cumulative_variance_pct",
                "eigenvalue",
            ]
        ].to_string(index=False)
    )

    print("\nArchivos generados:")
    print(f"- {OUT_VARIANCE}")
    print(f"- {OUT_LOADINGS}")
    print(f"- {OUT_CONTRIBUTIONS}")
    print(f"- {OUT_MODEL}")

    print(f"\nFilas usadas para PCA: {total_rows:,}")
    print(f"Componentes generados: {N_COMPONENTS:,}")

    print("\nProceso terminado.")


if __name__ == "__main__":
    main()