# -*- coding: utf-8 -*-
"""
Modeling 05 | Construcción de vista PCA para clustering

Este script construye una vista reducida para SOM/clustering usando
los componentes principales seleccionados.

Hace lo siguiente:
- Lee los scores PCA generados en Modeling 04.
- Selecciona IDs, columnas de perfilado/contraste y PCs seleccionadas.
- Valida que existan los componentes requeridos.
- Genera una vista PCA reducida para los siguientes modelos.
- Genera un reporte de componentes seleccionados.
"""

from pathlib import Path
import pandas as pd


# ============================================================
# CONFIGURACIÓN
# ============================================================

BASE_DIR = Path(r"C:\Users\Hp\OneDrive\Documentos\PT_Analisis")

FLUJO = "entidad_dia"

N_COMPONENTS_SELECTED = 18

INPUT_PCA_SCORES = BASE_DIR / "06_modeling" / "results" / FLUJO / "pca" / "pca_scores.csv"
INPUT_PCA_VARIANCE = BASE_DIR / "06_modeling" / "results" / FLUJO / "pca" / "pca_explained_variance.csv"
INPUT_DIAG = BASE_DIR / "06_modeling" / "reports" / f"modeling_01_diagnostico_{FLUJO}.csv"

OUT_DATASETS = BASE_DIR / "06_modeling" / "datasets" / FLUJO
OUT_REPORTS = BASE_DIR / "06_modeling" / "reports"

OUT_DATASETS.mkdir(parents=True, exist_ok=True)
OUT_REPORTS.mkdir(parents=True, exist_ok=True)

OUT_VIEW = OUT_DATASETS / f"modeling_{FLUJO}_pca_clustering_view.csv"
OUT_SELECTED_COMPONENTS = OUT_REPORTS / f"modeling_05_componentes_pca_seleccionados_{FLUJO}.csv"


# ============================================================
# COLUMNAS ID POR FLUJO
# ============================================================

ID_COLS_BY_FLOW = {
    "entidad_dia": [
        "cve_ent",
        "nom_ent",
        "fecha",
    ],
    "municipio_dia": [
        "cvegeo",
        "cve_ent",
        "cve_mun",
        "nom_ent",
        "nom_mun",
        "fecha",
    ],
}


# ============================================================
# FUNCIONES AUXILIARES
# ============================================================

def ensure_columns(df: pd.DataFrame, required_cols: list[str], context: str) -> None:
    missing = [c for c in required_cols if c not in df.columns]
    if missing:
        raise ValueError(f"Faltan columnas en {context}: {missing}")


def get_columns_from_diagnostic(df_diag: pd.DataFrame, uso: str) -> list[str]:
    return (
        df_diag.loc[df_diag["uso_sugerido"] == uso, "columna"]
        .dropna()
        .astype(str)
        .tolist()
    )


def build_pc_cols(n_components: int) -> list[str]:
    return [f"PC{i}" for i in range(1, n_components + 1)]


# ============================================================
# PIPELINE PRINCIPAL
# ============================================================

def main():
    print("\nModeling 05 | Construcción de vista PCA para clustering")
    print(f"Flujo: {FLUJO}")
    print(f"Componentes seleccionados: {N_COMPONENTS_SELECTED}")

    if not INPUT_PCA_SCORES.exists():
        raise FileNotFoundError(f"No existe pca_scores.csv: {INPUT_PCA_SCORES}")

    if not INPUT_PCA_VARIANCE.exists():
        raise FileNotFoundError(f"No existe pca_explained_variance.csv: {INPUT_PCA_VARIANCE}")

    if not INPUT_DIAG.exists():
        raise FileNotFoundError(f"No existe diagnóstico Modeling 01: {INPUT_DIAG}")

    print(f"\nLeyendo scores PCA:")
    print(f"- {INPUT_PCA_SCORES}")

    df_scores = pd.read_csv(INPUT_PCA_SCORES, encoding="utf-8-sig", low_memory=False)

    print(f"Filas scores: {len(df_scores):,}")
    print(f"Columnas scores: {len(df_scores.columns):,}")

    print(f"\nLeyendo varianza PCA:")
    print(f"- {INPUT_PCA_VARIANCE}")

    df_variance = pd.read_csv(INPUT_PCA_VARIANCE, encoding="utf-8-sig")

    print(f"\nLeyendo diagnóstico:")
    print(f"- {INPUT_DIAG}")

    df_diag = pd.read_csv(INPUT_DIAG, encoding="utf-8-sig")

    id_cols = ID_COLS_BY_FLOW[FLUJO]
    profiling_cols = get_columns_from_diagnostic(df_diag, "perfilado")
    pc_cols = build_pc_cols(N_COMPONENTS_SELECTED)

    required_cols = id_cols + profiling_cols + pc_cols
    ensure_columns(df_scores, required_cols, "pca_scores.csv")

    view = df_scores[required_cols].copy()

    # Validaciones básicas
    if view[id_cols].isna().sum().sum() > 0:
        raise ValueError("La vista PCA contiene nulos en columnas ID.")

    if view[pc_cols].isna().sum().sum() > 0:
        raise ValueError("La vista PCA contiene nulos en componentes principales.")

    duplicated_rows = view.duplicated(subset=id_cols).sum()
    if duplicated_rows > 0:
        raise ValueError(f"La vista PCA contiene {duplicated_rows:,} filas duplicadas por IDs.")

    # Reporte de componentes seleccionados
    ensure_columns(
        df_variance,
        [
            "component",
            "component_number",
            "explained_variance_pct",
            "cumulative_variance_pct",
            "eigenvalue",
        ],
        "pca_explained_variance.csv",
    )

    selected_variance = df_variance[
        df_variance["component_number"] <= N_COMPONENTS_SELECTED
    ].copy()

    cumulative_selected = selected_variance["cumulative_variance_pct"].iloc[-1]

    selected_variance.to_csv(OUT_SELECTED_COMPONENTS, index=False, encoding="utf-8-sig")
    view.to_csv(OUT_VIEW, index=False, encoding="utf-8-sig")

    print(f"\nVarianza acumulada con {N_COMPONENTS_SELECTED} PCs: {cumulative_selected:.4f}%")

    print(f"\nArchivos generados:")
    print(f"- {OUT_VIEW}")
    print(f"- {OUT_SELECTED_COMPONENTS}")

    print(f"\nFilas vista PCA clustering: {len(view):,}")
    print(f"Columnas vista PCA clustering: {len(view.columns):,}")
    print(f"Columnas PC: {len(pc_cols):,}")
    print(f"Columnas perfilado/contraste: {len(profiling_cols):,}")

    print("\nProceso terminado.")


if __name__ == "__main__":
    main()