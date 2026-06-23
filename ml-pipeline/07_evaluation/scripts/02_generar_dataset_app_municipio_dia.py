# -*- coding: utf-8 -*-
"""
Evaluation 02 | Dataset principal para app municipio-día

Este script:
- Lee salidas cerradas de Modeling para municipio-día.
- Une identificadores, variables útiles y cluster final.
- Agrega nombres interpretables desde app_cluster_catalog.csv.
- Genera un dataset reducido para API/frontend.
- Genera una muestra ligera para pruebas de frontend.
- No reentrena modelos.
- No modifica archivos de Modeling.
"""

from pathlib import Path
import json
import pandas as pd


# ============================================================
# Configuración
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

MODELING_DIR = PROJECT_ROOT / "06_modeling"
EVALUATION_DIR = PROJECT_ROOT / "07_evaluation"

MODELING_DATASETS_DIR = MODELING_DIR / "datasets" / "municipio_dia"
MODELING_RESULTS_DIR = MODELING_DIR / "results" / "municipio_dia" / "som_kmeans"

EVAL_DATASETS_DIR = EVALUATION_DIR / "datasets"
EVAL_REPORTS_DIR = EVALUATION_DIR / "reports"

EVAL_DATASETS_DIR.mkdir(parents=True, exist_ok=True)
EVAL_REPORTS_DIR.mkdir(parents=True, exist_ok=True)

INPUT_BASE = MODELING_DATASETS_DIR / "modeling_municipio_dia_base.csv"
INPUT_IDS = MODELING_DATASETS_DIR / "modeling_municipio_dia_ids.csv"
INPUT_CLUSTERS = MODELING_RESULTS_DIR / "som_kmeans_observation_clusters.csv"
INPUT_CATALOG = EVAL_DATASETS_DIR / "app_cluster_catalog.csv"

OUTPUT_APP_DATASET = EVAL_DATASETS_DIR / "app_municipio_dia.csv"
OUTPUT_APP_SAMPLE = EVAL_DATASETS_DIR / "app_municipio_dia_sample.csv"
OUTPUT_DIAGNOSTICO = EVAL_REPORTS_DIR / "evaluation_02_diagnostico_dataset_app.csv"
OUTPUT_RESUMEN_JSON = EVAL_REPORTS_DIR / "evaluation_02_resumen_dataset_app.json"

CHUNKSIZE = 500_000
SAMPLE_MAX_ROWS = 20_000
RANDOM_STATE = 42


# ============================================================
# Utilidades
# ============================================================

def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = (
        df.columns
        .str.strip()
        .str.lower()
        .str.replace(" ", "_", regex=False)
    )
    return df


def read_header(path: Path) -> list[str]:
    if not path.exists():
        raise FileNotFoundError(f"No existe el archivo requerido: {path}")
    return pd.read_csv(path, nrows=0, encoding="utf-8-sig").columns.tolist()


def normalize_col_list(cols: list[str]) -> list[str]:
    return (
        pd.Series(cols)
        .str.strip()
        .str.lower()
        .str.replace(" ", "_", regex=False)
        .tolist()
    )


def select_existing_columns(columns: list[str], candidates: list[str]) -> list[str]:
    columns_set = set(columns)
    return [col for col in candidates if col in columns_set]


def find_cluster_column(columns: list[str]) -> str:
    candidates = [
        "cluster_id",
        "cluster",
        "kmeans_cluster",
        "som_kmeans_cluster",
        "cluster_kmeans",
    ]

    for col in candidates:
        if col in columns:
            return col

    possible = [col for col in columns if "cluster" in col]
    if possible:
        return possible[0]

    raise ValueError(
        "No se encontró columna de cluster en som_kmeans_observation_clusters.csv. "
        f"Columnas disponibles: {columns}"
    )


def add_validation(rows: list[dict], name: str, status: str, detail: str):
    rows.append({
        "validacion": name,
        "estado": status,
        "detalle": detail,
    })


