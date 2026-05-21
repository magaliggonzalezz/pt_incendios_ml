# -*- coding: utf-8 -*-
"""
Modeling 06 | Entrenamiento SOM

Este script entrena un Self-Organizing Map usando la vista PCA reducida
generada en Modeling 05.

Hace lo siguiente:
- Lee la vista PCA para clustering.
- Usa únicamente las columnas PC como variables de entrenamiento.
- Escala las PCs a rango [0, 1] con MinMaxScaler.
- Entrena un SOM.
- Asigna a cada fila su BMU.
- Genera pesos del SOM, mapa de activación y U-Matrix.
- Calcula métricas internas básicas del SOM.
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

FLUJO = "entidad_dia"

INPUT_VIEW = BASE_DIR / "06_modeling" / "datasets" / FLUJO / f"modeling_{FLUJO}_pca_clustering_view.csv"

OUT_RESULTS = BASE_DIR / "06_modeling" / "results" / FLUJO / "som_sigma2_full"
OUT_MODELS = BASE_DIR / "06_modeling" / "models" / FLUJO / "som_sigma2_full"
OUT_REPORTS = BASE_DIR / "06_modeling" / "reports"

OUT_RESULTS.mkdir(parents=True, exist_ok=True)
OUT_MODELS.mkdir(parents=True, exist_ok=True)
OUT_REPORTS.mkdir(parents=True, exist_ok=True)

OUT_BMU = OUT_RESULTS / "som_bmu_assignments.csv"
OUT_WEIGHTS = OUT_RESULTS / "som_weights.csv"
OUT_ACTIVATION = OUT_RESULTS / "som_activation_map.csv"
OUT_U_MATRIX = OUT_RESULTS / "som_u_matrix.csv"
OUT_METRICS = OUT_RESULTS / "som_metrics.json"
OUT_SCALER = OUT_MODELS / "som_minmax_scaler.joblib"
OUT_SOM_MODEL = OUT_MODELS / "som_model.joblib"


# ============================================================
# PARÁMETROS SOM
# ============================================================

RANDOM_STATE = 42

SOM_X = 30
SOM_Y = 30

SIGMA = 2.0
LEARNING_RATE = 0.5

# Para entidad-día se puede entrenar con una muestra controlada.
# La asignación BMU final se hace sobre todas las filas.
TRAIN_SAMPLE_SIZE = None

# Iteraciones sobre la muestra.
N_ITERATIONS = 500_000

METRICS_SAMPLE_SIZE = None


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

def get_pc_cols(df: pd.DataFrame) -> list[str]:
    pc_cols = [c for c in df.columns if c.startswith("PC")]
    pc_cols = sorted(pc_cols, key=lambda x: int(x.replace("PC", "")))
    return pc_cols


def ensure_columns(df: pd.DataFrame, required_cols: list[str], context: str) -> None:
    missing = [c for c in required_cols if c not in df.columns]
    if missing:
        raise ValueError(f"Faltan columnas en {context}: {missing}")


def validate_matrix(X: pd.DataFrame) -> None:
    if X.empty:
        raise ValueError("La matriz de entrenamiento está vacía.")

    nulls = int(X.isna().sum().sum())
    if nulls > 0:
        raise ValueError(f"La matriz contiene {nulls:,} nulos.")

    arr = X.to_numpy()

    if np.isinf(arr).sum() > 0:
        raise ValueError("La matriz contiene valores infinitos.")


def build_training_sample(X_scaled: np.ndarray, sample_size: int, random_state: int) -> np.ndarray:
    n_rows = X_scaled.shape[0]

    if sample_size is None or sample_size >= n_rows:
        return X_scaled

    rng = np.random.default_rng(random_state)
    idx = rng.choice(n_rows, size=sample_size, replace=False)

    return X_scaled[idx]


def assign_bmus(som: MiniSom, X_scaled: np.ndarray) -> pd.DataFrame:
    bmus = []

    for row in X_scaled:
        x, y = som.winner(row)
        bmus.append((x, y, f"{x}_{y}"))

    return pd.DataFrame(bmus, columns=["som_x", "som_y", "som_node_id"])


def build_weights_df(som: MiniSom, pc_cols: list[str]) -> pd.DataFrame:
    weights = som.get_weights()

    rows = []

    for x in range(weights.shape[0]):
        for y in range(weights.shape[1]):
            row = {
                "som_x": x,
                "som_y": y,
                "som_node_id": f"{x}_{y}",
            }

            for i, pc in enumerate(pc_cols):
                row[pc] = weights[x, y, i]

            rows.append(row)

    return pd.DataFrame(rows)


def build_activation_map(bmu_df: pd.DataFrame, som_x: int, som_y: int) -> pd.DataFrame:
    counts = (
        bmu_df.groupby(["som_x", "som_y", "som_node_id"])
        .size()
        .reset_index(name="activation_count")
    )

    all_nodes = pd.DataFrame(
        [
            {
                "som_x": x,
                "som_y": y,
                "som_node_id": f"{x}_{y}",
            }
            for x in range(som_x)
            for y in range(som_y)
        ]
    )

    activation = all_nodes.merge(
        counts,
        on=["som_x", "som_y", "som_node_id"],
        how="left",
    )

    activation["activation_count"] = activation["activation_count"].fillna(0).astype(int)
    activation["is_occupied"] = activation["activation_count"] > 0

    return activation


def build_u_matrix_df(som: MiniSom) -> pd.DataFrame:
    u_matrix = som.distance_map()

    rows = []

    for x in range(u_matrix.shape[0]):
        for y in range(u_matrix.shape[1]):
            rows.append({
                "som_x": x,
                "som_y": y,
                "som_node_id": f"{x}_{y}",
                "u_matrix_distance": u_matrix[x, y],
            })

    return pd.DataFrame(rows)


def calculate_metrics(
    som: MiniSom,
    X_scaled: np.ndarray,
    metrics_sample_size: int,
    random_state: int,
    activation: pd.DataFrame,
) -> dict:
    n_rows = X_scaled.shape[0]

    if metrics_sample_size is not None and metrics_sample_size < n_rows:
        rng = np.random.default_rng(random_state)
        idx = rng.choice(n_rows, size=metrics_sample_size, replace=False)
        X_metrics = X_scaled[idx]
    else:
        X_metrics = X_scaled

    quantization_error = float(som.quantization_error(X_metrics))

    try:
        topographic_error = float(som.topographic_error(X_metrics))
    except Exception:
        topographic_error = None

    occupied_nodes = int(activation["is_occupied"].sum())
    total_nodes = int(len(activation))
    empty_nodes = total_nodes - occupied_nodes

    train_size_used = n_rows if TRAIN_SAMPLE_SIZE is None else min(TRAIN_SAMPLE_SIZE, n_rows)

    return {
        "flujo": FLUJO,
        "som_x": SOM_X,
        "som_y": SOM_Y,
        "total_nodes": total_nodes,
        "occupied_nodes": occupied_nodes,
        "empty_nodes": empty_nodes,
        "occupied_nodes_pct": occupied_nodes / total_nodes,
        "n_rows_total": int(n_rows),
        "train_sample_size": int(train_size_used),
        "metrics_sample_size": int(len(X_metrics)),
        "n_iterations": int(N_ITERATIONS),
        "sigma": float(SIGMA),
        "learning_rate": float(LEARNING_RATE),
        "quantization_error": quantization_error,
        "topographic_error": topographic_error,
        "random_state": RANDOM_STATE,
    }


# ============================================================
# PIPELINE PRINCIPAL
# ============================================================

def main():
    print("\nModeling 06 | Entrenamiento SOM")
    print(f"Flujo: {FLUJO}")

    if not INPUT_VIEW.exists():
        raise FileNotFoundError(f"No existe vista PCA clustering: {INPUT_VIEW}")

    print(f"\nLeyendo vista PCA clustering:")
    print(f"- {INPUT_VIEW}")

    df = pd.read_csv(INPUT_VIEW, encoding="utf-8-sig", low_memory=False)

    print(f"Filas: {len(df):,}")
    print(f"Columnas: {len(df.columns):,}")

    id_cols = ID_COLS_BY_FLOW[FLUJO]
    pc_cols = get_pc_cols(df)

    ensure_columns(df, id_cols, "vista PCA clustering")

    if not pc_cols:
        raise ValueError("No se encontraron columnas PC en la vista PCA clustering.")

    print(f"\nColumnas PC detectadas: {len(pc_cols):,}")

    X = df[pc_cols].copy()

    for col in pc_cols:
        X[col] = pd.to_numeric(X[col], errors="coerce")

    validate_matrix(X)

    print("\nEscalando PCs a rango [0, 1]...")

    scaler = MinMaxScaler()
    X_scaled = scaler.fit_transform(X)

    print(f"Matriz SOM escalada: {X_scaled.shape[0]:,} filas x {X_scaled.shape[1]:,} columnas")

    X_train = build_training_sample(
        X_scaled=X_scaled,
        sample_size=TRAIN_SAMPLE_SIZE,
        random_state=RANDOM_STATE,
    )

    print(f"\nDatos de entrenamiento SOM: {len(X_train):,} filas")
    print(f"Grid SOM: {SOM_X} x {SOM_Y} = {SOM_X * SOM_Y:,} nodos")
    print(f"Iteraciones: {N_ITERATIONS:,}")

    som = MiniSom(
        x=SOM_X,
        y=SOM_Y,
        input_len=X_scaled.shape[1],
        sigma=SIGMA,
        learning_rate=LEARNING_RATE,
        neighborhood_function="gaussian",
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

    print("\nAsignando BMU a todas las filas...")
    bmu_df = assign_bmus(som, X_scaled)

    bmu_out = pd.concat(
        [
            df[id_cols].reset_index(drop=True),
            bmu_df.reset_index(drop=True),
        ],
        axis=1,
    )

    # Conservar columnas de perfilado/contraste si existen
    profile_cols = [
        c for c in df.columns
        if c not in id_cols and not c.startswith("PC")
    ]

    if profile_cols:
        bmu_out = pd.concat(
            [
                bmu_out,
                df[profile_cols].reset_index(drop=True),
            ],
            axis=1,
        )

    print("Construyendo pesos del SOM...")
    weights_df = build_weights_df(som, pc_cols)

    print("Construyendo mapa de activación...")
    activation_df = build_activation_map(bmu_df, SOM_X, SOM_Y)

    print("Construyendo U-Matrix...")
    u_matrix_df = build_u_matrix_df(som)

    print("Calculando métricas SOM...")
    metrics = calculate_metrics(
        som=som,
        X_scaled=X_scaled,
        metrics_sample_size=METRICS_SAMPLE_SIZE,
        random_state=RANDOM_STATE,
        activation=activation_df,
    )

    bmu_out.to_csv(OUT_BMU, index=False, encoding="utf-8-sig")
    weights_df.to_csv(OUT_WEIGHTS, index=False, encoding="utf-8-sig")
    activation_df.to_csv(OUT_ACTIVATION, index=False, encoding="utf-8-sig")
    u_matrix_df.to_csv(OUT_U_MATRIX, index=False, encoding="utf-8-sig")

    joblib.dump(scaler, OUT_SCALER)
    joblib.dump(som, OUT_SOM_MODEL)

    with open(OUT_METRICS, "w", encoding="utf-8") as f:
        json.dump(metrics, f, ensure_ascii=False, indent=2)

    print(f"\nArchivos generados:")
    print(f"- {OUT_BMU}")
    print(f"- {OUT_WEIGHTS}")
    print(f"- {OUT_ACTIVATION}")
    print(f"- {OUT_U_MATRIX}")
    print(f"- {OUT_METRICS}")
    print(f"- {OUT_SCALER}")
    print(f"- {OUT_SOM_MODEL}")

    print("\nMétricas SOM:")
    for k, v in metrics.items():
        print(f"- {k}: {v}")

    print("\nProceso terminado.")


if __name__ == "__main__":
    main()