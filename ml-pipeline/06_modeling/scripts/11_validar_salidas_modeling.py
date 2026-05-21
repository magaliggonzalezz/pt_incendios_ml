# -*- coding: utf-8 -*-
"""
Modeling 11 | Validación general de salidas de Modeling

Este script valida las salidas generadas durante Modeling para el flujo seleccionado.

Hace lo siguiente:
- Verifica existencia de datasets, reports, results y models.
- Valida dimensiones principales.
- Valida consistencia entre IDs, matriz escalada, PCA, SOM y clusters.
- Valida que KMeans tenga 9 clusters propagados a todas las observaciones.
- Valida que HDBSCAN tenga etiquetas propagadas a todas las observaciones.
- Genera un reporte CSV de validación.
"""

from pathlib import Path
import json
import pandas as pd
import numpy as np


# ============================================================
# CONFIGURACIÓN
# ============================================================

BASE_DIR = Path(r"C:\Users\Hp\OneDrive\Documentos\PT_Analisis")

FLUJO = "entidad_dia"

EXPECTED_ROWS = 292_146
EXPECTED_SCALED_FEATURES = 97
EXPECTED_PCS_SELECTED = 18
EXPECTED_KMEANS_CLUSTERS = 9

OUT_REPORTS = BASE_DIR / "06_modeling" / "reports"
OUT_REPORTS.mkdir(parents=True, exist_ok=True)

OUT_VALIDATION = OUT_REPORTS / f"modeling_11_validacion_salidas_{FLUJO}.csv"


# ============================================================
# RUTAS
# ============================================================

PATHS = {
    # Datasets
    "base": BASE_DIR / "06_modeling" / "datasets" / FLUJO / f"modeling_{FLUJO}_base.csv",
    "ids": BASE_DIR / "06_modeling" / "datasets" / FLUJO / f"modeling_{FLUJO}_ids.csv",
    "scaled": BASE_DIR / "06_modeling" / "datasets" / FLUJO / f"modeling_{FLUJO}_scaled.csv",
    "pca_view": BASE_DIR / "06_modeling" / "datasets" / FLUJO / f"modeling_{FLUJO}_pca_clustering_view.csv",

    # Reports
    "diag": BASE_DIR / "06_modeling" / "reports" / f"modeling_01_diagnostico_{FLUJO}.csv",
    "imputacion": BASE_DIR / "06_modeling" / "reports" / f"modeling_03_imputacion_{FLUJO}.csv",
    "features": BASE_DIR / "06_modeling" / "reports" / f"modeling_03_features_{FLUJO}.csv",
    "pca_selected_components": BASE_DIR / "06_modeling" / "reports" / f"modeling_05_componentes_pca_seleccionados_{FLUJO}.csv",
    "cluster_profile_report": BASE_DIR / "06_modeling" / "reports" / f"modeling_08_resumen_perfil_clusters_{FLUJO}.csv",
    "comparison": BASE_DIR / "06_modeling" / "reports" / f"modeling_10_comparacion_configuraciones_{FLUJO}.csv",
    "decision": BASE_DIR / "06_modeling" / "reports" / f"modeling_10_decision_modelo_candidato_{FLUJO}.json",

    # PCA
    "pca_scores": BASE_DIR / "06_modeling" / "results" / FLUJO / "pca" / "pca_scores.csv",
    "pca_variance": BASE_DIR / "06_modeling" / "results" / FLUJO / "pca" / "pca_explained_variance.csv",
    "pca_loadings": BASE_DIR / "06_modeling" / "results" / FLUJO / "pca" / "pca_loadings.csv",
    "pca_feature_contributions": BASE_DIR / "06_modeling" / "results" / FLUJO / "pca" / "pca_feature_contributions.csv",

    # SOM seleccionado
    "som_bmu": BASE_DIR / "06_modeling" / "results" / FLUJO / "som_sigma2_full" / "som_bmu_assignments.csv",
    "som_weights": BASE_DIR / "06_modeling" / "results" / FLUJO / "som_sigma2_full" / "som_weights.csv",
    "som_activation": BASE_DIR / "06_modeling" / "results" / FLUJO / "som_sigma2_full" / "som_activation_map.csv",
    "som_u_matrix": BASE_DIR / "06_modeling" / "results" / FLUJO / "som_sigma2_full" / "som_u_matrix.csv",
    "som_metrics": BASE_DIR / "06_modeling" / "results" / FLUJO / "som_sigma2_full" / "som_metrics.json",

    # KMeans
    "kmeans_comparison": BASE_DIR / "06_modeling" / "results" / FLUJO / "som_kmeans" / "som_kmeans_comparison.csv",
    "kmeans_node_clusters": BASE_DIR / "06_modeling" / "results" / FLUJO / "som_kmeans" / "som_kmeans_node_clusters.csv",
    "kmeans_observation_clusters": BASE_DIR / "06_modeling" / "results" / FLUJO / "som_kmeans" / "som_kmeans_observation_clusters.csv",
    "kmeans_selected_metrics": BASE_DIR / "06_modeling" / "results" / FLUJO / "som_kmeans" / "som_kmeans_selected_metrics.json",
    "kmeans_cluster_profile": BASE_DIR / "06_modeling" / "results" / FLUJO / "som_kmeans" / "som_kmeans_cluster_profile.csv",
    "kmeans_feature_profile": BASE_DIR / "06_modeling" / "results" / FLUJO / "som_kmeans" / "som_kmeans_feature_profile.csv",
    "kmeans_entity_distribution": BASE_DIR / "06_modeling" / "results" / FLUJO / "som_kmeans" / "som_kmeans_cluster_entity_distribution.csv",
    "kmeans_month_distribution": BASE_DIR / "06_modeling" / "results" / FLUJO / "som_kmeans" / "som_kmeans_cluster_month_distribution.csv",

    # HDBSCAN
    "hdbscan_comparison": BASE_DIR / "06_modeling" / "results" / FLUJO / "som_hdbscan" / "som_hdbscan_comparison.csv",
    "hdbscan_node_clusters": BASE_DIR / "06_modeling" / "results" / FLUJO / "som_hdbscan" / "som_hdbscan_node_clusters.csv",
    "hdbscan_observation_clusters": BASE_DIR / "06_modeling" / "results" / FLUJO / "som_hdbscan" / "som_hdbscan_observation_clusters.csv",
    "hdbscan_selected_metrics": BASE_DIR / "06_modeling" / "results" / FLUJO / "som_hdbscan" / "som_hdbscan_selected_metrics.json",

    # Models
    "scaler_model": BASE_DIR / "06_modeling" / "models" / FLUJO / "preprocessing" / "standard_scaler.joblib",
    "pca_model": BASE_DIR / "06_modeling" / "models" / FLUJO / "pca" / "pca_model.joblib",
    "som_model": BASE_DIR / "06_modeling" / "models" / FLUJO / "som_sigma2_full" / "som_model.joblib",
    "som_scaler": BASE_DIR / "06_modeling" / "models" / FLUJO / "som_sigma2_full" / "som_minmax_scaler.joblib",
    "kmeans_model": BASE_DIR / "06_modeling" / "models" / FLUJO / "som_kmeans" / "som_kmeans_model.joblib",
    "hdbscan_model": BASE_DIR / "06_modeling" / "models" / FLUJO / "som_hdbscan" / "som_hdbscan_model.joblib",
}


