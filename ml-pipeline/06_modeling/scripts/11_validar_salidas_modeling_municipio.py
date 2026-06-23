# -*- coding: utf-8 -*-
"""
Modeling 11 | Validación general de salidas municipio-día

Este script valida las salidas principales de Modeling para el flujo municipio-día.

Hace lo siguiente:
- Verifica existencia de archivos esperados.
- Valida dimensiones principales.
- Valida consistencia entre IDs, matriz escalada, vista PCA, BMU y clusters.
- Valida PCA seleccionado.
- Valida SOM seleccionado.
- Valida KMeans como candidato principal.
- Valida HDBSCAN como contraste.
- Valida decisión final de Modeling 10.
- Genera reporte CSV de validación.
"""

from pathlib import Path
import json
import pandas as pd
import numpy as np


# ============================================================
# CONFIGURACIÓN
# ============================================================

BASE_DIR = Path(r"C:\Users\Hp\OneDrive\Documentos\PT_Analisis")

FLUJO = "municipio_dia"
SOM_CONFIG = "som_50x50_sigma3_sample"

EXPECTED_ROWS = 11_154_221
EXPECTED_FEATURES = 65
EXPECTED_PCA_COMPONENTS = 28
EXPECTED_KMEANS_K = 11

CHUNKSIZE = 300_000

DIR_DATASETS = BASE_DIR / "06_modeling" / "datasets" / FLUJO
DIR_RESULTS = BASE_DIR / "06_modeling" / "results" / FLUJO
DIR_REPORTS = BASE_DIR / "06_modeling" / "reports"
DIR_MODELS = BASE_DIR / "06_modeling" / "models" / FLUJO

FILES = {
    "diagnostico": DIR_REPORTS / f"modeling_01_diagnostico_{FLUJO}.csv",
    "base": DIR_DATASETS / f"modeling_{FLUJO}_base.csv",
    "ids": DIR_DATASETS / f"modeling_{FLUJO}_ids.csv",
    "scaled": DIR_DATASETS / f"modeling_{FLUJO}_scaled.csv",
    "imputacion": DIR_REPORTS / f"modeling_03_imputacion_{FLUJO}.csv",
    "features": DIR_REPORTS / f"modeling_03_features_{FLUJO}.csv",
    "pca_variance": DIR_RESULTS / "pca" / "pca_explained_variance.csv",
    "pca_loadings": DIR_RESULTS / "pca" / "pca_loadings.csv",
    "pca_contrib": DIR_RESULTS / "pca" / "pca_feature_contributions.csv",
    "pca_model": DIR_MODELS / "pca" / "pca_model.joblib",
    "pca_view": DIR_DATASETS / f"modeling_{FLUJO}_pca_clustering_view.csv",
    "pca_selected": DIR_REPORTS / f"modeling_05_componentes_pca_seleccionados_{FLUJO}.csv",
    "som_metrics": DIR_RESULTS / SOM_CONFIG / "som_metrics.json",
    "som_weights": DIR_RESULTS / SOM_CONFIG / "som_weights.csv",
    "som_activation": DIR_RESULTS / SOM_CONFIG / "som_activation_map.csv",
    "som_bmu": DIR_RESULTS / SOM_CONFIG / "som_bmu_assignments.csv",
    "som_umatrix": DIR_RESULTS / SOM_CONFIG / "som_u_matrix.csv",
    "som_model": DIR_MODELS / SOM_CONFIG / "som_model.joblib",
    "som_scaler": DIR_MODELS / SOM_CONFIG / "som_minmax_scaler.joblib",
    "kmeans_comparison": DIR_RESULTS / "som_kmeans" / "som_kmeans_comparison.csv",
    "kmeans_nodes": DIR_RESULTS / "som_kmeans" / "som_kmeans_node_clusters.csv",
    "kmeans_obs": DIR_RESULTS / "som_kmeans" / "som_kmeans_observation_clusters.csv",
    "kmeans_selected": DIR_RESULTS / "som_kmeans" / "som_kmeans_selected_metrics.json",
    "kmeans_model": DIR_MODELS / "som_kmeans" / "som_kmeans_model.joblib",
    "kmeans_profile": DIR_RESULTS / "som_kmeans" / "som_kmeans_cluster_profile.csv",
    "kmeans_feature_profile": DIR_RESULTS / "som_kmeans" / "som_kmeans_feature_profile.csv",
    "kmeans_entity_dist": DIR_RESULTS / "som_kmeans" / "som_kmeans_cluster_entity_distribution.csv",
    "kmeans_month_dist": DIR_RESULTS / "som_kmeans" / "som_kmeans_cluster_month_distribution.csv",
    "kmeans_summary": DIR_REPORTS / f"modeling_08_resumen_perfil_clusters_{FLUJO}.csv",
    "hdbscan_comparison": DIR_RESULTS / "som_hdbscan" / "som_hdbscan_comparison.csv",
    "hdbscan_nodes": DIR_RESULTS / "som_hdbscan" / "som_hdbscan_node_clusters.csv",
    "hdbscan_obs": DIR_RESULTS / "som_hdbscan" / "som_hdbscan_observation_clusters.csv",
    "hdbscan_selected": DIR_RESULTS / "som_hdbscan" / "som_hdbscan_selected_metrics.json",
    "hdbscan_model": DIR_MODELS / "som_hdbscan" / "som_hdbscan_model.joblib",
    "comparison_10": DIR_REPORTS / f"modeling_10_comparacion_configuraciones_{FLUJO}.csv",
    "decision_10": DIR_REPORTS / f"modeling_10_decision_modelo_candidato_{FLUJO}.json",
}

