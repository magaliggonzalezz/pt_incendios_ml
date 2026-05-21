# -*- coding: utf-8 -*-
"""
Modeling 10 | Comparación interna de configuraciones municipio-día

Este script compara las configuraciones de modelado generadas para municipio-día.

Hace lo siguiente:
- Lee métricas PCA, SOM, KMeans y HDBSCAN.
- Resume configuraciones candidatas.
- Compara utilidad metodológica, balance de clusters y aplicabilidad.
- Selecciona el modelo candidato principal.
- Genera un CSV de comparación y un JSON de decisión.
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

PCA_VARIANCE = BASE_DIR / "06_modeling" / "results" / FLUJO / "pca" / "pca_explained_variance.csv"
SOM_METRICS = BASE_DIR / "06_modeling" / "results" / FLUJO / SOM_CONFIG / "som_metrics.json"

KMEANS_COMPARISON = BASE_DIR / "06_modeling" / "results" / FLUJO / "som_kmeans" / "som_kmeans_comparison.csv"
KMEANS_SELECTED = BASE_DIR / "06_modeling" / "results" / FLUJO / "som_kmeans" / "som_kmeans_selected_metrics.json"
KMEANS_PROFILE = BASE_DIR / "06_modeling" / "reports" / f"modeling_08_resumen_perfil_clusters_{FLUJO}.csv"

HDBSCAN_COMPARISON = BASE_DIR / "06_modeling" / "results" / FLUJO / "som_hdbscan" / "som_hdbscan_comparison.csv"
HDBSCAN_SELECTED = BASE_DIR / "06_modeling" / "results" / FLUJO / "som_hdbscan" / "som_hdbscan_selected_metrics.json"

OUT_REPORTS = BASE_DIR / "06_modeling" / "reports"
OUT_REPORTS.mkdir(parents=True, exist_ok=True)

OUT_COMPARISON = OUT_REPORTS / f"modeling_10_comparacion_configuraciones_{FLUJO}.csv"
OUT_DECISION = OUT_REPORTS / f"modeling_10_decision_modelo_candidato_{FLUJO}.json"


# ============================================================
# FUNCIONES
# ============================================================

def ensure_file(path: Path, label: str) -> None:
    if not path.exists():
        raise FileNotFoundError(f"No existe {label}: {path}")


def read_json(path: Path) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def clean_json_value(value):
    if isinstance(value, np.integer):
        return int(value)

    if isinstance(value, np.floating):
        return float(value)

    if isinstance(value, float) and np.isnan(value):
        return None

    return value


def save_json(data: dict, path: Path) -> None:
    clean = {k: clean_json_value(v) for k, v in data.items()}

    with open(path, "w", encoding="utf-8") as f:
        json.dump(clean, f, ensure_ascii=False, indent=2)


def get_pca_90_info() -> dict:
    pca = pd.read_csv(PCA_VARIANCE, encoding="utf-8-sig")

    required = {"component", "cumulative_variance_pct"}
    missing = required - set(pca.columns)

    if missing:
        raise ValueError(f"Faltan columnas en pca_explained_variance.csv: {missing}")

    pca["component_number"] = (
        pca["component"]
        .astype(str)
        .str.replace("PC", "", regex=False)
        .astype(int)
    )

    pca_90 = pca[pca["cumulative_variance_pct"] >= 90].sort_values("component_number").iloc[0]

    return {
        "pca_components_selected": int(pca_90["component_number"]),
        "pca_cumulative_variance_pct": float(pca_90["cumulative_variance_pct"]),
    }


def summarize_kmeans() -> dict:
    selected = read_json(KMEANS_SELECTED)
    profile = pd.read_csv(KMEANS_PROFILE, encoding="utf-8-sig")

    n_clusters = int(selected["selected_k"])

    min_pct = float(profile["pct_observaciones"].min())
    max_pct = float(profile["pct_observaciones"].max())

    top_conafor = profile.sort_values("has_conafor_rate", ascending=False).iloc[0]
    top_firms = profile.sort_values("has_firms_rate", ascending=False).iloc[0]

    return {
        "modelo": "PCA + SOM + KMeans",
        "rol": "candidato_principal",
        "n_clusters": n_clusters,
        "noise_pct": 0.0,
        "silhouette_score": float(selected["silhouette_score"]),
        "davies_bouldin_score": float(selected["davies_bouldin_score"]),
        "calinski_harabasz_score": float(selected["calinski_harabasz_score"]),
        "min_cluster_pct": min_pct,
        "max_cluster_pct": max_pct,
        "cluster_mayor_has_conafor": int(top_conafor["cluster_kmeans"]),
        "mayor_has_conafor_rate": float(top_conafor["has_conafor_rate"]),
        "cluster_mayor_has_firms": int(top_firms["cluster_kmeans"]),
        "mayor_has_firms_rate": float(top_firms["has_firms_rate"]),
        "decision": "seleccionado",
        "motivo": (
            "Genera una segmentación balanceada e interpretable para municipio-día, "
            "sin ruido y con todos los registros asignados."
        ),
    }


def summarize_hdbscan() -> dict:
    selected = read_json(HDBSCAN_SELECTED)

    n_clusters = int(selected["n_clusters"])
    noise_pct = float(selected["noise_observations_pct"])

    return {
        "modelo": "PCA + SOM + HDBSCAN",
        "rol": "contraste",
        "n_clusters": n_clusters,
        "noise_pct": noise_pct,
        "silhouette_score": float(selected["silhouette_score"]) if selected.get("silhouette_score") is not None else np.nan,
        "davies_bouldin_score": float(selected["davies_bouldin_score"]) if selected.get("davies_bouldin_score") is not None else np.nan,
        "calinski_harabasz_score": float(selected["calinski_harabasz_score"]) if selected.get("calinski_harabasz_score") is not None else np.nan,
        "dbcv": float(selected["dbcv"]) if selected.get("dbcv") is not None else np.nan,
        "min_cluster_pct": np.nan,
        "max_cluster_pct": np.nan,
        "cluster_mayor_has_conafor": np.nan,
        "mayor_has_conafor_rate": np.nan,
        "cluster_mayor_has_firms": np.nan,
        "mayor_has_firms_rate": np.nan,
        "decision": "no_seleccionado",
        "motivo": (
            "Produce una estructura desbalanceada: un cluster dominante, "
            "un cluster pequeño y una proporción relevante de ruido."
        ),
    }


# ============================================================
# PIPELINE
# ============================================================

def main():
    print("\nModeling 10 | Comparación interna de configuraciones")
    print(f"Flujo: {FLUJO}")

    ensure_file(PCA_VARIANCE, "varianza PCA")
    ensure_file(SOM_METRICS, "métricas SOM")
    ensure_file(KMEANS_COMPARISON, "comparación KMeans")
    ensure_file(KMEANS_SELECTED, "métricas KMeans seleccionadas")
    ensure_file(KMEANS_PROFILE, "perfil KMeans")
    ensure_file(HDBSCAN_COMPARISON, "comparación HDBSCAN")
    ensure_file(HDBSCAN_SELECTED, "métricas HDBSCAN seleccionadas")

    pca_info = get_pca_90_info()
    som_metrics = read_json(SOM_METRICS)

    kmeans_summary = summarize_kmeans()
    hdbscan_summary = summarize_hdbscan()

    rows = []

    for row in [kmeans_summary, hdbscan_summary]:
        rows.append({
            "flujo": FLUJO,
            "pca_components": pca_info["pca_components_selected"],
            "pca_cumulative_variance_pct": pca_info["pca_cumulative_variance_pct"],
            "som_config": SOM_CONFIG,
            "som_x": som_metrics["som_x"],
            "som_y": som_metrics["som_y"],
            "som_total_nodes": som_metrics["total_nodes"],
            "som_occupied_nodes": som_metrics["occupied_nodes"],
            "som_occupied_nodes_pct": som_metrics["occupied_nodes_pct"],
            "som_quantization_error": som_metrics["quantization_error"],
            "som_topographic_error": som_metrics["topographic_error"],
            **row,
        })

    comparison = pd.DataFrame(rows)
    comparison.to_csv(OUT_COMPARISON, index=False, encoding="utf-8-sig")

    decision = {
        "flujo": FLUJO,
        "modelo_candidato_principal": "PCA + SOM + KMeans",
        "modelo_contraste": "PCA + SOM + HDBSCAN",
        "pca_components": pca_info["pca_components_selected"],
        "pca_cumulative_variance_pct": pca_info["pca_cumulative_variance_pct"],
        "som_config": SOM_CONFIG,
        "som_x": som_metrics["som_x"],
        "som_y": som_metrics["som_y"],
        "som_sigma": som_metrics["sigma"],
        "som_learning_rate": som_metrics["learning_rate"],
        "som_train_sample_rows_actual": som_metrics.get("train_sample_rows_actual"),
        "som_n_iterations": som_metrics["n_iterations"],
        "kmeans_k": int(kmeans_summary["n_clusters"]),
        "hdbscan_n_clusters": int(hdbscan_summary["n_clusters"]),
        "hdbscan_noise_pct": float(hdbscan_summary["noise_pct"]),
        "decision": (
            "Se selecciona PCA + SOM + KMeans como modelo candidato principal "
            "para municipio-día por su mayor utilidad interpretativa, balance de clusters "
            "y asignación completa de observaciones. HDBSCAN se conserva como contraste."
        ),
    }

    save_json(decision, OUT_DECISION)

    print("\nArchivos generados:")
    print(f"- {OUT_COMPARISON}")
    print(f"- {OUT_DECISION}")

    print("\nModelo candidato principal:")
    print(f"- PCA {decision['pca_components']} PCs")
    print(f"- SOM {decision['som_x']}x{decision['som_y']} sigma={decision['som_sigma']} muestra controlada")
    print(f"- KMeans k={decision['kmeans_k']} sobre nodos SOM ocupados")

    print("\nModelo de contraste:")
    print(f"- HDBSCAN n_clusters={decision['hdbscan_n_clusters']}")
    print(f"- HDBSCAN noise_pct={decision['hdbscan_noise_pct']:.4f}")

    print("\nProceso terminado.")


if __name__ == "__main__":
    main()