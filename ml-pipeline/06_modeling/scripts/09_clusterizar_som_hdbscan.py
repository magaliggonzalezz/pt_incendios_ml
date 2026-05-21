# -*- coding: utf-8 -*-
"""
Modeling 09 | Clustering HDBSCAN sobre nodos SOM

Este script aplica HDBSCAN sobre los nodos ocupados del SOM seleccionado.

Hace lo siguiente:
- Lee pesos del SOM, mapa de activación y asignaciones BMU.
- Filtra nodos SOM ocupados.
- Prueba varias configuraciones de HDBSCAN.
- Calcula métricas internas cuando aplica.
- Propaga etiquetas HDBSCAN a las observaciones entidad-día.
- Conserva ruido como cluster -1.
"""

from pathlib import Path
import json
import numpy as np
import pandas as pd
from sklearn.metrics import silhouette_score, davies_bouldin_score, calinski_harabasz_score
import joblib

try:
    import hdbscan
except ImportError as exc:
    raise ImportError(
        "No está instalado hdbscan. Instálalo con:\n"
        "pip install hdbscan"
    ) from exc


# ============================================================
# CONFIGURACIÓN
# ============================================================

BASE_DIR = Path(r"C:\Users\Hp\OneDrive\Documentos\PT_Analisis")

FLUJO = "entidad_dia"
SOM_CONFIG = "som_sigma2_full"

INPUT_WEIGHTS = BASE_DIR / "06_modeling" / "results" / FLUJO / SOM_CONFIG / "som_weights.csv"
INPUT_ACTIVATION = BASE_DIR / "06_modeling" / "results" / FLUJO / SOM_CONFIG / "som_activation_map.csv"
INPUT_BMU = BASE_DIR / "06_modeling" / "results" / FLUJO / SOM_CONFIG / "som_bmu_assignments.csv"

OUT_RESULTS = BASE_DIR / "06_modeling" / "results" / FLUJO / "som_hdbscan"
OUT_MODELS = BASE_DIR / "06_modeling" / "models" / FLUJO / "som_hdbscan"

OUT_RESULTS.mkdir(parents=True, exist_ok=True)
OUT_MODELS.mkdir(parents=True, exist_ok=True)

OUT_COMPARISON = OUT_RESULTS / "som_hdbscan_comparison.csv"
OUT_NODE_CLUSTERS = OUT_RESULTS / "som_hdbscan_node_clusters.csv"
OUT_OBSERVATION_CLUSTERS = OUT_RESULTS / "som_hdbscan_observation_clusters.csv"
OUT_SELECTED_METRICS = OUT_RESULTS / "som_hdbscan_selected_metrics.json"
OUT_MODEL = OUT_MODELS / "som_hdbscan_model.joblib"


# ============================================================
# PARÁMETROS
# ============================================================

MIN_CLUSTER_SIZE_VALUES = [10, 15, 20, 25, 30, 40, 50]
MIN_SAMPLES_VALUES = [None, 5, 10, 15]

RANDOM_STATE = 42


# ============================================================
# FUNCIONES AUXILIARES
# ============================================================

def ensure_columns(df: pd.DataFrame, required_cols: list[str], context: str) -> None:
    missing = [c for c in required_cols if c not in df.columns]
    if missing:
        raise ValueError(f"Faltan columnas en {context}: {missing}")


def get_pc_cols(df: pd.DataFrame) -> list[str]:
    pc_cols = [c for c in df.columns if c.startswith("PC")]
    return sorted(pc_cols, key=lambda x: int(x.replace("PC", "")))


def validate_numeric_matrix(X: pd.DataFrame) -> None:
    if X.empty:
        raise ValueError("La matriz de nodos ocupados está vacía.")

    nulls = int(X.isna().sum().sum())
    if nulls > 0:
        raise ValueError(f"La matriz contiene {nulls:,} nulos.")

    arr = X.to_numpy()

    if np.isinf(arr).sum() > 0:
        raise ValueError("La matriz contiene infinitos.")


