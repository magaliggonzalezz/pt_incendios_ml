# -*- coding: utf-8 -*-
"""
Modeling 07 | Clustering KMeans sobre nodos SOM

Este script aplica KMeans sobre los nodos ocupados del SOM seleccionado.

Hace lo siguiente:
- Lee pesos del SOM, mapa de activación y asignaciones BMU.
- Filtra nodos SOM ocupados.
- Entrena KMeans para varios valores de k.
- Calcula métricas internas de clustering.
- Selecciona una configuración candidata por silhouette.
- Propaga el cluster de cada nodo SOM a cada observación entidad-día.
- Genera archivos de comparación, clusters por nodo y clusters por observación.
"""

from pathlib import Path
import json
import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score, davies_bouldin_score, calinski_harabasz_score
import joblib


# ============================================================
# CONFIGURACIÓN
# ============================================================

BASE_DIR = Path(r"C:\Users\Hp\OneDrive\Documentos\PT_Analisis")

FLUJO = "entidad_dia"
SOM_CONFIG = "som_sigma2_full"

INPUT_WEIGHTS = BASE_DIR / "06_modeling" / "results" / FLUJO / SOM_CONFIG / "som_weights.csv"
INPUT_ACTIVATION = BASE_DIR / "06_modeling" / "results" / FLUJO / SOM_CONFIG / "som_activation_map.csv"
INPUT_BMU = BASE_DIR / "06_modeling" / "results" / FLUJO / SOM_CONFIG / "som_bmu_assignments.csv"

OUT_RESULTS = BASE_DIR / "06_modeling" / "results" / FLUJO / "som_kmeans"
OUT_MODELS = BASE_DIR / "06_modeling" / "models" / FLUJO / "som_kmeans"
OUT_REPORTS = BASE_DIR / "06_modeling" / "reports"

OUT_RESULTS.mkdir(parents=True, exist_ok=True)
OUT_MODELS.mkdir(parents=True, exist_ok=True)
OUT_REPORTS.mkdir(parents=True, exist_ok=True)

OUT_COMPARISON = OUT_RESULTS / "som_kmeans_comparison.csv"
OUT_NODE_CLUSTERS = OUT_RESULTS / "som_kmeans_node_clusters.csv"
OUT_OBSERVATION_CLUSTERS = OUT_RESULTS / "som_kmeans_observation_clusters.csv"
OUT_SELECTED_METRICS = OUT_RESULTS / "som_kmeans_selected_metrics.json"
OUT_MODEL = OUT_MODELS / "som_kmeans_model.joblib"


# ============================================================
# PARÁMETROS
# ============================================================

RANDOM_STATE = 42
K_VALUES = list(range(4, 11))

# Se selecciona por silhouette como criterio inicial.
# La decisión final puede ajustarse después por interpretabilidad.
SELECTION_METRIC = "silhouette_score"


# ============================================================
# FUNCIONES AUXILIARES
# ============================================================

def ensure_columns(df: pd.DataFrame, required_cols: list[str], context: str) -> None:
    missing = [c for c in required_cols if c not in df.columns]
    if missing:
        raise ValueError(f"Faltan columnas en {context}: {missing}")


def get_pc_cols(df: pd.DataFrame) -> list[str]:
    pc_cols = [c for c in df.columns if c.startswith("PC")]
    pc_cols = sorted(pc_cols, key=lambda x: int(x.replace("PC", "")))
    return pc_cols


def validate_numeric_matrix(X: pd.DataFrame) -> None:
    if X.empty:
        raise ValueError("La matriz de nodos ocupados está vacía.")

    nulls = int(X.isna().sum().sum())
    if nulls > 0:
        raise ValueError(f"La matriz contiene {nulls:,} nulos.")

    arr = X.to_numpy()

    if np.isinf(arr).sum() > 0:
        raise ValueError("La matriz contiene infinitos.")


