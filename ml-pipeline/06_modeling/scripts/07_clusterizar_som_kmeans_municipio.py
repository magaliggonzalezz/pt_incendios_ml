# -*- coding: utf-8 -*-
"""
Modeling 07 | Clustering KMeans sobre nodos SOM municipio-día

Este script aplica KMeans sobre los nodos ocupados del SOM municipio-día.

Hace lo siguiente:
- Lee pesos SOM, mapa de activación y asignaciones BMU.
- Filtra nodos ocupados.
- Entrena KMeans para varios valores de k.
- Calcula métricas internas sobre nodos SOM ocupados.
- Propaga etiquetas de cluster a todas las observaciones municipio-día.
- Guarda comparación, clusters por nodo, clusters por observación y modelo seleccionado.
"""

from pathlib import Path
import json
import numpy as np
import pandas as pd
import joblib

from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score, davies_bouldin_score, calinski_harabasz_score


# ============================================================
# CONFIGURACIÓN
# ============================================================

BASE_DIR = Path(r"C:\Users\Hp\OneDrive\Documentos\PT_Analisis")

FLUJO = "municipio_dia"
SOM_CONFIG = "som_50x50_sigma3_sample"

INPUT_WEIGHTS = BASE_DIR / "06_modeling" / "results" / FLUJO / SOM_CONFIG / "som_weights.csv"
INPUT_ACTIVATION = BASE_DIR / "06_modeling" / "results" / FLUJO / SOM_CONFIG / "som_activation_map.csv"
INPUT_BMU = BASE_DIR / "06_modeling" / "results" / FLUJO / SOM_CONFIG / "som_bmu_assignments.csv"

OUT_RESULTS = BASE_DIR / "06_modeling" / "results" / FLUJO / "som_kmeans"
OUT_MODELS = BASE_DIR / "06_modeling" / "models" / FLUJO / "som_kmeans"

OUT_RESULTS.mkdir(parents=True, exist_ok=True)
OUT_MODELS.mkdir(parents=True, exist_ok=True)

OUT_COMPARISON = OUT_RESULTS / "som_kmeans_comparison.csv"
OUT_NODE_CLUSTERS = OUT_RESULTS / "som_kmeans_node_clusters.csv"
OUT_OBSERVATION_CLUSTERS = OUT_RESULTS / "som_kmeans_observation_clusters.csv"
OUT_SELECTED_METRICS = OUT_RESULTS / "som_kmeans_selected_metrics.json"
OUT_MODEL = OUT_MODELS / "som_kmeans_model.joblib"


# ============================================================
# PARÁMETROS
# ============================================================

RANDOM_STATE = 42

K_VALUES = list(range(5, 16))

# Selección inicial automática por silhouette, pero con control de clusters extremos.
MAX_CLUSTER_OBSERVATIONS_PCT_ALLOWED = 0.40
MIN_CLUSTER_OBSERVATIONS_PCT_ALLOWED = 0.005


# ============================================================
# FUNCIONES AUXILIARES
# ============================================================

def ensure_file(path: Path, label: str) -> None:
    if not path.exists():
        raise FileNotFoundError(f"No existe {label}: {path}")


def ensure_columns(df: pd.DataFrame, required_cols: list[str], context: str) -> None:
    missing = [c for c in required_cols if c not in df.columns]
    if missing:
        raise ValueError(f"Faltan columnas en {context}: {missing}")


def get_pc_cols(df: pd.DataFrame) -> list[str]:
    pc_cols = [c for c in df.columns if c.startswith("PC")]
    return sorted(pc_cols, key=lambda x: int(x.replace("PC", "")))


def validate_numeric_matrix(X: pd.DataFrame) -> None:
    nulls = int(X.isna().sum().sum())
    if nulls > 0:
        raise ValueError(f"La matriz contiene {nulls:,} nulos.")

    arr = X.to_numpy(dtype=np.float64)

    if np.isinf(arr).sum() > 0:
        raise ValueError("La matriz contiene infinitos.")


def compute_cluster_observation_distribution(
    node_clusters: pd.DataFrame,
    cluster_col: str,
) -> pd.DataFrame:
    dist = (
        node_clusters.groupby(cluster_col, as_index=False)
        .agg(n_observaciones=("activation_count", "sum"))
        .sort_values(cluster_col)
    )

    total = dist["n_observaciones"].sum()
    dist["pct_observaciones"] = dist["n_observaciones"] / total

    return dist


