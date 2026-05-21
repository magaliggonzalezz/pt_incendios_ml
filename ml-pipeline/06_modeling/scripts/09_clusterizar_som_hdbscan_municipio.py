# -*- coding: utf-8 -*-
"""
Modeling 09 | Clustering HDBSCAN sobre nodos SOM municipio-día

Este script aplica HDBSCAN sobre los nodos ocupados del SOM municipio-día.

Hace lo siguiente:
- Lee pesos SOM, mapa de activación y asignaciones BMU.
- Filtra nodos ocupados.
- Prueba varias configuraciones HDBSCAN.
- Calcula métricas internas sobre nodos SOM ocupados.
- Selecciona una configuración candidata.
- Propaga etiquetas HDBSCAN a todas las observaciones municipio-día por chunks.
- Guarda comparación, clusters por nodo, clusters por observación y modelo.
"""

from pathlib import Path
import json
import numpy as np
import pandas as pd
import joblib

from sklearn.metrics import silhouette_score, davies_bouldin_score, calinski_harabasz_score

try:
    import hdbscan
    from hdbscan.validity import validity_index
except ImportError as exc:
    raise ImportError(
        "No está instalado hdbscan. Instálalo con:\n"
        "pip install hdbscan\n\n"
        "Si te falla en Python 3.14, usa Python 3.13 como hiciste antes."
    ) from exc


# ============================================================
# CONFIGURACIÓN
# ============================================================

BASE_DIR = Path(r"C:\Users\Hp\OneDrive\Documentos\PT_Analisis")

FLUJO = "municipio_dia"
SOM_CONFIG = "som_50x50_sigma3_sample"

CHUNKSIZE = 300_000
RANDOM_STATE = 42

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


MIN_CLUSTER_SIZES = [20, 30, 40, 50, 75, 100, 125, 150]
MIN_SAMPLES_VALUES = [None, 5, 10, 15, 20, 30]


# ============================================================
# FUNCIONES
# ============================================================

def ensure_file(path: Path, label: str) -> None:
    if not path.exists():
        raise FileNotFoundError(f"No existe {label}: {path}")


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


def remove_output_if_exists(path: Path) -> None:
    if path.exists():
        path.unlink()


def calc_metrics(X: np.ndarray, labels: np.ndarray, activation_counts: np.ndarray) -> dict:
    labels = np.asarray(labels)

    non_noise_mask = labels != -1
    unique_non_noise = sorted(set(labels[non_noise_mask]))

    n_clusters = len(unique_non_noise)

    total_obs = int(activation_counts.sum())
    noise_obs = int(activation_counts[labels == -1].sum()) if (labels == -1).any() else 0
    noise_obs_pct = noise_obs / total_obs if total_obs > 0 else np.nan

    metrics = {
        "n_clusters": int(n_clusters),
        "noise_nodes": int((labels == -1).sum()),
        "noise_nodes_pct": float((labels == -1).mean()),
        "noise_observations": int(noise_obs),
        "noise_observations_pct": float(noise_obs_pct),
        "silhouette_score": np.nan,
        "davies_bouldin_score": np.nan,
        "calinski_harabasz_score": np.nan,
        "dbcv": np.nan,
    }

    if n_clusters >= 2 and non_noise_mask.sum() > n_clusters:
        X_non_noise = X[non_noise_mask]
        labels_non_noise = labels[non_noise_mask]

        metrics["silhouette_score"] = float(silhouette_score(X_non_noise, labels_non_noise))
        metrics["davies_bouldin_score"] = float(davies_bouldin_score(X_non_noise, labels_non_noise))
        metrics["calinski_harabasz_score"] = float(calinski_harabasz_score(X_non_noise, labels_non_noise))

    if n_clusters >= 2:
        try:
            metrics["dbcv"] = float(validity_index(X, labels))
        except Exception:
            metrics["dbcv"] = np.nan

    return metrics


def run_hdbscan(X: np.ndarray, min_cluster_size: int, min_samples):
    model = hdbscan.HDBSCAN(
        min_cluster_size=min_cluster_size,
        min_samples=min_samples,
        metric="euclidean",
        cluster_selection_method="eom",
        prediction_data=False,
    )

    labels = model.fit_predict(X)

    return model, labels


def select_best_config(comparison: pd.DataFrame) -> pd.Series:
    valid = comparison.copy()

    valid = valid[
        (valid["n_clusters"] >= 3)
        & (valid["n_clusters"] <= 25)
        & (valid["noise_observations_pct"] <= 0.35)
    ].copy()

    if valid.empty:
        valid = comparison[comparison["n_clusters"] >= 2].copy()

    if valid.empty:
        return comparison.iloc[0]

    valid["dbcv_sort"] = valid["dbcv"].fillna(-999)
    valid["silhouette_sort"] = valid["silhouette_score"].fillna(-999)

    valid = valid.sort_values(
        by=[
            "dbcv_sort",
            "silhouette_sort",
            "noise_observations_pct",
            "n_clusters",
        ],
        ascending=[
            False,
            False,
            True,
            True,
        ],
    )

    return valid.iloc[0]


