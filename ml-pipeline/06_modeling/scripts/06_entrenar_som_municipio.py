# -*- coding: utf-8 -*-
"""
Modeling 06 | Entrenamiento SOM municipio-día

Este script entrena un Self-Organizing Map para el flujo municipio-día.

Hace lo siguiente:
- Lee la vista PCA para clustering por chunks.
- Detecta columnas PC.
- Ajusta MinMaxScaler sobre todos los scores PCA.
- Toma una muestra controlada para entrenar SOM.
- Entrena SOM sobre la muestra escalada.
- Asigna BMU a todas las observaciones municipio-día por chunks.
- Genera pesos SOM, mapa de activación, U-Matrix, asignaciones BMU y métricas.
"""

from pathlib import Path
import json
import numpy as np
import pandas as pd
import joblib
from sklearn.preprocessing import MinMaxScaler

try:
    from minisom import MiniSom
except ImportError as exc:
    raise ImportError(
        "No está instalado minisom. Instálalo con:\n"
        "pip install minisom"
    ) from exc


# ============================================================
# CONFIGURACIÓN
# ============================================================

BASE_DIR = Path(r"C:\Users\Hp\OneDrive\Documentos\PT_Analisis")

FLUJO = "municipio_dia"
SOM_CONFIG = "som_50x50_sigma3_sample"

INPUT_PCA_VIEW = BASE_DIR / "06_modeling" / "datasets" / FLUJO / f"modeling_{FLUJO}_pca_clustering_view.csv"

OUT_RESULTS = BASE_DIR / "06_modeling" / "results" / FLUJO / SOM_CONFIG
OUT_MODELS = BASE_DIR / "06_modeling" / "models" / FLUJO / SOM_CONFIG

OUT_RESULTS.mkdir(parents=True, exist_ok=True)
OUT_MODELS.mkdir(parents=True, exist_ok=True)

OUT_BMU = OUT_RESULTS / "som_bmu_assignments.csv"
OUT_WEIGHTS = OUT_RESULTS / "som_weights.csv"
OUT_ACTIVATION = OUT_RESULTS / "som_activation_map.csv"
OUT_U_MATRIX = OUT_RESULTS / "som_u_matrix.csv"
OUT_METRICS = OUT_RESULTS / "som_metrics.json"

OUT_SCALER = OUT_MODELS / "som_minmax_scaler.joblib"
OUT_MODEL = OUT_MODELS / "som_model.joblib"


# ============================================================
# PARÁMETROS
# ============================================================

RANDOM_STATE = 42

CHUNKSIZE = 300_000
SAMPLE_PER_CHUNK = 10_000
METRICS_SAMPLE_SIZE = 100_000

SOM_X = 50
SOM_Y = 50

SIGMA = 3.0
LEARNING_RATE = 0.5
N_ITERATIONS = 750_000


# ============================================================
# FUNCIONES AUXILIARES
# ============================================================

def ensure_file(path: Path, label: str) -> None:
    if not path.exists():
        raise FileNotFoundError(f"No existe {label}: {path}")


def get_pc_cols(cols: list[str]) -> list[str]:
    pc_cols = [c for c in cols if c.startswith("PC")]
    return sorted(pc_cols, key=lambda x: int(x.replace("PC", "")))


def remove_output_if_exists(path: Path) -> None:
    if path.exists():
        path.unlink()


def validate_numeric_chunk(chunk: pd.DataFrame, chunk_id: int) -> None:
    nulls = int(chunk.isna().sum().sum())
    if nulls > 0:
        raise ValueError(f"Chunk {chunk_id}: contiene {nulls:,} nulos.")

    arr = chunk.to_numpy(dtype=np.float64)

    if np.isinf(arr).sum() > 0:
        raise ValueError(f"Chunk {chunk_id}: contiene infinitos.")


def fit_minmax_scaler(input_path: Path, pc_cols: list[str]) -> MinMaxScaler:
    scaler = MinMaxScaler()

    total_rows = 0

    print("\nAjustando MinMaxScaler sobre todos los PCs...")

    for i, chunk in enumerate(
        pd.read_csv(
            input_path,
            encoding="utf-8-sig",
            usecols=pc_cols,
            chunksize=CHUNKSIZE,
            low_memory=False,
        ),
        start=1,
    ):
        validate_numeric_chunk(chunk, i)

        X = chunk.to_numpy(dtype=np.float64)

        scaler.partial_fit(X)

        total_rows += len(chunk)

        print(f"- scaler chunk {i:,}: filas acumuladas {total_rows:,}")

    return scaler