# ============================================================
# FUNCIONES AUXILIARES
# ============================================================

def add_result(rows, validacion, estado, detalle="", valor_observado=None, valor_esperado=None):
    rows.append({
        "validacion": validacion,
        "estado": estado,
        "detalle": detalle,
        "valor_observado": valor_observado,
        "valor_esperado": valor_esperado,
    })


def check_file_exists(rows, name, path):
    if path.exists():
        add_result(rows, f"existe_{name}", "OK", str(path))
    else:
        add_result(rows, f"existe_{name}", "ERROR", str(path))


def read_csv(path):
    return pd.read_csv(path, encoding="utf-8-sig", low_memory=False)


def read_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def validate_rows(rows, name, df, expected_rows):
    observed = len(df)
    estado = "OK" if observed == expected_rows else "ERROR"
    add_result(
        rows,
        f"filas_{name}",
        estado,
        "",
        observed,
        expected_rows,
    )


def validate_no_nulls(rows, name, df, cols=None):
    if cols is None:
        nulls = int(df.isna().sum().sum())
    else:
        nulls = int(df[cols].isna().sum().sum())

    estado = "OK" if nulls == 0 else "ERROR"
    add_result(rows, f"nulos_{name}", estado, "", nulls, 0)


def validate_required_columns(rows, name, df, required_cols):
    missing = [c for c in required_cols if c not in df.columns]
    estado = "OK" if not missing else "ERROR"
    add_result(rows, f"columnas_requeridas_{name}", estado, "; ".join(missing))


def get_pc_cols(df):
    pc_cols = [c for c in df.columns if c.startswith("PC")]
    return sorted(pc_cols, key=lambda x: int(x.replace("PC", "")))


# ============================================================
# PIPELINE PRINCIPAL
# ============================================================