def run_kmeans_config(
    X_nodes: pd.DataFrame,
    occupied_nodes: pd.DataFrame,
    k: int,
) -> tuple[KMeans, pd.DataFrame, dict]:
    model = KMeans(
        n_clusters=k,
        random_state=RANDOM_STATE,
        n_init=25,
        max_iter=500,
    )

    labels = model.fit_predict(X_nodes)

    temp_nodes = occupied_nodes.copy()
    temp_nodes["cluster_kmeans"] = labels + 1

    dist = compute_cluster_observation_distribution(
        temp_nodes,
        "cluster_kmeans",
    )

    silhouette = silhouette_score(X_nodes, labels)
    db = davies_bouldin_score(X_nodes, labels)
    ch = calinski_harabasz_score(X_nodes, labels)

    row = {
        "k": k,
        "silhouette_score": float(silhouette),
        "davies_bouldin_score": float(db),
        "calinski_harabasz_score": float(ch),
        "inertia": float(model.inertia_),
        "min_cluster_observations_pct": float(dist["pct_observaciones"].min()),
        "max_cluster_observations_pct": float(dist["pct_observaciones"].max()),
        "min_cluster_observations": int(dist["n_observaciones"].min()),
        "max_cluster_observations": int(dist["n_observaciones"].max()),
    }

    return model, temp_nodes, row


def select_best_k(comparison: pd.DataFrame) -> int:
    valid = comparison.copy()

    valid = valid[
        (valid["max_cluster_observations_pct"] <= MAX_CLUSTER_OBSERVATIONS_PCT_ALLOWED)
        & (valid["min_cluster_observations_pct"] >= MIN_CLUSTER_OBSERVATIONS_PCT_ALLOWED)
    ]

    if valid.empty:
        valid = comparison.copy()

    valid = valid.sort_values(
        by=[
            "silhouette_score",
            "davies_bouldin_score",
            "calinski_harabasz_score",
        ],
        ascending=[
            False,
            True,
            False,
        ],
    )

    return int(valid.iloc[0]["k"])


def remap_clusters_by_size(node_clusters: pd.DataFrame) -> pd.DataFrame:
    node_clusters = node_clusters.copy()

    sizes = (
        node_clusters.groupby("cluster_kmeans", as_index=False)
        .agg(n_observaciones=("activation_count", "sum"))
        .sort_values("n_observaciones", ascending=False)
        .reset_index(drop=True)
    )

    sizes["cluster_ordered"] = range(1, len(sizes) + 1)

    remap = dict(zip(sizes["cluster_kmeans"], sizes["cluster_ordered"]))

    node_clusters["cluster_kmeans_raw"] = node_clusters["cluster_kmeans"].astype(int)
    node_clusters["cluster_kmeans"] = node_clusters["cluster_kmeans"].map(remap).astype(int)

    return node_clusters


def save_json(data: dict, path: Path) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# ============================================================
# PIPELINE PRINCIPAL
# ============================================================