def remap_clusters_by_size(node_clusters: pd.DataFrame) -> pd.DataFrame:
    node_clusters = node_clusters.copy()

    non_noise = node_clusters[node_clusters["cluster_hdbscan_raw"] != -1].copy()

    sizes = (
        non_noise.groupby("cluster_hdbscan_raw", as_index=False)
        .agg(n_observaciones=("activation_count", "sum"))
        .sort_values("n_observaciones", ascending=False)
        .reset_index(drop=True)
    )

    sizes["cluster_hdbscan"] = range(1, len(sizes) + 1)

    remap = dict(zip(sizes["cluster_hdbscan_raw"], sizes["cluster_hdbscan"]))

    node_clusters["cluster_hdbscan"] = node_clusters["cluster_hdbscan_raw"].map(remap)
    node_clusters["cluster_hdbscan"] = node_clusters["cluster_hdbscan"].fillna(-1).astype(int)

    return node_clusters


def propagate_labels_by_chunks(selected_node_clusters: pd.DataFrame) -> int:
    remove_output_if_exists(OUT_OBSERVATION_CLUSTERS)

    label_map = selected_node_clusters[
        [
            "som_node_id",
            "cluster_hdbscan_raw",
            "cluster_hdbscan",
        ]
    ].copy()

    total_rows = 0

    print("\nPropagando etiquetas HDBSCAN a observaciones por chunks...")

    for i, chunk in enumerate(
        pd.read_csv(
            INPUT_BMU,
            encoding="utf-8-sig",
            chunksize=CHUNKSIZE,
            low_memory=False,
        ),
        start=1,
    ):
        out = chunk.merge(
            label_map,
            on="som_node_id",
            how="left",
        )

        missing = int(out["cluster_hdbscan"].isna().sum())
        if missing > 0:
            raise ValueError(f"Chunk {i}: {missing:,} observaciones sin cluster HDBSCAN.")

        out["cluster_hdbscan_raw"] = out["cluster_hdbscan_raw"].astype(int)
        out["cluster_hdbscan"] = out["cluster_hdbscan"].astype(int)

        out.to_csv(
            OUT_OBSERVATION_CLUSTERS,
            index=False,
            encoding="utf-8-sig",
            mode="a",
            header=not OUT_OBSERVATION_CLUSTERS.exists(),
        )

        total_rows += len(out)

        print(f"- chunk {i:,}: filas acumuladas {total_rows:,}")

    return total_rows


def save_json(data: dict, path: Path) -> None:
    clean = {}

    for k, v in data.items():
        if isinstance(v, np.integer):
            clean[k] = int(v)
        elif isinstance(v, np.floating):
            clean[k] = float(v)
        elif pd.isna(v) if isinstance(v, float) else False:
            clean[k] = None
        else:
            clean[k] = v

    with open(path, "w", encoding="utf-8") as f:
        json.dump(clean, f, ensure_ascii=False, indent=2)


# ============================================================
# PIPELINE PRINCIPAL
# ============================================================