def safe_to_numeric(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce")


def ensure_bool_int(df: pd.DataFrame, col: str):
    if col in df.columns:
        df[col] = safe_to_numeric(df[col]).fillna(0).astype("int8")


def create_id_observacion(df: pd.DataFrame, start_index: int) -> pd.Series:
    return pd.Series(
        range(start_index, start_index + len(df)),
        index=df.index,
        dtype="int64"
    )


# ============================================================
# Proceso principal
# ============================================================

def main():
    print("\nEvaluation 02 | Dataset principal para app")
    print("Flujo: municipio_dia")

    validations = []

    print("\nVerificando archivos requeridos...")

    for path_name, path in [
        ("base_modeling", INPUT_BASE),
        ("ids_modeling", INPUT_IDS),
        ("clusters_modeling", INPUT_CLUSTERS),
        ("catalogo_clusters", INPUT_CATALOG),
    ]:
        exists = path.exists()
        add_validation(
            validations,
            f"existe_{path_name}",
            "OK" if exists else "ERROR",
            str(path),
        )
        if not exists:
            raise FileNotFoundError(f"No existe archivo requerido: {path}")

    print("Leyendo encabezados...")

    base_cols_original = read_header(INPUT_BASE)
    ids_cols_original = read_header(INPUT_IDS)
    clusters_cols_original = read_header(INPUT_CLUSTERS)

    base_cols = normalize_col_list(base_cols_original)
    ids_cols = normalize_col_list(ids_cols_original)
    clusters_cols = normalize_col_list(clusters_cols_original)

    base_rename = dict(zip(base_cols_original, base_cols))
    ids_rename = dict(zip(ids_cols_original, ids_cols))
    clusters_rename = dict(zip(clusters_cols_original, clusters_cols))

    # Columnas útiles esperadas en IDs
    ids_candidates = [
        "fecha",
        "anio",
        "año",
        "mes",
        "dia",
        "entidad",
        "estado",
        "cve_ent",
        "municipio",
        "cve_mun",
        "cvegeo",
        "latitud_centroide",
        "longitud_centroide",
        "lat_centroide",
        "lon_centroide",
        "latitude",
        "longitude",
        "latitud",
        "longitud",
    ]

    # Columnas útiles esperadas en base/modeling
    base_candidates = [
        "has_firms",
        "has_conafor",
        "has_smn",
        "firms_count",
        "conafor_count",
        "smn_count",
        "frp_sum",
        "frp_mean",
        "brightness_mean",
        "bright_t31_mean",
        "tmin_c_mean",
        "tmax_c_mean",
        "precip_mm_sum",
        "precip_mm_mean",
        "evap_mm_sum",
        "evap_mm_mean",
        "total_hectareas_sum",
        "total_hectáreas_sum",
        "hectareas_total",
        "hectáreas_total",
        "area_afectada_sum",
    ]

    selected_ids_cols = select_existing_columns(ids_cols, ids_candidates)
    selected_base_cols = select_existing_columns(base_cols, base_candidates)

    cluster_col = find_cluster_column(clusters_cols)
    selected_cluster_cols = [cluster_col]

    print("\nColumnas seleccionadas:")
    print(f"- IDs: {len(selected_ids_cols)}")
    print(f"- Base: {len(selected_base_cols)}")
    print(f"- Cluster: {cluster_col}")

    add_validation(
        validations,
        "columnas_ids_detectadas",
        "OK" if len(selected_ids_cols) > 0 else "ERROR",
        f"{len(selected_ids_cols)} columnas: {selected_ids_cols}",
    )
    add_validation(
        validations,
        "columnas_base_detectadas",
        "OK" if len(selected_base_cols) > 0 else "WARNING",
        f"{len(selected_base_cols)} columnas: {selected_base_cols}",
    )
    add_validation(
        validations,
        "columna_cluster_detectada",
        "OK",
        cluster_col,
    )

    # Mapear nombres normalizados a nombres originales para usecols
    ids_usecols_original = [
        original for original, normalized in ids_rename.items()
        if normalized in selected_ids_cols
    ]

    base_usecols_original = [
        original for original, normalized in base_rename.items()
        if normalized in selected_base_cols
    ]

    clusters_usecols_original = [
        original for original, normalized in clusters_rename.items()
        if normalized in selected_cluster_cols
    ]

    print("\nLeyendo catálogo de clusters...")
    catalog = pd.read_csv(INPUT_CATALOG, encoding="utf-8-sig")
    catalog = normalize_columns(catalog)

    required_catalog_cols = ["cluster_id", "cluster_name"]
    missing_catalog_cols = [c for c in required_catalog_cols if c not in catalog.columns]

    if missing_catalog_cols:
        raise ValueError(
            "El catálogo de clusters no contiene columnas requeridas: "
            + ", ".join(missing_catalog_cols)
        )

    catalog_cols_to_merge = [
        col for col in [
            "cluster_id",
            "cluster_label",
            "cluster_name",
            "descripcion_corta",
            "nivel_actividad_firms",
            "nivel_confirmacion_conafor",
            "nivel_cobertura_smn",
            "color_sugerido",
            "orden_visualizacion",
        ]
        if col in catalog.columns
    ]

    catalog_merge = catalog[catalog_cols_to_merge].copy()
    catalog_merge["cluster_id"] = safe_to_numeric(catalog_merge["cluster_id"]).astype("int64")

    print("\nGenerando dataset app por chunks...")

    ids_iter = pd.read_csv(
        INPUT_IDS,
        usecols=ids_usecols_original,
        chunksize=CHUNKSIZE,
        encoding="utf-8-sig",
        low_memory=False,
    )

    base_iter = pd.read_csv(
        INPUT_BASE,
        usecols=base_usecols_original,
        chunksize=CHUNKSIZE,
        encoding="utf-8-sig",
        low_memory=False,
    )

    clusters_iter = pd.read_csv(
        INPUT_CLUSTERS,
        usecols=clusters_usecols_original,
        chunksize=CHUNKSIZE,
        encoding="utf-8-sig",
        low_memory=False,
    )

    total_rows = 0
    cluster_counts = {}
    sample_parts = []
    first_write = True
    chunk_number = 0

    if OUTPUT_APP_DATASET.exists():
        OUTPUT_APP_DATASET.unlink()

    for ids_chunk, base_chunk, clusters_chunk in zip(ids_iter, base_iter, clusters_iter):
        chunk_number += 1

        ids_chunk = normalize_columns(ids_chunk)
        base_chunk = normalize_columns(base_chunk)
        clusters_chunk = normalize_columns(clusters_chunk)

        if not (len(ids_chunk) == len(base_chunk) == len(clusters_chunk)):
            raise ValueError(
                f"Los chunks no tienen la misma longitud en chunk {chunk_number}: "
                f"ids={len(ids_chunk)}, base={len(base_chunk)}, clusters={len(clusters_chunk)}"
            )

        app_chunk = pd.concat(
            [
                ids_chunk.reset_index(drop=True),
                base_chunk.reset_index(drop=True),
                clusters_chunk.reset_index(drop=True),
            ],
            axis=1,
        )

        if cluster_col != "cluster_id":
            app_chunk = app_chunk.rename(columns={cluster_col: "cluster_id"})

        app_chunk["cluster_id"] = safe_to_numeric(app_chunk["cluster_id"]).astype("int64")

        app_chunk.insert(
            0,
            "id_observacion",
            create_id_observacion(app_chunk, total_rows + 1).values,
        )

        # Normalizaciones de nombres frecuentes
        rename_optional = {
            "año": "anio",
            "estado": "entidad",
            "lat_centroide": "latitud_centroide",
            "lon_centroide": "longitud_centroide",
            "latitude": "latitud_centroide",
            "longitude": "longitud_centroide",
            "latitud": "latitud_centroide",
            "longitud": "longitud_centroide",
            "total_hectáreas_sum": "total_hectareas_sum",
            "hectáreas_total": "total_hectareas_sum",
            "hectareas_total": "total_hectareas_sum",
            "area_afectada_sum": "total_hectareas_sum",
        }

        app_chunk = app_chunk.rename(
            columns={k: v for k, v in rename_optional.items() if k in app_chunk.columns}
        )

        # Derivar anio y mes si solo existe fecha
        if "fecha" in app_chunk.columns:
            fecha_dt = pd.to_datetime(app_chunk["fecha"], errors="coerce")

            if "anio" not in app_chunk.columns:
                app_chunk["anio"] = fecha_dt.dt.year

            if "mes" not in app_chunk.columns:
                app_chunk["mes"] = fecha_dt.dt.month

        # Flags en entero compacto
        for flag_col in ["has_firms", "has_conafor", "has_smn"]:
            ensure_bool_int(app_chunk, flag_col)

        app_chunk = app_chunk.merge(
            catalog_merge,
            on="cluster_id",
            how="left",
        )

        app_chunk["flujo_modelo"] = "municipio_dia"
        app_chunk["modelo_final"] = "PCA + SOM + KMeans"

        # Orden sugerido de columnas
        preferred_order = [
            "id_observacion",
            "fecha",
            "anio",
            "mes",
            "entidad",
            "cve_ent",
            "municipio",
            "cve_mun",
            "cvegeo",
            "latitud_centroide",
            "longitud_centroide",
            "cluster_id",
            "cluster_label",
            "cluster_name",
            "descripcion_corta",
            "nivel_actividad_firms",
            "nivel_confirmacion_conafor",
            "nivel_cobertura_smn",
            "has_firms",
            "has_conafor",
            "has_smn",
            "firms_count",
            "conafor_count",
            "smn_count",
            "frp_sum",
            "frp_mean",
            "brightness_mean",
            "bright_t31_mean",
            "tmin_c_mean",
            "tmax_c_mean",
            "precip_mm_sum",
            "precip_mm_mean",
            "evap_mm_sum",
            "evap_mm_mean",
            "total_hectareas_sum",
            "color_sugerido",
            "orden_visualizacion",
            "flujo_modelo",
            "modelo_final",
        ]

        ordered_cols = [col for col in preferred_order if col in app_chunk.columns]
        remaining_cols = [col for col in app_chunk.columns if col not in ordered_cols]
        app_chunk = app_chunk[ordered_cols + remaining_cols]

        app_chunk.to_csv(
            OUTPUT_APP_DATASET,
            mode="w" if first_write else "a",
            index=False,
            header=first_write,
            encoding="utf-8-sig",
        )

        first_write = False

        counts = app_chunk["cluster_id"].value_counts().to_dict()
        for cluster_id, count in counts.items():
            cluster_counts[int(cluster_id)] = cluster_counts.get(int(cluster_id), 0) + int(count)

        # Muestra estratificada tentativa por chunk
        frac = min(1.0, SAMPLE_MAX_ROWS / max(1, 11_154_221))
        sample_chunk = app_chunk.sample(
            frac=frac,
            random_state=RANDOM_STATE + chunk_number,
        )

        if not sample_chunk.empty:
            sample_parts.append(sample_chunk)

        total_rows += len(app_chunk)

        print(f"  Chunk {chunk_number} procesado | filas acumuladas: {total_rows:,}")

    print("\nGenerando muestra ligera...")

    if sample_parts:
        sample_df = pd.concat(sample_parts, ignore_index=True)

        if len(sample_df) > SAMPLE_MAX_ROWS:
            # Estratificación por cluster si es posible
            sample_df = (
                sample_df
                .groupby("cluster_id", group_keys=False)
                .apply(
                    lambda x: x.sample(
                        min(len(x), max(1, SAMPLE_MAX_ROWS // max(1, sample_df["cluster_id"].nunique()))),
                        random_state=RANDOM_STATE,
                    ),
                    include_groups=True,
                )
                .reset_index(drop=True)
            )

            if len(sample_df) > SAMPLE_MAX_ROWS:
                sample_df = sample_df.sample(SAMPLE_MAX_ROWS, random_state=RANDOM_STATE)

        sample_df.to_csv(OUTPUT_APP_SAMPLE, index=False, encoding="utf-8-sig")
    else:
        pd.DataFrame().to_csv(OUTPUT_APP_SAMPLE, index=False, encoding="utf-8-sig")

    print("\nValidando salidas...")

    output_exists = OUTPUT_APP_DATASET.exists()
    sample_exists = OUTPUT_APP_SAMPLE.exists()

    add_validation(
        validations,
        "dataset_app_generado",
        "OK" if output_exists else "ERROR",
        str(OUTPUT_APP_DATASET),
    )

    add_validation(
        validations,
        "sample_app_generado",
        "OK" if sample_exists else "ERROR",
        str(OUTPUT_APP_SAMPLE),
    )

    add_validation(
        validations,
        "filas_dataset_app",
        "OK" if total_rows > 0 else "ERROR",
        f"Filas generadas: {total_rows}",
    )

    add_validation(
        validations,
        "clusters_dataset_app",
        "OK" if len(cluster_counts) == 11 else "WARNING",
        f"Clusters detectados en dataset app: {sorted(cluster_counts.keys())}",
    )

    add_validation(
        validations,
        "sin_cluster_nulo",
        "OK",
        "cluster_id se convirtió a entero durante el procesamiento",
    )

    diagnostico = pd.DataFrame(validations)
    diagnostico.to_csv(OUTPUT_DIAGNOSTICO, index=False, encoding="utf-8-sig")

    resumen = {
        "fase_crisp_dm": "Evaluation",
        "flujo_principal": "municipio_dia",
        "modelo_final": "PCA + SOM + KMeans",
        "objetivo": "Generar dataset reducido para consumo de API/frontend",
        "archivo_dataset_app": str(OUTPUT_APP_DATASET),
        "archivo_sample_app": str(OUTPUT_APP_SAMPLE),
        "archivo_diagnostico": str(OUTPUT_DIAGNOSTICO),
        "filas_generadas": int(total_rows),
        "clusters_detectados": sorted([int(k) for k in cluster_counts.keys()]),
        "conteo_por_cluster": {str(k): int(v) for k, v in sorted(cluster_counts.items())},
        "validaciones_ok": int((diagnostico["estado"] == "OK").sum()),
        "warnings": int((diagnostico["estado"] == "WARNING").sum()),
        "errores": int((diagnostico["estado"] == "ERROR").sum()),
    }

    with open(OUTPUT_RESUMEN_JSON, "w", encoding="utf-8") as f:
        json.dump(resumen, f, ensure_ascii=False, indent=2)

    print("\nArchivos generados:")
    print(f"- {OUTPUT_APP_DATASET}")
    print(f"- {OUTPUT_APP_SAMPLE}")
    print(f"- {OUTPUT_DIAGNOSTICO}")
    print(f"- {OUTPUT_RESUMEN_JSON}")

    print("\nResumen:")
    print(f"- Filas generadas: {total_rows:,}")
    print(f"- Clusters detectados: {sorted(cluster_counts.keys())}")
    print(f"- Validaciones OK: {(diagnostico['estado'] == 'OK').sum()}")
    print(f"- Warnings: {(diagnostico['estado'] == 'WARNING').sum()}")
    print(f"- Errores: {(diagnostico['estado'] == 'ERROR').sum()}")

    if (diagnostico["estado"] == "ERROR").any():
        print("\nProceso terminado con errores. Revisa el diagnóstico.")
    else:
        print("\nProceso terminado correctamente.")


if __name__ == "__main__":
    main()