def main():
    print("\nModeling 11 | Validación general de salidas")
    print(f"Flujo: {FLUJO}")

    rows = []

    print("\nVerificando existencia de archivos...")
    for name, path in PATHS.items():
        check_file_exists(rows, name, path)

    missing = [name for name, path in PATHS.items() if not path.exists()]

    if missing:
        df_validation = pd.DataFrame(rows)
        df_validation.to_csv(OUT_VALIDATION, index=False, encoding="utf-8-sig")

        print("\nERROR: faltan archivos requeridos:")
        for m in missing:
            print(f"- {m}: {PATHS[m]}")

        print(f"\nReporte generado:")
        print(f"- {OUT_VALIDATION}")
        return

    print("Leyendo archivos principales...")

    base = read_csv(PATHS["base"])
    ids = read_csv(PATHS["ids"])
    scaled = read_csv(PATHS["scaled"])
    pca_view = read_csv(PATHS["pca_view"])
    pca_scores = read_csv(PATHS["pca_scores"])
    pca_variance = read_csv(PATHS["pca_variance"])
    som_bmu = read_csv(PATHS["som_bmu"])
    som_weights = read_csv(PATHS["som_weights"])
    som_activation = read_csv(PATHS["som_activation"])
    kmeans_obs = read_csv(PATHS["kmeans_observation_clusters"])
    kmeans_nodes = read_csv(PATHS["kmeans_node_clusters"])
    kmeans_comparison = read_csv(PATHS["kmeans_comparison"])
    hdbscan_obs = read_csv(PATHS["hdbscan_observation_clusters"])
    hdbscan_nodes = read_csv(PATHS["hdbscan_node_clusters"])

    som_metrics = read_json(PATHS["som_metrics"])
    kmeans_selected = read_json(PATHS["kmeans_selected_metrics"])
    hdbscan_selected = read_json(PATHS["hdbscan_selected_metrics"])
    decision = read_json(PATHS["decision"])

    print("Validando dimensiones principales...")

    for name, df in [
        ("base", base),
        ("ids", ids),
        ("scaled", scaled),
        ("pca_view", pca_view),
        ("pca_scores", pca_scores),
        ("som_bmu", som_bmu),
        ("kmeans_observation_clusters", kmeans_obs),
        ("hdbscan_observation_clusters", hdbscan_obs),
    ]:
        validate_rows(rows, name, df, EXPECTED_ROWS)

    observed_scaled_cols = len(scaled.columns)
    add_result(
        rows,
        "columnas_scaled",
        "OK" if observed_scaled_cols == EXPECTED_SCALED_FEATURES else "ERROR",
        "",
        observed_scaled_cols,
        EXPECTED_SCALED_FEATURES,
    )

    pc_cols_view = get_pc_cols(pca_view)
    observed_pcs_view = len(pc_cols_view)

    add_result(
        rows,
        "componentes_pca_view",
        "OK" if observed_pcs_view == EXPECTED_PCS_SELECTED else "ERROR",
        "",
        observed_pcs_view,
        EXPECTED_PCS_SELECTED,
    )

    print("Validando nulos y consistencia PCA...")

    validate_no_nulls(rows, "scaled", scaled)
    validate_no_nulls(rows, "pca_view_pcs", pca_view, pc_cols_view)

    selected_pca_row = pca_variance[pca_variance["component_number"] == EXPECTED_PCS_SELECTED]

    if selected_pca_row.empty:
        add_result(rows, "pca_varianza_18pc", "ERROR", "No existe PC18")
    else:
        variance_18 = float(selected_pca_row["cumulative_variance_pct"].iloc[0])
        add_result(
            rows,
            "pca_varianza_18pc",
            "OK" if variance_18 >= 90 else "WARNING",
            "",
            round(variance_18, 4),
            ">= 90",
        )

    print("Validando SOM seleccionado...")

    add_result(
        rows,
        "som_config_sigma",
        "OK" if float(som_metrics.get("sigma")) == 2.0 else "ERROR",
        "",
        som_metrics.get("sigma"),
        2.0,
    )

    add_result(
        rows,
        "som_train_full",
        "OK" if int(som_metrics.get("train_sample_size")) == EXPECTED_ROWS else "ERROR",
        "",
        som_metrics.get("train_sample_size"),
        EXPECTED_ROWS,
    )

    add_result(
        rows,
        "som_metrics_full",
        "OK" if int(som_metrics.get("metrics_sample_size")) == EXPECTED_ROWS else "ERROR",
        "",
        som_metrics.get("metrics_sample_size"),
        EXPECTED_ROWS,
    )

    observed_som_nodes = len(som_weights)
    add_result(
        rows,
        "som_total_nodes",
        "OK" if observed_som_nodes == 900 else "ERROR",
        "",
        observed_som_nodes,
        900,
    )

    occupied_nodes = int(som_activation["activation_count"].gt(0).sum())
    expected_occupied = int(som_metrics.get("occupied_nodes"))

    add_result(
        rows,
        "som_occupied_nodes_consistency",
        "OK" if occupied_nodes == expected_occupied else "ERROR",
        "",
        occupied_nodes,
        expected_occupied,
    )

    print("Validando KMeans...")

    validate_required_columns(
        rows,
        "kmeans_observation_clusters",
        kmeans_obs,
        ["som_node_id", "cluster_kmeans"],
    )

    missing_kmeans = int(kmeans_obs["cluster_kmeans"].isna().sum())
    add_result(
        rows,
        "kmeans_observaciones_sin_cluster",
        "OK" if missing_kmeans == 0 else "ERROR",
        "",
        missing_kmeans,
        0,
    )

    n_kmeans_clusters = int(kmeans_obs["cluster_kmeans"].nunique())

    add_result(
        rows,
        "kmeans_n_clusters",
        "OK" if n_kmeans_clusters == EXPECTED_KMEANS_CLUSTERS else "ERROR",
        "",
        n_kmeans_clusters,
        EXPECTED_KMEANS_CLUSTERS,
    )

    selected_k = int(kmeans_selected.get("selected_k", kmeans_selected.get("k")))

    add_result(
        rows,
        "kmeans_selected_k",
        "OK" if selected_k == EXPECTED_KMEANS_CLUSTERS else "ERROR",
        "",
        selected_k,
        EXPECTED_KMEANS_CLUSTERS,
    )

    if "k" in kmeans_comparison.columns:
        add_result(
            rows,
            "kmeans_comparison_incluye_k9",
            "OK" if EXPECTED_KMEANS_CLUSTERS in set(kmeans_comparison["k"].astype(int)) else "ERROR",
            "",
        )

    print("Validando HDBSCAN...")

    validate_required_columns(
        rows,
        "hdbscan_observation_clusters",
        hdbscan_obs,
        ["som_node_id", "cluster_hdbscan"],
    )

    missing_hdbscan = int(hdbscan_obs["cluster_hdbscan"].isna().sum())
    add_result(
        rows,
        "hdbscan_observaciones_sin_etiqueta",
        "OK" if missing_hdbscan == 0 else "ERROR",
        "",
        missing_hdbscan,
        0,
    )

    n_hdbscan_labels = int(hdbscan_obs["cluster_hdbscan"].nunique())

    add_result(
        rows,
        "hdbscan_n_etiquetas",
        "OK" if n_hdbscan_labels >= 2 else "ERROR",
        "",
        n_hdbscan_labels,
        ">= 2",
    )

    add_result(
        rows,
        "hdbscan_selected_clusters",
        "OK" if int(hdbscan_selected.get("n_clusters")) >= 2 else "ERROR",
        "",
        hdbscan_selected.get("n_clusters"),
        ">= 2",
    )

    print("Validando decisión final...")

    modelo_candidato = decision.get("modelo_candidato_principal", "")

    add_result(
        rows,
        "decision_modelo_candidato",
        "OK" if "KMeans_k9" in modelo_candidato else "ERROR",
        "",
        modelo_candidato,
        "contiene KMeans_k9",
    )

    add_result(
        rows,
        "decision_nota_crisp_dm",
        "OK" if "no constituyen Evaluation formal" in decision.get("nota_crisp_dm", "") else "WARNING",
        "",
    )

    df_validation = pd.DataFrame(rows)
    df_validation.to_csv(OUT_VALIDATION, index=False, encoding="utf-8-sig")

    n_total = len(df_validation)
    n_errors = int((df_validation["estado"] == "ERROR").sum())
    n_warnings = int((df_validation["estado"] == "WARNING").sum())
    n_ok = int((df_validation["estado"] == "OK").sum())

    print("\nArchivo generado:")
    print(f"- {OUT_VALIDATION}")

    print("\nResumen:")
    print(f"- Validaciones totales: {n_total}")
    print(f"- OK: {n_ok}")
    print(f"- Warnings: {n_warnings}")
    print(f"- Errores: {n_errors}")

    if n_errors == 0:
        print("\nModeling entidad-día queda validado.")
    else:
        print("\nHay errores por corregir antes de cerrar Modeling entidad-día.")

    print("\nProceso terminado.")


if __name__ == "__main__":
    main()