# -*- coding: utf-8 -*-
"""
Modeling 05 | Construcción de vista PCA para clustering municipio-día

Este script construye la vista PCA reducida para clustering.

Hace lo siguiente:
- Lee la matriz escalada municipio-día por chunks.
- Lee IDs/perfilado por chunks.
- Carga el modelo PCA entrenado.
- Transforma la matriz escalada a scores PCA.
- Conserva solo los componentes seleccionados.
- Guarda una vista compacta para SOM/clustering.
- Genera reporte de componentes PCA seleccionados.
"""

from pathlib import Path
import pandas as pd
import numpy as np
import joblib


# ============================================================
# CONFIGURACIÓN
# ============================================================

BASE_DIR = Path(r"C:\Users\Hp\OneDrive\Documentos\PT_Analisis")

FLUJO = "municipio_dia"

CHUNKSIZE = 300_000
N_COMPONENTS_SELECTED = 28

INPUT_IDS = BASE_DIR / "06_modeling" / "datasets" / FLUJO / f"modeling_{FLUJO}_ids.csv"
INPUT_SCALED = BASE_DIR / "06_modeling" / "datasets" / FLUJO / f"modeling_{FLUJO}_scaled.csv"
INPUT_PCA_MODEL = BASE_DIR / "06_modeling" / "models" / FLUJO / "pca" / "pca_model.joblib"
INPUT_VARIANCE = BASE_DIR / "06_modeling" / "results" / FLUJO / "pca" / "pca_explained_variance.csv"

OUT_DATASETS = BASE_DIR / "06_modeling" / "datasets" / FLUJO
OUT_REPORTS = BASE_DIR / "06_modeling" / "reports"

OUT_DATASETS.mkdir(parents=True, exist_ok=True)
OUT_REPORTS.mkdir(parents=True, exist_ok=True)

OUT_VIEW = OUT_DATASETS / f"modeling_{FLUJO}_pca_clustering_view.csv"
OUT_REPORT = OUT_REPORTS / f"modeling_05_componentes_pca_seleccionados_{FLUJO}.csv"


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


def remove_output_if_exists(path: Path) -> None:
    if path.exists():
        path.unlink()


def read_row_count(path: Path) -> int:
    n = 0
    for chunk in pd.read_csv(
        path,
        encoding="utf-8-sig",
        usecols=[0],
        chunksize=500_000,
        low_memory=False,
    ):
        n += len(chunk)
    return n


# ============================================================
# PIPELINE PRINCIPAL
# ============================================================

def main():
    print("\nModeling 05 | Construcción de vista PCA para clustering")
    print(f"Flujo: {FLUJO}")
    print(f"Componentes seleccionados: {N_COMPONENTS_SELECTED}")

    ensure_file(INPUT_IDS, "IDs/perfilado")
    ensure_file(INPUT_SCALED, "matriz escalada")
    ensure_file(INPUT_PCA_MODEL, "modelo PCA")
    ensure_file(INPUT_VARIANCE, "varianza PCA")

    print("\nValidando conteo de filas...")
    n_ids = read_row_count(INPUT_IDS)
    n_scaled = read_row_count(INPUT_SCALED)

    print(f"- Filas IDs: {n_ids:,}")
    print(f"- Filas scaled: {n_scaled:,}")

    if n_ids != n_scaled:
        raise ValueError(f"IDs y scaled no tienen mismas filas: {n_ids:,} vs {n_scaled:,}")

    print("\nCargando modelo PCA:")
    print(f"- {INPUT_PCA_MODEL}")
    pca = joblib.load(INPUT_PCA_MODEL)

    print("\nLeyendo varianza PCA:")
    print(f"- {INPUT_VARIANCE}")
    variance = pd.read_csv(INPUT_VARIANCE, encoding="utf-8-sig")

    selected_var = variance.loc[
        variance["component_number"] == N_COMPONENTS_SELECTED,
        "cumulative_variance_pct",
    ]

    if selected_var.empty:
        raise ValueError(f"No existe componente {N_COMPONENTS_SELECTED} en varianza PCA.")

    selected_var_pct = float(selected_var.iloc[0])

    print(f"Varianza acumulada con {N_COMPONENTS_SELECTED} PCs: {selected_var_pct:.4f}%")

    report = variance[variance["component_number"] <= N_COMPONENTS_SELECTED].copy()
    report["selected_for_clustering"] = True
    report.to_csv(OUT_REPORT, index=False, encoding="utf-8-sig")

    remove_output_if_exists(OUT_VIEW)

    pc_cols = [f"PC{i}" for i in range(1, N_COMPONENTS_SELECTED + 1)]

    print("\nConstruyendo vista PCA por chunks...")

    total_rows = 0

    ids_iter = pd.read_csv(
        INPUT_IDS,
        encoding="utf-8-sig",
        chunksize=CHUNKSIZE,
        low_memory=False,
    )

    scaled_iter = pd.read_csv(
        INPUT_SCALED,
        encoding="utf-8-sig",
        chunksize=CHUNKSIZE,
        low_memory=False,
    )

    for i, (ids_chunk, scaled_chunk) in enumerate(zip(ids_iter, scaled_iter), start=1):
        if len(ids_chunk) != len(scaled_chunk):
            raise ValueError(
                f"Chunk {i}: IDs y scaled no tienen mismas filas: "
                f"{len(ids_chunk):,} vs {len(scaled_chunk):,}"
            )

        validate_numeric_chunk(scaled_chunk, i)

        X = scaled_chunk.to_numpy(dtype=np.float64)
        scores = pca.transform(X)[:, :N_COMPONENTS_SELECTED]

        scores_df = pd.DataFrame(
            scores,
            columns=pc_cols,
            index=ids_chunk.index,
        )

        out_chunk = pd.concat(
            [
                ids_chunk.reset_index(drop=True),
                scores_df.reset_index(drop=True),
            ],
            axis=1,
        )

        out_chunk.to_csv(
            OUT_VIEW,
            index=False,
            encoding="utf-8-sig",
            mode="a",
            header=not OUT_VIEW.exists(),
            float_format="%.6f",
        )

        total_rows += len(out_chunk)

        print(f"- chunk {i:,}: filas acumuladas {total_rows:,}")

    print("\nArchivos generados:")
    print(f"- {OUT_VIEW}")
    print(f"- {OUT_REPORT}")

    print(f"\nFilas vista PCA clustering: {total_rows:,}")
    print(f"Columnas PC: {N_COMPONENTS_SELECTED}")
    print(f"Varianza acumulada: {selected_var_pct:.4f}%")

    print("\nProceso terminado.")


if __name__ == "__main__":
    main()