def main():
    print("\nModeling 09 | Clustering HDBSCAN sobre nodos SOM")
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

    pc_cols = get_pc_cols(weights_df)

    if not pc_cols:
        raise ValueError("No se detectaron columnas PC en pesos SOM.")

    nodes = weights_df.merge(
        activation_df[["som_node_id", "activation_count"]],
        on="som_node_id",
        how="left",
    )

    nodes["activation_count"] = nodes["activation_count"].fillna(0).astype(int)

    occupied_nodes = nodes[nodes["activation_count"] > 0].copy()

    X_nodes_df = occupied_nodes[pc_cols].copy()

    for col in pc_cols:
        X_nodes_df[col] = pd.to_numeric(X_nodes_df[col], errors="coerce")

    validate_numeric_matrix(X_nodes_df)

    X_nodes = X_nodes_df.to_numpy(dtype=np.float64)
    activation_counts = occupied_nodes["activation_count"].to_numpy(dtype=np.int64)

    print(f"\nNodos totales SOM: {len(nodes):,}")
    print(f"Nodos ocupados: {len(occupied_nodes):,}")
    print(f"Observaciones representadas: {int(activation_counts.sum()):,}")
    print(f"Columnas PC: {len(pc_cols):,}")

    print("\nProbando configuraciones HDBSCAN...")

    comparison_rows = []
    models = {}
    labels_by_config = {}

    for min_cluster_size in MIN_CLUSTER_SIZES:
        for min_samples in MIN_SAMPLES_VALUES:
            model, labels = run_hdbscan(
                X=X_nodes,
                min_cluster_size=min_cluster_size,
                min_samples=min_samples,
            )

            metrics = calc_metrics(
                X=X_nodes,
                labels=labels,
                activation_counts=activation_counts,
            )

            key = (min_cluster_size, min_samples)

            models[key] = model
            labels_by_config[key] = labels

            row = {
                "min_cluster_size": min_cluster_size,
                "min_samples": "None" if min_samples is None else int(min_samples),
                **metrics,
            }

            comparison_rows.append(row)

            print(
                f"- min_cluster_size={min_cluster_size}, "
                f"min_samples={min_samples}: "
                f"clusters={metrics['n_clusters']}, "
                f"noise_obs={metrics['noise_observations_pct']:.4f}, "
                f"silhouette={metrics['silhouette_score']}, "
                f"DBCV={metrics['dbcv']}"
            )

    comparison = pd.DataFrame(comparison_rows)

    selected = select_best_config(comparison)

    selected_min_cluster_size = int(selected["min_cluster_size"])
    selected_min_samples_raw = selected["min_samples"]
    selected_min_samples = None if str(selected_min_samples_raw) == "None" else int(selected_min_samples_raw)

    selected_key = (selected_min_cluster_size, selected_min_samples)

    selected_model = models[selected_key]
    selected_labels = labels_by_config[selected_key]

    selected_node_clusters = occupied_nodes.copy()
    selected_node_clusters["cluster_hdbscan_raw"] = selected_labels.astype(int)
    selected_node_clusters = remap_clusters_by_size(selected_node_clusters)

    node_clusters_out = nodes.merge(
        selected_node_clusters[
            [
                "som_node_id",
                "cluster_hdbscan_raw",
                "cluster_hdbscan",
            ]
        ],
        on="som_node_id",
        how="left",
    )

    node_clusters_out["cluster_hdbscan_raw"] = (
        node_clusters_out["cluster_hdbscan_raw"]
        .fillna(-999)
        .astype(int)
    )

    node_clusters_out["cluster_hdbscan"] = (
        node_clusters_out["cluster_hdbscan"]
        .fillna(-999)
        .astype(int)
    )

    total_rows = propagate_labels_by_chunks(selected_node_clusters)

    comparison.to_csv(OUT_COMPARISON, index=False, encoding="utf-8-sig")
    node_clusters_out.to_csv(OUT_NODE_CLUSTERS, index=False, encoding="utf-8-sig")

    selected_metrics = selected.to_dict()
    selected_metrics["flujo"] = FLUJO
    selected_metrics["som_config"] = SOM_CONFIG
    selected_metrics["nota"] = "HDBSCAN entrenado sobre nodos SOM ocupados; etiquetas propagadas a todas las observaciones municipio-día."
    selected_metrics["observations_labeled"] = int(total_rows)

    save_json(selected_metrics, OUT_SELECTED_METRICS)
    joblib.dump(selected_model, OUT_MODEL)

    obs_clusters = pd.read_csv(
        OUT_OBSERVATION_CLUSTERS,
        encoding="utf-8-sig",
        usecols=["cluster_hdbscan"],
        low_memory=False,
    )

    selected_sizes = (
        obs_clusters.groupby("cluster_hdbscan", as_index=False)
        .size()
        .rename(columns={"size": "n_observaciones"})
        .sort_values("cluster_hdbscan")
    )

    selected_sizes["pct_observaciones"] = selected_sizes["n_observaciones"] / len(obs_clusters)

    print("\nConfiguración HDBSCAN seleccionada:")
    print(f"- min_cluster_size: {selected_min_cluster_size}")
    print(f"- min_samples: {selected_min_samples}")
    print(f"- n_clusters: {int(selected['n_clusters'])}")
    print(f"- noise_observations_pct: {float(selected['noise_observations_pct']):.4f}")
    print(f"- silhouette_score: {selected['silhouette_score']}")
    print(f"- dbcv: {selected['dbcv']}")

    print("\nArchivos generados:")
    print(f"- {OUT_COMPARISON}")
    print(f"- {OUT_NODE_CLUSTERS}")
    print(f"- {OUT_OBSERVATION_CLUSTERS}")
    print(f"- {OUT_SELECTED_METRICS}")
    print(f"- {OUT_MODEL}")

    print("\nResumen configuración seleccionada por observaciones:")
    print(selected_sizes.to_string(index=False))

    print("\nProceso terminado.")


if __name__ == "__main__":
    main()