def build_training_sample(input_path: Path, pc_cols: list[str], scaler: MinMaxScaler) -> np.ndarray:
    samples = []

    print("\nConstruyendo muestra de entrenamiento SOM...")

    for i, chunk in enumerate(
        pd.read_csv(
            input_path,
            encoding="utf-8-sig",
            usecols=pc_cols,
            chunksize=CHUNKSIZE,
            low_memory=False,
        ),
        start=1,
    ):
        validate_numeric_chunk(chunk, i)

        n_sample = min(SAMPLE_PER_CHUNK, len(chunk))

        sample = chunk.sample(
            n=n_sample,
            random_state=RANDOM_STATE + i,
        )

        X_sample = sample.to_numpy(dtype=np.float64)
        X_sample_scaled = scaler.transform(X_sample)

        samples.append(X_sample_scaled)

        print(f"- chunk {i:,}: muestra {n_sample:,} filas")

    X_train = np.vstack(samples)

    print(f"Muestra total de entrenamiento SOM: {len(X_train):,} filas")

    return X_train


def build_metrics_sample(X_train: np.ndarray) -> np.ndarray:
    if len(X_train) <= METRICS_SAMPLE_SIZE:
        return X_train

    rng = np.random.default_rng(RANDOM_STATE)

    idx = rng.choice(
        len(X_train),
        size=METRICS_SAMPLE_SIZE,
        replace=False,
    )

    return X_train[idx]


def build_weights_df(som: MiniSom, pc_cols: list[str]) -> pd.DataFrame:
    weights = som.get_weights()

    rows = []

    for x in range(SOM_X):
        for y in range(SOM_Y):
            row = {
                "som_x": x,
                "som_y": y,
                "som_node_id": f"{x}_{y}",
            }

            for j, pc in enumerate(pc_cols):
                row[pc] = float(weights[x, y, j])

            rows.append(row)

    return pd.DataFrame(rows)


def build_u_matrix_df(som: MiniSom) -> pd.DataFrame:
    u_matrix = som.distance_map()

    rows = []

    for x in range(SOM_X):
        for y in range(SOM_Y):
            rows.append({
                "som_x": x,
                "som_y": y,
                "som_node_id": f"{x}_{y}",
                "u_matrix_distance": float(u_matrix[x, y]),
            })

    return pd.DataFrame(rows)


def build_activation_df(activation: np.ndarray) -> pd.DataFrame:
    rows = []

    total_nodes = SOM_X * SOM_Y

    for x in range(SOM_X):
        for y in range(SOM_Y):
            count = int(activation[x, y])

            rows.append({
                "som_x": x,
                "som_y": y,
                "som_node_id": f"{x}_{y}",
                "activation_count": count,
                "is_occupied": count > 0,
            })

    df = pd.DataFrame(rows)

    df["activation_pct"] = df["activation_count"] / df["activation_count"].sum()

    occupied = int((df["activation_count"] > 0).sum())

    print(f"\nNodos ocupados: {occupied:,} de {total_nodes:,}")

    return df


def assign_bmu_all_rows(
    input_path: Path,
    pc_cols: list[str],
    id_profile_cols: list[str],
    scaler: MinMaxScaler,
    som: MiniSom,
) -> tuple[np.ndarray, int]:
    remove_output_if_exists(OUT_BMU)

    activation = np.zeros((SOM_X, SOM_Y), dtype=np.int64)

    total_rows = 0

    print("\nAsignando BMU a todas las observaciones municipio-día...")

    usecols = id_profile_cols + pc_cols

    for i, chunk in enumerate(
        pd.read_csv(
            input_path,
            encoding="utf-8-sig",
            usecols=usecols,
            chunksize=CHUNKSIZE,
            low_memory=False,
        ),
        start=1,
    ):
        ids = chunk[id_profile_cols].copy()

        X = chunk[pc_cols].copy()
        validate_numeric_chunk(X, i)

        X_scaled = scaler.transform(X.to_numpy(dtype=np.float64))

        bmu_rows = []

        for row in X_scaled:
            x, y = som.winner(row)
            activation[x, y] += 1

            bmu_rows.append((x, y, f"{x}_{y}"))

        bmu_df = pd.DataFrame(
            bmu_rows,
            columns=["som_x", "som_y", "som_node_id"],
        )

        out = pd.concat(
            [
                ids.reset_index(drop=True),
                bmu_df.reset_index(drop=True),
            ],
            axis=1,
        )

        out.to_csv(
            OUT_BMU,
            index=False,
            encoding="utf-8-sig",
            mode="a",
            header=not OUT_BMU.exists(),
        )

        total_rows += len(chunk)

        print(f"- BMU chunk {i:,}: filas acumuladas {total_rows:,}")

    return activation, total_rows