OUT_VALIDATION = DIR_REPORTS / f"modeling_11_validacion_salidas_{FLUJO}.csv"


# ============================================================
# FUNCIONES
# ============================================================

def read_json(path: Path) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def add_result(rows, validacion, estado, detalle):
    rows.append({
        "validacion": validacion,
        "estado": estado,
        "detalle": detalle,
    })


def count_rows_csv(path: Path) -> int:
    total = 0
    for chunk in pd.read_csv(path, encoding="utf-8-sig", chunksize=CHUNKSIZE, low_memory=False):
        total += len(chunk)
    return total


def count_nulls_csv(path: Path, usecols=None) -> int:
    total_nulls = 0
    for chunk in pd.read_csv(path, encoding="utf-8-sig", usecols=usecols, chunksize=CHUNKSIZE, low_memory=False):
        total_nulls += int(chunk.isna().sum().sum())
    return total_nulls


def get_header(path: Path) -> list[str]:
    return pd.read_csv(path, encoding="utf-8-sig", nrows=0).columns.tolist()


def get_pc_cols(columns: list[str]) -> list[str]:
    return sorted(
        [c for c in columns if c.startswith("PC")],
        key=lambda x: int(x.replace("PC", ""))
    )


# ============================================================
# PIPELINE
# ============================================================

