# -*- coding: utf-8 -*-
"""
Modeling 10 | Comparación interna de configuraciones

Este script resume las configuraciones probadas durante Modeling.

Hace lo siguiente:
- Lee métricas PCA.
- Lee métricas SOM de distintas corridas.
- Lee comparación KMeans.
- Lee comparación HDBSCAN.
- Genera una comparación integrada.
- Define el candidato principal de modelado.
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

OUT_REPORTS = BASE_DIR / "06_modeling" / "reports"
OUT_REPORTS.mkdir(parents=True, exist_ok=True)

INPUT_PCA_VARIANCE = BASE_DIR / "06_modeling" / "results" / FLUJO / "pca" / "pca_explained_variance.csv"

SOM_METRICS_FILES = {
    "som_sigma1_5_sample": BASE_DIR / "06_modeling" / "results" / FLUJO / "som" / "som_metrics.json",
    "som_sigma2_sample": BASE_DIR / "06_modeling" / "results" / FLUJO / "som_sigma2" / "som_metrics.json",
    "som_sigma2_full": BASE_DIR / "06_modeling" / "results" / FLUJO / "som_sigma2_full" / "som_metrics.json",
}

INPUT_KMEANS_COMPARISON = BASE_DIR / "06_modeling" / "results" / FLUJO / "som_kmeans" / "som_kmeans_comparison.csv"
INPUT_KMEANS_SELECTED = BASE_DIR / "06_modeling" / "results" / FLUJO / "som_kmeans" / "som_kmeans_selected_metrics.json"

INPUT_HDBSCAN_COMPARISON = BASE_DIR / "06_modeling" / "results" / FLUJO / "som_hdbscan" / "som_hdbscan_comparison.csv"
INPUT_HDBSCAN_SELECTED = BASE_DIR / "06_modeling" / "results" / FLUJO / "som_hdbscan" / "som_hdbscan_selected_metrics.json"

OUT_COMPARISON = OUT_REPORTS / f"modeling_10_comparacion_configuraciones_{FLUJO}.csv"
OUT_DECISION = OUT_REPORTS / f"modeling_10_decision_modelo_candidato_{FLUJO}.json"


# ============================================================
# FUNCIONES AUXILIARES
# ============================================================

def read_json_if_exists(path: Path) -> dict | None:
    if not path.exists():
        return None

    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def read_csv_if_exists(path: Path) -> pd.DataFrame | None:
    if not path.exists():
        return None

    return pd.read_csv(path, encoding="utf-8-sig")


def get_pca_summary(path: Path) -> dict:
    if not path.exists():
        return {
            "pca_components_total": np.nan,
            "pca_components_90pct": np.nan,
            "pca_selected_components": 18,
            "pca_selected_variance_pct": np.nan,
        }

    df = pd.read_csv(path, encoding="utf-8-sig")

    mask_90 = df["cumulative_variance_pct"] >= 90

    n_90 = int(df.loc[mask_90, "component_number"].iloc[0]) if mask_90.any() else np.nan

    selected = df[df["component_number"] == 18]

    selected_var = (
        float(selected["cumulative_variance_pct"].iloc[0])
        if not selected.empty
        else np.nan
    )

    return {
        "pca_components_total": int(len(df)),
        "pca_components_90pct": n_90,
        "pca_selected_components": 18,
        "pca_selected_variance_pct": selected_var,
    }


def build_som_rows(som_metrics_files: dict[str, Path]) -> list[dict]:
    rows = []

    for config_name, path in som_metrics_files.items():
        metrics = read_json_if_exists(path)

        if metrics is None:
            rows.append({
                "etapa": "som",
                "configuracion": config_name,
                "estado": "no_encontrado",
            })
            continue

        rows.append({
            "etapa": "som",
            "configuracion": config_name,
            "estado": "ok",
            "som_x": metrics.get("som_x"),
            "som_y": metrics.get("som_y"),
            "sigma": metrics.get("sigma"),
            "learning_rate": metrics.get("learning_rate"),
            "train_sample_size": metrics.get("train_sample_size"),
            "metrics_sample_size": metrics.get("metrics_sample_size"),
            "n_iterations": metrics.get("n_iterations"),
            "occupied_nodes": metrics.get("occupied_nodes"),
            "empty_nodes": metrics.get("empty_nodes"),
            "occupied_nodes_pct": metrics.get("occupied_nodes_pct"),
            "quantization_error": metrics.get("quantization_error"),
            "topographic_error": metrics.get("topographic_error"),
            "decision": (
                "seleccionado_como_som_base"
                if config_name == "som_sigma2_full"
                else "comparativo"
            ),
        })

    return rows


def build_kmeans_rows(comparison_path: Path, selected_path: Path) -> list[dict]:
    rows = []

    comparison = read_csv_if_exists(comparison_path)
    selected = read_json_if_exists(selected_path)

    if comparison is None:
        return [{
            "etapa": "som_kmeans",
            "configuracion": "kmeans",
            "estado": "no_encontrado",
        }]

    selected_k = None
    if selected is not None:
        selected_k = int(selected.get("selected_k", selected.get("k")))

    for _, r in comparison.iterrows():
        k = int(r["k"])

        rows.append({
            "etapa": "som_kmeans",
            "configuracion": f"kmeans_k{k}",
            "estado": "ok",
            "k": k,
            "silhouette_score": r.get("silhouette_score"),
            "davies_bouldin_score": r.get("davies_bouldin_score"),
            "calinski_harabasz_score": r.get("calinski_harabasz_score"),
            "inertia": r.get("inertia"),
            "min_cluster_observations_pct": r.get("min_cluster_observations_pct"),
            "max_cluster_observations_pct": r.get("max_cluster_observations_pct"),
            "decision": (
                "seleccionado_como_candidato_principal"
                if selected_k == k
                else "comparativo"
            ),
        })

    return rows


def build_hdbscan_rows(comparison_path: Path, selected_path: Path) -> list[dict]:
    rows = []

    comparison = read_csv_if_exists(comparison_path)
    selected = read_json_if_exists(selected_path)

    if comparison is None:
        return [{
            "etapa": "som_hdbscan",
            "configuracion": "hdbscan",
            "estado": "no_encontrado",
        }]

    selected_mcs = None
    selected_ms = None

    if selected is not None:
        selected_mcs = int(selected.get("min_cluster_size"))
        raw_ms = selected.get("min_samples")
        selected_ms = int(raw_ms) if raw_ms is not None else -1

    for _, r in comparison.iterrows():
        mcs = int(r["min_cluster_size"])
        ms = int(r["min_samples"])

        is_selected = selected_mcs == mcs and selected_ms == ms

        rows.append({
            "etapa": "som_hdbscan",
            "configuracion": f"hdbscan_mcs{mcs}_ms{ms}",
            "estado": "ok",
            "min_cluster_size": mcs,
            "min_samples": ms,
            "n_clusters": r.get("n_clusters"),
            "noise_observations_pct": r.get("noise_observations_pct"),
            "silhouette_score": r.get("silhouette_score"),
            "davies_bouldin_score": r.get("davies_bouldin_score"),
            "calinski_harabasz_score": r.get("calinski_harabasz_score"),
            "dbcv": r.get("dbcv"),
            "decision": (
                "mejor_hdbscan_pero_no_principal"
                if is_selected
                else "comparativo"
            ),
        })

    return rows


# ============================================================
# PIPELINE PRINCIPAL
# ============================================================

def main():
    print("\nModeling 10 | Comparación interna de configuraciones")
    print(f"Flujo: {FLUJO}")

    pca_summary = get_pca_summary(INPUT_PCA_VARIANCE)

    rows = []

    rows.append({
        "etapa": "pca",
        "configuracion": "pca_18_componentes",
        "estado": "ok",
        **pca_summary,
        "decision": "18_PCs_retenidas_por_90pct_varianza",
    })

    rows.extend(build_som_rows(SOM_METRICS_FILES))
    rows.extend(build_kmeans_rows(INPUT_KMEANS_COMPARISON, INPUT_KMEANS_SELECTED))
    rows.extend(build_hdbscan_rows(INPUT_HDBSCAN_COMPARISON, INPUT_HDBSCAN_SELECTED))

    comparison = pd.DataFrame(rows)
    comparison.to_csv(OUT_COMPARISON, index=False, encoding="utf-8-sig")

    decision = {
        "flujo": FLUJO,
        "modelo_candidato_principal": "PCA_18PCs__SOM_30x30_sigma2_full__KMeans_k9",
        "pca": {
            "componentes_seleccionados": 18,
            "varianza_acumulada_pct": pca_summary.get("pca_selected_variance_pct"),
        },
        "som": {
            "configuracion": "som_sigma2_full",
            "grid": "30x30",
            "sigma": 2.0,
            "entrenamiento": "dataset_completo_entidad_dia",
            "motivo": "mejor equilibrio entre estabilidad topologica, ocupacion de nodos y defensa metodologica",
        },
        "clustering_principal": {
            "algoritmo": "KMeans sobre nodos SOM ocupados",
            "k": 9,
            "motivo": "mejor silhouette entre k probados y segmentacion interpretable sin ruido",
        },
        "clustering_comparativo": {
            "algoritmo": "HDBSCAN sobre nodos SOM ocupados",
            "estatus": "comparativo_exploratorio",
            "motivo": "mejores metricas internas pero demasiados clusters para interpretacion y aplicacion web",
        },
        "nota_crisp_dm": (
            "Estas metricas corresponden a comparacion interna dentro de Modeling; "
            "no constituyen Evaluation formal."
        ),
    }

    with open(OUT_DECISION, "w", encoding="utf-8") as f:
        json.dump(decision, f, ensure_ascii=False, indent=2)

    print("\nArchivos generados:")
    print(f"- {OUT_COMPARISON}")
    print(f"- {OUT_DECISION}")

    print("\nModelo candidato principal:")
    print("- PCA 18 PCs")
    print("- SOM 30x30 sigma=2.0 full dataset")
    print("- KMeans k=9 sobre nodos SOM ocupados")

    print("\nProceso terminado.")


if __name__ == "__main__":
    main()