def weighted_cluster_sizes(labels: np.ndarray, weights: np.ndarray) -> pd.DataFrame:
    df = pd.DataFrame({
        "cluster": labels,
        "activation_count": weights,
    })

    out = (
        df.groupby("cluster", as_index=False)
        .agg(
            n_nodes=("cluster", "size"),
            n_observations=("activation_count", "sum"),
        )
        .sort_values("cluster")
    )

    total_nodes = out["n_nodes"].sum()
    total_obs = out["n_observations"].sum()

    out["pct_nodes"] = out["n_nodes"] / total_nodes
    out["pct_observations"] = out["n_observations"] / total_obs

    return out


def run_kmeans_for_k(X: pd.DataFrame, weights: np.ndarray, k: int) -> tuple[KMeans, dict, np.ndarray]:
    model = KMeans(
        n_clusters=k,
        random_state=RANDOM_STATE,
        n_init=20,
    )

    labels = model.fit_predict(X, sample_weight=weights)

    # Métricas sobre nodos ocupados. No se pondera silhouette directamente.
    sil = silhouette_score(X, labels)
    db = davies_bouldin_score(X, labels)
    ch = calinski_harabasz_score(X, labels)

    sizes = weighted_cluster_sizes(labels, weights)

    min_cluster_obs_pct = float(sizes["pct_observations"].min())
    max_cluster_obs_pct = float(sizes["pct_observations"].max())
    min_cluster_nodes = int(sizes["n_nodes"].min())
    max_cluster_nodes = int(sizes["n_nodes"].max())

    metrics = {
        "k": int(k),
        "silhouette_score": float(sil),
        "davies_bouldin_score": float(db),
        "calinski_harabasz_score": float(ch),
        "inertia": float(model.inertia_),
        "n_occupied_nodes": int(len(X)),
        "total_observations_represented": int(weights.sum()),
        "min_cluster_nodes": min_cluster_nodes,
        "max_cluster_nodes": max_cluster_nodes,
        "min_cluster_observations_pct": min_cluster_obs_pct,
        "max_cluster_observations_pct": max_cluster_obs_pct,
    }

    return model, metrics, labels


def select_best_k(comparison: pd.DataFrame) -> int:
    valid = comparison.copy()

    # Evitar soluciones con clusters extremadamente pequeños en observaciones.
    valid = valid[valid["min_cluster_observations_pct"] >= 0.01]

    if valid.empty:
        valid = comparison.copy()

    if SELECTION_METRIC == "silhouette_score":
        best_row = valid.sort_values(
            by=["silhouette_score", "davies_bouldin_score"],
            ascending=[False, True],
        ).iloc[0]
        return int(best_row["k"])

    if SELECTION_METRIC == "davies_bouldin_score":
        best_row = valid.sort_values(
            by=["davies_bouldin_score", "silhouette_score"],
            ascending=[True, False],
        ).iloc[0]
        return int(best_row["k"])

    raise ValueError(f"Métrica de selección no soportada: {SELECTION_METRIC}")


# ============================================================
# PIPELINE PRINCIPAL
# ============================================================