def main():
    print("\nModeling 11 | Validación general de salidas")
    print(f"Flujo: {FLUJO}")

    rows = []

    print("\nVerificando existencia de archivos...")

    for name, path in FILES.items():
        if path.exists():
            add_result(rows, f"existe_{name}", "OK", str(path))
        else:
            add_result(rows, f"existe_{name}", "ERROR", f"No existe: {path}")

    if any(r["estado"] == "ERROR" for r in rows):
        pd.DataFrame(rows).to_csv(OUT_VALIDATION, index=False, encoding="utf-8-sig")
        print("\nHay archivos faltantes. Revisa el reporte.")
        print(f"- {OUT_VALIDATION}")
        return

    print("Leyendo archivos principales...")

    diag = pd.read_csv(FILES["diagnostico"], encoding="utf-8-sig")
    pca_var = pd.read_csv(FILES["pca_variance"], encoding="utf-8-sig")
    pca_selected = pd.read_csv(FILES["pca_selected"], encoding="utf-8-sig")
    som_metrics = read_json(FILES["som_metrics"])
    kmeans_selected = read_json(FILES["kmeans_selected"])
    hdbscan_selected = read_json(FILES["hdbscan_selected"])
    decision_10 = read_json(FILES["decision_10"])
    comparison_10 = pd.read_csv(FILES["comparison_10"], encoding="utf-8-sig")
    kmeans_summary = pd.read_csv(FILES["kmeans_summary"], encoding="utf-8-sig")

    print("Validando diagnóstico...")

    n_candidate = int((diag["uso_sugerido"] == "candidata_modelado").sum())
    n_profile = int((diag["uso_sugerido"] == "perfilado").sum())
    n_review = int((diag["uso_sugerido"] == "revisar").sum())

    add_result(
        rows,
        "diagnostico_candidatas",
        "OK" if n_candidate == EXPECTED_FEATURES else "ERROR",
        f"candidatas={n_candidate}, esperado={EXPECTED_FEATURES}",
    )

    add_result(
        rows,
        "diagnostico_perfilado",
        "OK" if n_profile == 6 else "ERROR",
        f"perfilado={n_profile}, esperado=6",
    )

    add_result(
        rows,
        "diagnostico_sin_revisar",
        "OK" if n_review == 0 else "ERROR",
        f"columnas revisar={n_review}",
    )

    print("Validando dimensiones principales...")

    base_header = get_header(FILES["base"])
    ids_header = get_header(FILES["ids"])
    scaled_header = get_header(FILES["scaled"])
    pca_view_header = get_header(FILES["pca_view"])

    base_rows = count_rows_csv(FILES["base"])
    ids_rows = count_rows_csv(FILES["ids"])
    scaled_rows = count_rows_csv(FILES["scaled"])
    pca_view_rows = count_rows_csv(FILES["pca_view"])

    for label, n in [
        ("base_rows", base_rows),
        ("ids_rows", ids_rows),
        ("scaled_rows", scaled_rows),
        ("pca_view_rows", pca_view_rows),
    ]:
        add_result(
            rows,
            label,
            "OK" if n == EXPECTED_ROWS else "ERROR",
            f"filas={n:,}, esperado={EXPECTED_ROWS:,}",
        )

    add_result(
        rows,
        "scaled_features",
        "OK" if len(scaled_header) == EXPECTED_FEATURES else "ERROR",
        f"features_scaled={len(scaled_header)}, esperado={EXPECTED_FEATURES}",
    )

    pc_cols_view = get_pc_cols(pca_view_header)

    add_result(
        rows,
        "pca_view_componentes",
        "OK" if len(pc_cols_view) == EXPECTED_PCA_COMPONENTS else "ERROR",
        f"PCs en vista={len(pc_cols_view)}, esperado={EXPECTED_PCA_COMPONENTS}",
    )

    print("Validando nulos y consistencia PCA...")

    scaled_nulls = count_nulls_csv(FILES["scaled"])

    add_result(
        rows,
        "scaled_sin_nulos",
        "OK" if scaled_nulls == 0 else "ERROR",
        f"nulos en scaled={scaled_nulls:,}",
    )

    if "component" in pca_var.columns and "cumulative_variance_pct" in pca_var.columns:
        pca_var["component_number"] = (
            pca_var["component"].astype(str).str.replace("PC", "", regex=False).astype(int)
        )
        pca_28 = pca_var[pca_var["component_number"] == EXPECTED_PCA_COMPONENTS]
        if not pca_28.empty:
            var_28 = float(pca_28.iloc[0]["cumulative_variance_pct"])
            add_result(
                rows,
                "pca_28_varianza",
                "OK" if var_28 >= 90 else "ERROR",
                f"varianza acumulada PC28={var_28:.4f}%",
            )
        else:
            add_result(rows, "pca_28_varianza", "ERROR", "No se encontró PC28")
    else:
        add_result(rows, "pca_columnas_varianza", "ERROR", "Faltan columnas PCA")

    print("Validando SOM seleccionado...")

    som_checks = {
        "som_x": som_metrics.get("som_x") == 50,
        "som_y": som_metrics.get("som_y") == 50,
        "som_total_nodes": som_metrics.get("total_nodes") == 2500,
        "som_sigma": float(som_metrics.get("sigma")) == 3.0,
        "som_rows_total": som_metrics.get("n_rows_total") == EXPECTED_ROWS,
        "som_occupied_nodes_alto": som_metrics.get("occupied_nodes_pct", 0) >= 0.95,
        "som_quantization_error_valido": som_metrics.get("quantization_error", 999) < 0.2,
        "som_topographic_error_valido": som_metrics.get("topographic_error", 999) < 0.2,
    }

    for check, ok in som_checks.items():
        add_result(rows, check, "OK" if ok else "ERROR", str(som_metrics))

    som_bmu_rows = count_rows_csv(FILES["som_bmu"])
    add_result(
        rows,
        "som_bmu_rows",
        "OK" if som_bmu_rows == EXPECTED_ROWS else "ERROR",
        f"filas BMU={som_bmu_rows:,}",
    )

    print("Validando KMeans...")

    kmeans_obs_rows = count_rows_csv(FILES["kmeans_obs"])

    add_result(
        rows,
        "kmeans_obs_rows",
        "OK" if kmeans_obs_rows == EXPECTED_ROWS else "ERROR",
        f"filas KMeans obs={kmeans_obs_rows:,}",
    )

    add_result(
        rows,
        "kmeans_selected_k",
        "OK" if int(kmeans_selected.get("selected_k")) == EXPECTED_KMEANS_K else "ERROR",
        f"k={kmeans_selected.get('selected_k')}, esperado={EXPECTED_KMEANS_K}",
    )

    add_result(
        rows,
        "kmeans_clusters_summary",
        "OK" if kmeans_summary["cluster_kmeans"].nunique() == EXPECTED_KMEANS_K else "ERROR",
        f"clusters resumen={kmeans_summary['cluster_kmeans'].nunique()}",
    )

    for col in ["has_conafor_rate", "has_firms_rate", "has_smn_rate"]:
        add_result(
            rows,
            f"kmeans_summary_{col}",
            "OK" if col in kmeans_summary.columns else "ERROR",
            f"columna {col} presente={col in kmeans_summary.columns}",
        )

    print("Validando HDBSCAN...")

    hdbscan_obs_rows = count_rows_csv(FILES["hdbscan_obs"])

    add_result(
        rows,
        "hdbscan_obs_rows",
        "OK" if hdbscan_obs_rows == EXPECTED_ROWS else "ERROR",
        f"filas HDBSCAN obs={hdbscan_obs_rows:,}",
    )

    add_result(
        rows,
        "hdbscan_contraste_clusters",
        "OK" if int(hdbscan_selected.get("n_clusters")) >= 2 else "ERROR",
        f"clusters HDBSCAN={hdbscan_selected.get('n_clusters')}",
    )

    add_result(
        rows,
        "hdbscan_ruido_registrado",
        "OK" if float(hdbscan_selected.get("noise_observations_pct")) >= 0 else "ERROR",
        f"noise_pct={hdbscan_selected.get('noise_observations_pct')}",
    )

    print("Validando decisión final...")

    add_result(
        rows,
        "decision_modelo_principal",
        "OK" if decision_10.get("modelo_candidato_principal") == "PCA + SOM + KMeans" else "ERROR",
        f"modelo={decision_10.get('modelo_candidato_principal')}",
    )

    add_result(
        rows,
        "decision_kmeans_k",
        "OK" if int(decision_10.get("kmeans_k")) == EXPECTED_KMEANS_K else "ERROR",
        f"kmeans_k={decision_10.get('kmeans_k')}",
    )

    add_result(
        rows,
        "comparison_10_modelos",
        "OK" if len(comparison_10) >= 2 else "ERROR",
        f"filas comparación={len(comparison_10)}",
    )

    validation = pd.DataFrame(rows)
    validation.to_csv(OUT_VALIDATION, index=False, encoding="utf-8-sig")

    total = len(validation)
    n_ok = int((validation["estado"] == "OK").sum())
    n_warn = int((validation["estado"] == "WARNING").sum())
    n_error = int((validation["estado"] == "ERROR").sum())

    print("\nArchivo generado:")
    print(f"- {OUT_VALIDATION}")

    print("\nResumen:")
    print(f"- Validaciones totales: {total}")
    print(f"- OK: {n_ok}")
    print(f"- Warnings: {n_warn}")
    print(f"- Errores: {n_error}")

    if n_error == 0:
        print("\nModeling municipio-día queda validado.")
    else:
        print("\nHay errores pendientes en Modeling municipio-día.")

    print("\nProceso terminado.")


if __name__ == "__main__":
    main()