def calculate_metrics(
    som: MiniSom,
    X_metrics: np.ndarray,
    total_rows: int,
    activation_df: pd.DataFrame,
) -> dict:
    print("\nCalculando métricas SOM...")

    quantization_error = float(som.quantization_error(X_metrics))
    topographic_error = float(som.topographic_error(X_metrics))

    total_nodes = SOM_X * SOM_Y
    occupied_nodes = int((activation_df["activation_count"] > 0).sum())
    empty_nodes = total_nodes - occupied_nodes

    metrics = {
        "flujo": FLUJO,
        "som_config": SOM_CONFIG,
        "som_x": SOM_X,
        "som_y": SOM_Y,
        "total_nodes": total_nodes,
        "occupied_nodes": occupied_nodes,
        "empty_nodes": empty_nodes,
        "occupied_nodes_pct": occupied_nodes / total_nodes,
        "n_rows_total": int(total_rows),
        "train_sample_size": int(len(X_metrics)) if len(X_metrics) < SAMPLE_PER_CHUNK else "sample_controlled",
        "train_sample_rows_actual": None,
        "metrics_sample_size": int(len(X_metrics)),
        "n_iterations": int(N_ITERATIONS),
        "sigma": float(SIGMA),
        "learning_rate": float(LEARNING_RATE),
        "quantization_error": quantization_error,
        "topographic_error": topographic_error,
        "random_state": RANDOM_STATE,
        "sample_per_chunk": SAMPLE_PER_CHUNK,
    }

    return metrics


def save_json(data: dict, path: Path) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# ============================================================
# PIPELINE PRINCIPAL
# ============================================================

def main():
    print("\nModeling 06 | Entrenamiento SOM")
    print(f"Flujo: {FLUJO}")
    print(f"Configuración SOM: {SOM_CONFIG}")

    ensure_file(INPUT_PCA_VIEW, "vista PCA clustering")

    print("\nLeyendo encabezado vista PCA:")
    print(f"- {INPUT_PCA_VIEW}")

    header = pd.read_csv(INPUT_PCA_VIEW, encoding="utf-8-sig", nrows=0)

    pc_cols = get_pc_cols(list(header.columns))
    id_profile_cols = [c for c in header.columns if c not in pc_cols]

    if not pc_cols:
        raise ValueError("No se detectaron columnas PC.")

    print(f"Columnas PC detectadas: {len(pc_cols):,}")
    print(f"Columnas ID/perfilado: {len(id_profile_cols):,}")

    scaler = fit_minmax_scaler(INPUT_PCA_VIEW, pc_cols)

    X_train = build_training_sample(INPUT_PCA_VIEW, pc_cols, scaler)

    print(f"\nGrid SOM: {SOM_X} x {SOM_Y} = {SOM_X * SOM_Y:,} nodos")
    print(f"Sigma: {SIGMA}")
    print(f"Learning rate: {LEARNING_RATE}")
    print(f"Iteraciones: {N_ITERATIONS:,}")

    som = MiniSom(
        x=SOM_X,
        y=SOM_Y,
        input_len=len(pc_cols),
        sigma=SIGMA,
        learning_rate=LEARNING_RATE,
        random_seed=RANDOM_STATE,
    )

    print("\nInicializando pesos con PCA...")
    som.pca_weights_init(X_train)

    print("Entrenando SOM...")
    som.train_random(
        data=X_train,
        num_iteration=N_ITERATIONS,
        verbose=True,
    )

    X_metrics = build_metrics_sample(X_train)

    activation, total_rows = assign_bmu_all_rows(
        input_path=INPUT_PCA_VIEW,
        pc_cols=pc_cols,
        id_profile_cols=id_profile_cols,
        scaler=scaler,
        som=som,
    )

    weights_df = build_weights_df(som, pc_cols)
    activation_df = build_activation_df(activation)
    u_matrix_df = build_u_matrix_df(som)

    metrics = calculate_metrics(
        som=som,
        X_metrics=X_metrics,
        total_rows=total_rows,
        activation_df=activation_df,
    )

    metrics["train_sample_rows_actual"] = int(len(X_train))

    weights_df.to_csv(OUT_WEIGHTS, index=False, encoding="utf-8-sig")
    activation_df.to_csv(OUT_ACTIVATION, index=False, encoding="utf-8-sig")
    u_matrix_df.to_csv(OUT_U_MATRIX, index=False, encoding="utf-8-sig")

    save_json(metrics, OUT_METRICS)

    joblib.dump(scaler, OUT_SCALER)
    joblib.dump(som, OUT_MODEL)

    print("\nArchivos generados:")
    print(f"- {OUT_BMU}")
    print(f"- {OUT_WEIGHTS}")
    print(f"- {OUT_ACTIVATION}")
    print(f"- {OUT_U_MATRIX}")
    print(f"- {OUT_METRICS}")
    print(f"- {OUT_SCALER}")
    print(f"- {OUT_MODEL}")

    print("\nMétricas SOM:")
    for k, v in metrics.items():
        print(f"- {k}: {v}")

    print("\nProceso terminado.")


if __name__ == "__main__":
    main()