def main():
    print("\nModeling 07 | Clustering KMeans sobre nodos SOM")
    print(f"Flujo: {FLUJO}")
    print(f"SOM usado: {SOM_CONFIG}")

    ensure_file(INPUT_WEIGHTS, "pesos SOM")
    ensure_file(INPUT_ACTIVATION, "mapa de activación SOM")
    ensure_file(INPUT_BMU, "asignaciones BMU")

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

    print(f"\nColumnas PC en pesos SOM: {len(pc_cols):,}")
    print(f"Nodos totales SOM: {len(nodes):,}")
    print(f"Nodos ocupados: {len(occupied_nodes):,}")
    print(f"Observaciones representadas: {occupied_nodes['activation_count'].sum():,}")

    X_nodes = occupied_nodes[pc_cols].copy()

    for col in pc_cols:
        X_nodes[col] = pd.to_numeric(X_nodes[col], errors="coerce")

    validate_numeric_matrix(X_nodes)

    print("\nEntrenando KMeans para varios k...")

    comparison_rows = []
    models = {}
    node_clusters_by_k = {}

    for k in K_VALUES:
        model, node_clusters, row = run_kmeans_config(
            X_nodes=X_nodes,
            occupied_nodes=occupied_nodes,
            k=k,
        )

        models[k] = model
        node_clusters_by_k[k] = node_clusters
        comparison_rows.append(row)

        print(
            f"- k={k}: "
            f"silhouette={row['silhouette_score']:.4f}, "
            f"DB={row['davies_bouldin_score']:.4f}, "
            f"CH={row['calinski_harabasz_score']:.2f}, "
            f"inertia={row['inertia']:.4f}, "
            f"min_pct={row['min_cluster_observations_pct']:.4f}, "
            f"max_pct={row['max_cluster_observations_pct']:.4f}"
        )

    comparison = pd.DataFrame(comparison_rows)

    selected_k = select_best_k(comparison)

    print(f"\nK seleccionado inicialmente: {selected_k}")

    selected_model = models[selected_k]
    selected_node_clusters = node_clusters_by_k[selected_k].copy()

    selected_node_clusters = remap_clusters_by_size(selected_node_clusters)

    node_clusters_out = nodes.merge(
        selected_node_clusters[
            [
                "som_node_id",
                "cluster_kmeans_raw",
                "cluster_kmeans",
            ]
        ],
        on="som_node_id",
        how="left",
    )

    node_clusters_out["cluster_kmeans_raw"] = (
        node_clusters_out["cluster_kmeans_raw"]
        .fillna(-999)
        .astype(int)
    )

    node_clusters_out["cluster_kmeans"] = (
        node_clusters_out["cluster_kmeans"]
        .fillna(-999)
        .astype(int)
    )

    observation_clusters = bmu_df.merge(
        selected_node_clusters[
            [
                "som_node_id",
                "cluster_kmeans_raw",
                "cluster_kmeans",
            ]
        ],
        on="som_node_id",
        how="left",
    )

    missing_cluster = int(observation_clusters["cluster_kmeans"].isna().sum())

    if missing_cluster > 0:
        raise ValueError(f"Hay {missing_cluster:,} observaciones sin cluster KMeans.")

    observation_clusters["cluster_kmeans_raw"] = observation_clusters["cluster_kmeans_raw"].astype(int)
    observation_clusters["cluster_kmeans"] = observation_clusters["cluster_kmeans"].astype(int)

    selected_row = comparison[comparison["k"] == selected_k].iloc[0].to_dict()

    selected_metrics = {
        "flujo": FLUJO,
        "som_config": SOM_CONFIG,
        "selected_k": int(selected_k),
        **{
            k: (
                int(v)
                if isinstance(v, (np.integer,))
                else float(v)
                if isinstance(v, (np.floating,))
                else v
            )
            for k, v in selected_row.items()
        },
        "nota": "KMeans entrenado sobre nodos SOM ocupados; etiquetas propagadas a todas las observaciones municipio-día.",
    }

    comparison.to_csv(OUT_COMPARISON, index=False, encoding="utf-8-sig")
    node_clusters_out.to_csv(OUT_NODE_CLUSTERS, index=False, encoding="utf-8-sig")
    observation_clusters.to_csv(OUT_OBSERVATION_CLUSTERS, index=False, encoding="utf-8-sig")

    save_json(selected_metrics, OUT_SELECTED_METRICS)
    joblib.dump(selected_model, OUT_MODEL)

    selected_sizes = (
        observation_clusters.groupby("cluster_kmeans", as_index=False)
        .size()
        .rename(columns={"size": "n_observaciones"})
        .sort_values("cluster_kmeans")
    )

    selected_sizes["pct_observaciones"] = (
        selected_sizes["n_observaciones"] / len(observation_clusters)
    )

    print("\nArchivos generados:")
    print(f"- {OUT_COMPARISON}")
    print(f"- {OUT_NODE_CLUSTERS}")
    print(f"- {OUT_OBSERVATION_CLUSTERS}")
    print(f"- {OUT_SELECTED_METRICS}")
    print(f"- {OUT_MODEL}")

    print("\nMétricas comparativas:")
    print(
        comparison[
            [
                "k",
                "silhouette_score",
                "davies_bouldin_score",
                "calinski_harabasz_score",
                "inertia",
                "min_cluster_observations_pct",
                "max_cluster_observations_pct",
            ]
        ].to_string(index=False)
    )

    print("\nTamaño de clusters seleccionados:")
    print(selected_sizes.to_string(index=False))

    print("\nProceso terminado.")


if __name__ == "__main__":
    main()