def main():
    print("\nModeling 07 | Clustering KMeans sobre nodos SOM")
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
    ensure_columns(activation_df, ["som_x", "som_y", "som_node_id", "activation_count", "is_occupied"], "som_activation_map.csv")
    ensure_columns(bmu_df, ["som_x", "som_y", "som_node_id"], "som_bmu_assignments.csv")

    pc_cols = get_pc_cols(weights_df)

    if not pc_cols:
        raise ValueError("No se encontraron columnas PC en som_weights.csv.")

    print(f"\nColumnas PC en pesos SOM: {len(pc_cols):,}")

    nodes = weights_df.merge(
        activation_df[["som_node_id", "activation_count", "is_occupied"]],
        on="som_node_id",
        how="left",
    )

    nodes["activation_count"] = nodes["activation_count"].fillna(0).astype(int)
    nodes["is_occupied"] = nodes["is_occupied"].astype(str).str.lower().isin(["true", "1", "yes"])

    occupied_nodes = nodes[nodes["activation_count"] > 0].copy()

    print(f"Nodos totales SOM: {len(nodes):,}")
    print(f"Nodos ocupados: {len(occupied_nodes):,}")
    print(f"Observaciones representadas: {occupied_nodes['activation_count'].sum():,}")

    X_nodes = occupied_nodes[pc_cols].copy()

    for col in pc_cols:
        X_nodes[col] = pd.to_numeric(X_nodes[col], errors="coerce")

    validate_numeric_matrix(X_nodes)

    node_weights = occupied_nodes["activation_count"].to_numpy()

    comparison_rows = []
    models = {}
    labels_by_k = {}

    print("\nEntrenando KMeans para varios k...")

    for k in K_VALUES:
        if k >= len(occupied_nodes):
            print(f"- k={k} omitido: mayor o igual que nodos ocupados.")
            continue

        model, metrics, labels = run_kmeans_for_k(X_nodes, node_weights, k)

        comparison_rows.append(metrics)
        models[k] = model
        labels_by_k[k] = labels

        print(
            f"- k={k}: "
            f"silhouette={metrics['silhouette_score']:.4f}, "
            f"DB={metrics['davies_bouldin_score']:.4f}, "
            f"CH={metrics['calinski_harabasz_score']:.2f}, "
            f"inertia={metrics['inertia']:.4f}"
        )

    comparison = pd.DataFrame(comparison_rows)

    if comparison.empty:
        raise ValueError("No se pudo entrenar ningún KMeans.")

    selected_k = select_best_k(comparison)

    print(f"\nK seleccionado inicialmente: {selected_k}")

    selected_model = models[selected_k]
    selected_labels = labels_by_k[selected_k]

    occupied_nodes["kmeans_cluster"] = selected_labels
    occupied_nodes["kmeans_cluster"] = occupied_nodes["kmeans_cluster"].astype(int)

    # Reordenar clusters por tamaño de observaciones descendente para lectura más limpia.
    cluster_sizes = (
        occupied_nodes.groupby("kmeans_cluster", as_index=False)
        .agg(n_observations=("activation_count", "sum"))
        .sort_values("n_observations", ascending=False)
        .reset_index(drop=True)
    )
    cluster_sizes["cluster_ordered"] = range(1, len(cluster_sizes) + 1)

    remap = dict(zip(cluster_sizes["kmeans_cluster"], cluster_sizes["cluster_ordered"]))

    occupied_nodes["cluster_kmeans"] = occupied_nodes["kmeans_cluster"].map(remap).astype(int)

    # Nodos no ocupados se conservan sin cluster.
    node_clusters = nodes.merge(
        occupied_nodes[["som_node_id", "kmeans_cluster", "cluster_kmeans"]],
        on="som_node_id",
        how="left",
    )

    # Propagar a observaciones
    observation_clusters = bmu_df.merge(
        occupied_nodes[["som_node_id", "cluster_kmeans"]],
        on="som_node_id",
        how="left",
    )

    missing_cluster = int(observation_clusters["cluster_kmeans"].isna().sum())

    if missing_cluster > 0:
        raise ValueError(
            f"Hay {missing_cluster:,} observaciones sin cluster KMeans. "
            "Esto no debería ocurrir si todos los BMU están ocupados."
        )

    observation_clusters["cluster_kmeans"] = observation_clusters["cluster_kmeans"].astype(int)

    selected_metrics = comparison.loc[comparison["k"] == selected_k].iloc[0].to_dict()
    selected_metrics["selected_k"] = int(selected_k)
    selected_metrics["selection_metric"] = SELECTION_METRIC
    selected_metrics["som_config"] = SOM_CONFIG
    selected_metrics["flujo"] = FLUJO

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
    selected_sizes = (
        observation_clusters.groupby("cluster_kmeans", as_index=False)
        .size()
        .rename(columns={"size": "n_observaciones"})
    )
    selected_sizes["pct_observaciones"] = selected_sizes["n_observaciones"] / len(observation_clusters)
    print(selected_sizes.to_string(index=False))

    print("\nProceso terminado.")


if __name__ == "__main__":
    main()