def summarize_labels(labels: np.ndarray, activation_count: np.ndarray) -> dict:
    df = pd.DataFrame({
        "label": labels,
        "activation_count": activation_count,
    })

    total_nodes = len(df)
    total_obs = int(df["activation_count"].sum())

    noise_nodes = int((df["label"] == -1).sum())
    noise_obs = int(df.loc[df["label"] == -1, "activation_count"].sum())

    non_noise = df[df["label"] != -1]

    n_clusters = int(non_noise["label"].nunique())

    if not non_noise.empty:
        cluster_obs = (
            non_noise.groupby("label")["activation_count"]
            .sum()
            .reset_index(name="n_observations")
        )

        min_cluster_obs_pct = float(cluster_obs["n_observations"].min() / total_obs)
        max_cluster_obs_pct = float(cluster_obs["n_observations"].max() / total_obs)
    else:
        min_cluster_obs_pct = np.nan
        max_cluster_obs_pct = np.nan

    return {
        "n_clusters": n_clusters,
        "noise_nodes": noise_nodes,
        "noise_nodes_pct": noise_nodes / total_nodes,
        "noise_observations": noise_obs,
        "noise_observations_pct": noise_obs / total_obs if total_obs > 0 else np.nan,
        "min_cluster_observations_pct": min_cluster_obs_pct,
        "max_cluster_observations_pct": max_cluster_obs_pct,
    }


def compute_internal_metrics(X: pd.DataFrame, labels: np.ndarray) -> dict:
    labels = np.asarray(labels)

    mask = labels != -1
    X_valid = X.loc[mask]
    labels_valid = labels[mask]

    n_clusters = len(set(labels_valid))

    if n_clusters < 2 or len(X_valid) <= n_clusters:
        return {
            "silhouette_score": np.nan,
            "davies_bouldin_score": np.nan,
            "calinski_harabasz_score": np.nan,
        }

    return {
        "silhouette_score": float(silhouette_score(X_valid, labels_valid)),
        "davies_bouldin_score": float(davies_bouldin_score(X_valid, labels_valid)),
        "calinski_harabasz_score": float(calinski_harabasz_score(X_valid, labels_valid)),
    }


def compute_dbcv(X: pd.DataFrame, labels: np.ndarray) -> float:
    try:
        from hdbscan.validity import validity_index
        return float(validity_index(X.to_numpy(), labels))
    except Exception:
        return np.nan


def run_hdbscan_config(X: pd.DataFrame, activation_count: np.ndarray, min_cluster_size, min_samples):
    model = hdbscan.HDBSCAN(
        min_cluster_size=min_cluster_size,
        min_samples=min_samples,
        metric="euclidean",
        cluster_selection_method="eom",
        prediction_data=False,
    )

    labels = model.fit_predict(X)

    summary = summarize_labels(labels, activation_count)
    metrics = compute_internal_metrics(X, labels)
    dbcv = compute_dbcv(X, labels)

    persistence_mean = np.nan
    persistence_max = np.nan

    if hasattr(model, "cluster_persistence_") and len(model.cluster_persistence_) > 0:
        persistence_mean = float(np.mean(model.cluster_persistence_))
        persistence_max = float(np.max(model.cluster_persistence_))

    row = {
        "min_cluster_size": min_cluster_size,
        "min_samples": -1 if min_samples is None else min_samples,
        **summary,
        **metrics,
        "dbcv": dbcv,
        "cluster_persistence_mean": persistence_mean,
        "cluster_persistence_max": persistence_max,
    }

    return model, labels, row


def select_best_config(comparison: pd.DataFrame) -> pd.Series:
    valid = comparison.copy()

    valid = valid[valid["n_clusters"] >= 2]
    valid = valid[valid["noise_observations_pct"] <= 0.40]

    if valid.empty:
        valid = comparison[comparison["n_clusters"] >= 2].copy()

    if valid.empty:
        raise ValueError("Ninguna configuración HDBSCAN generó al menos 2 clusters.")

    valid = valid.sort_values(
        by=[
            "silhouette_score",
            "dbcv",
            "noise_observations_pct",
            "davies_bouldin_score",
        ],
        ascending=[
            False,
            False,
            True,
            True,
        ],
    )

    return valid.iloc[0]


def remap_hdbscan_labels_by_size(nodes: pd.DataFrame) -> pd.DataFrame:
    nodes = nodes.copy()

    non_noise = nodes[nodes["hdbscan_cluster_raw"] != -1].copy()

    if non_noise.empty:
        nodes["cluster_hdbscan"] = -1
        return nodes

    sizes = (
        non_noise.groupby("hdbscan_cluster_raw", as_index=False)
        .agg(n_observations=("activation_count", "sum"))
        .sort_values("n_observations", ascending=False)
        .reset_index(drop=True)
    )

    sizes["cluster_ordered"] = range(1, len(sizes) + 1)
    remap = dict(zip(sizes["hdbscan_cluster_raw"], sizes["cluster_ordered"]))

    nodes["cluster_hdbscan"] = nodes["hdbscan_cluster_raw"].map(remap)
    nodes["cluster_hdbscan"] = nodes["cluster_hdbscan"].fillna(-1).astype(int)

    return nodes


# ============================================================
# PIPELINE PRINCIPAL
# ============================================================

def main():
    print("\nModeling 09 | Clustering HDBSCAN sobre nodos SOM")
    print(f"Flujo: {FLUJO}")
    print(f"SOM usado: {SOM_CONFIG}")

    for path in [INPUT_WEIGHTS, INPUT_ACTIVATION, INPUT_BMU]:
        if not path.exists():
            raise FileNotFoundError(f"No existe archivo requerido: {path}")

    print("\nLeyendo pesos SOM:")
    print(f"- {INPUT_WEIGHTS}")
    weights_df = pd.read_csv(INPUT_WEIGHTS, encoding="utf-8-sig", low_memory=False)

    print("\nLeyendo mapa de activación:")
    print(f"- {INPUT_ACTIVATION}")
    activation_df = pd.read_csv(INPUT_ACTIVATION, encoding="utf-8-sig", low_memory=False)

    print("\nLeyendo asignaciones BMU:")
    print(f"- {INPUT_BMU}")
    bmu_df = pd.read_csv(INPUT_BMU, encoding="utf-8-sig", low_memory=False)

    ensure_columns(weights_df, ["som_x", "som_y", "som_node_id"], "som_weights.csv")
    ensure_columns(activation_df, ["som_node_id", "activation_count"], "som_activation_map.csv")
    ensure_columns(bmu_df, ["som_node_id"], "som_bmu_assignments.csv")

    pc_cols = get_pc_cols(weights_df)

    if not pc_cols:
        raise ValueError("No se encontraron columnas PC en som_weights.csv.")

    nodes = weights_df.merge(
        activation_df[["som_node_id", "activation_count"]],
        on="som_node_id",
        how="left",
    )

    nodes["activation_count"] = nodes["activation_count"].fillna(0).astype(int)

    occupied_nodes = nodes[nodes["activation_count"] > 0].copy()

    print(f"\nNodos totales SOM: {len(nodes):,}")
    print(f"Nodos ocupados: {len(occupied_nodes):,}")
    print(f"Observaciones representadas: {occupied_nodes['activation_count'].sum():,}")
    print(f"Columnas PC: {len(pc_cols):,}")

    X_nodes = occupied_nodes[pc_cols].copy()

    for col in pc_cols:
        X_nodes[col] = pd.to_numeric(X_nodes[col], errors="coerce")

    validate_numeric_matrix(X_nodes)

    activation_count = occupied_nodes["activation_count"].to_numpy()

    comparison_rows = []
    models = {}
    labels_by_config = {}

    print("\nProbando configuraciones HDBSCAN...")

    for min_cluster_size in MIN_CLUSTER_SIZE_VALUES:
        for min_samples in MIN_SAMPLES_VALUES:
            model, labels, row = run_hdbscan_config(
                X=X_nodes,
                activation_count=activation_count,
                min_cluster_size=min_cluster_size,
                min_samples=min_samples,
            )

            key = (min_cluster_size, min_samples)
            models[key] = model
            labels_by_config[key] = labels
            comparison_rows.append(row)

            print(
                f"- min_cluster_size={min_cluster_size}, "
                f"min_samples={min_samples}: "
                f"clusters={row['n_clusters']}, "
                f"noise_obs={row['noise_observations_pct']:.4f}, "
                f"silhouette={row['silhouette_score']}, "
                f"DBCV={row['dbcv']}"
            )

    comparison = pd.DataFrame(comparison_rows)

    selected = select_best_config(comparison)

    selected_min_cluster_size = int(selected["min_cluster_size"])
    selected_min_samples = None if int(selected["min_samples"]) == -1 else int(selected["min_samples"])

    selected_key = (selected_min_cluster_size, selected_min_samples)

    selected_model = models[selected_key]
    selected_labels = labels_by_config[selected_key]

    print("\nConfiguración HDBSCAN seleccionada:")
    print(f"- min_cluster_size: {selected_min_cluster_size}")
    print(f"- min_samples: {selected_min_samples}")
    print(f"- n_clusters: {int(selected['n_clusters'])}")
    print(f"- noise_observations_pct: {selected['noise_observations_pct']:.4f}")
    print(f"- silhouette_score: {selected['silhouette_score']}")
    print(f"- dbcv: {selected['dbcv']}")

    occupied_nodes["hdbscan_cluster_raw"] = selected_labels.astype(int)
    occupied_nodes = remap_hdbscan_labels_by_size(occupied_nodes)

    node_clusters = nodes.merge(
        occupied_nodes[["som_node_id", "hdbscan_cluster_raw", "cluster_hdbscan"]],
        on="som_node_id",
        how="left",
    )

    node_clusters["hdbscan_cluster_raw"] = node_clusters["hdbscan_cluster_raw"].fillna(-999).astype(int)
    node_clusters["cluster_hdbscan"] = node_clusters["cluster_hdbscan"].fillna(-999).astype(int)

    observation_clusters = bmu_df.merge(
        occupied_nodes[["som_node_id", "hdbscan_cluster_raw", "cluster_hdbscan"]],
        on="som_node_id",
        how="left",
    )

    missing_cluster = int(observation_clusters["cluster_hdbscan"].isna().sum())

    if missing_cluster > 0:
        raise ValueError(f"Hay {missing_cluster:,} observaciones sin etiqueta HDBSCAN.")

    observation_clusters["hdbscan_cluster_raw"] = observation_clusters["hdbscan_cluster_raw"].astype(int)
    observation_clusters["cluster_hdbscan"] = observation_clusters["cluster_hdbscan"].astype(int)

    selected_metrics = selected.to_dict()
    selected_metrics["som_config"] = SOM_CONFIG
    selected_metrics["flujo"] = FLUJO
    selected_metrics["selected_min_samples"] = selected_min_samples

    comparison.to_csv(OUT_COMPARISON, index=False, encoding="utf-8-sig")
    node_clusters.to_csv(OUT_NODE_CLUSTERS, index=False, encoding="utf-8-sig")
    observation_clusters.to_csv(OUT_OBSERVATION_CLUSTERS, index=False, encoding="utf-8-sig")

    joblib.dump(selected_model, OUT_MODEL)

    with open(OUT_SELECTED_METRICS, "w", encoding="utf-8") as f:
        json.dump(selected_metrics, f, ensure_ascii=False, indent=2)

    print(f"\nArchivos generados:")
    print(f"- {OUT_COMPARISON}")
    print(f"- {OUT_NODE_CLUSTERS}")
    print(f"- {OUT_OBSERVATION_CLUSTERS}")
    print(f"- {OUT_SELECTED_METRICS}")
    print(f"- {OUT_MODEL}")

    print("\nResumen configuración seleccionada por observaciones:")
    selected_sizes = (
        observation_clusters.groupby("cluster_hdbscan", as_index=False)
        .size()
        .rename(columns={"size": "n_observaciones"})
        .sort_values("cluster_hdbscan")
    )

    selected_sizes["pct_observaciones"] = (
        selected_sizes["n_observaciones"] / len(observation_clusters)
    )

    print(selected_sizes.to_string(index=False))

    print("\nProceso terminado.")


if __name__ == "__main__":
    main()