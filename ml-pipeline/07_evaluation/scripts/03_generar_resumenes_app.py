# -*- coding: utf-8 -*-
"""
Evaluation 03 | Resúmenes para app

Este script:
- Lee el dataset principal app_municipio_dia.csv.
- Genera resúmenes agregados para gráficas, filtros, panel derecho y consultas.
- Genera resúmenes por cluster, mes, entidad, municipio y combinaciones con cluster.
- Trabaja por chunks para no cargar 11M de filas completas en memoria.
- No reentrena modelos.
- No modifica Modeling ni Feature Engineering.
"""

from pathlib import Path
import json
import pandas as pd


# ============================================================
# Configuración
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

EVALUATION_DIR = PROJECT_ROOT / "07_evaluation"
EVAL_DATASETS_DIR = EVALUATION_DIR / "datasets"
EVAL_REPORTS_DIR = EVALUATION_DIR / "reports"

INPUT_APP_DATASET = EVAL_DATASETS_DIR / "app_municipio_dia.csv"

OUTPUT_RESUMEN_CLUSTER = EVAL_DATASETS_DIR / "app_resumen_cluster.csv"
OUTPUT_RESUMEN_MES = EVAL_DATASETS_DIR / "app_resumen_mes.csv"
OUTPUT_RESUMEN_ENTIDAD = EVAL_DATASETS_DIR / "app_resumen_entidad.csv"
OUTPUT_RESUMEN_MUNICIPIO = EVAL_DATASETS_DIR / "app_resumen_municipio.csv"
OUTPUT_RESUMEN_ENTIDAD_CLUSTER = EVAL_DATASETS_DIR / "app_resumen_entidad_cluster.csv"
OUTPUT_RESUMEN_MUNICIPIO_CLUSTER = EVAL_DATASETS_DIR / "app_resumen_municipio_cluster.csv"

OUTPUT_DIAGNOSTICO = EVAL_REPORTS_DIR / "evaluation_03_diagnostico_resumenes_app.csv"
OUTPUT_RESUMEN_JSON = EVAL_REPORTS_DIR / "evaluation_03_resumen_resumenes_app.json"

CHUNKSIZE = 500_000


# ============================================================
# Utilidades
# ============================================================

def normalize_columns_list(cols: list[str]) -> list[str]:
    return (
        pd.Series(cols)
        .str.strip()
        .str.lower()
        .str.replace(" ", "_", regex=False)
        .tolist()
    )


def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = normalize_columns_list(df.columns.tolist())
    return df


def add_validation(rows: list[dict], name: str, status: str, detail: str):
    rows.append({
        "validacion": name,
        "estado": status,
        "detalle": detail,
    })


def existing_columns(columns: list[str], candidates: list[str]) -> list[str]:
    return [col for col in candidates if col in columns]


def safe_numeric(df: pd.DataFrame, col: str):
    if col in df.columns:
        df[col] = pd.to_numeric(df[col], errors="coerce")


def prepare_chunk(df: pd.DataFrame) -> pd.DataFrame:
    df = normalize_columns(df)

    if "fecha" in df.columns and ("anio" not in df.columns or "mes" not in df.columns):
        fecha_dt = pd.to_datetime(df["fecha"], errors="coerce")

        if "anio" not in df.columns:
            df["anio"] = fecha_dt.dt.year

        if "mes" not in df.columns:
            df["mes"] = fecha_dt.dt.month

    for col in [
        "cluster_id",
        "anio",
        "mes",
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
    ]:
        safe_numeric(df, col)

    return df


def build_agg_dict(columns: list[str]) -> dict:
    agg = {}

    # Conteo base
    agg["id_observacion"] = "count"

    # Flags / conteos
    if "has_firms" in columns:
        agg["has_firms"] = "sum"
    if "has_conafor" in columns:
        agg["has_conafor"] = "sum"
    if "has_smn" in columns:
        agg["has_smn"] = "sum"

    if "firms_count" in columns:
        agg["firms_count"] = "sum"
    if "conafor_count" in columns:
        agg["conafor_count"] = "sum"
    if "smn_count" in columns:
        agg["smn_count"] = "sum"

    # Variables satelitales
    if "frp_sum" in columns:
        agg["frp_sum"] = "sum"
    if "frp_mean" in columns:
        agg["frp_mean"] = "mean"
    if "brightness_mean" in columns:
        agg["brightness_mean"] = "mean"
    if "bright_t31_mean" in columns:
        agg["bright_t31_mean"] = "mean"

    # Variables meteorológicas
    if "tmin_c_mean" in columns:
        agg["tmin_c_mean"] = "mean"
    if "tmax_c_mean" in columns:
        agg["tmax_c_mean"] = "mean"
    if "precip_mm_sum" in columns:
        agg["precip_mm_sum"] = "sum"
    if "precip_mm_mean" in columns:
        agg["precip_mm_mean"] = "mean"
    if "evap_mm_sum" in columns:
        agg["evap_mm_sum"] = "sum"
    if "evap_mm_mean" in columns:
        agg["evap_mm_mean"] = "mean"

    # CONAFOR
    if "total_hectareas_sum" in columns:
        agg["total_hectareas_sum"] = "sum"

    # Etiquetas visuales
    for col in [
        "cluster_label",
        "cluster_name",
        "nivel_actividad_firms",
        "nivel_confirmacion_conafor",
        "nivel_cobertura_smn",
        "color_sugerido",
        "orden_visualizacion",
    ]:
        if col in columns:
            agg[col] = "first"

    return agg


def rename_summary_columns(df: pd.DataFrame) -> pd.DataFrame:
    rename_map = {
        "id_observacion": "n_observaciones",
        "has_firms": "dias_con_firms",
        "has_conafor": "dias_con_conafor",
        "has_smn": "dias_con_smn",
        "firms_count": "firms_total",
        "conafor_count": "conafor_total",
        "smn_count": "smn_total",
        "frp_sum": "frp_total",
        "frp_mean": "frp_promedio",
        "brightness_mean": "brightness_promedio",
        "bright_t31_mean": "bright_t31_promedio",
        "tmin_c_mean": "tmin_promedio",
        "tmax_c_mean": "tmax_promedio",
        "precip_mm_sum": "precip_total",
        "precip_mm_mean": "precip_promedio",
        "evap_mm_sum": "evap_total",
        "evap_mm_mean": "evap_promedio",
        "total_hectareas_sum": "hectareas_total",
    }

    return df.rename(columns={k: v for k, v in rename_map.items() if k in df.columns})


def aggregate_summary(
    input_path: Path,
    group_cols: list[str],
    output_path: Path,
    summary_name: str,
    all_columns: list[str],
) -> dict:
    if not group_cols:
        return {
            "nombre": summary_name,
            "generado": False,
            "archivo": str(output_path),
            "filas": 0,
            "motivo": "Sin columnas de agrupación disponibles",
        }

    missing_group_cols = [col for col in group_cols if col not in all_columns]

    if missing_group_cols:
        return {
            "nombre": summary_name,
            "generado": False,
            "archivo": str(output_path),
            "filas": 0,
            "motivo": f"Faltan columnas: {missing_group_cols}",
        }

    print(f"\nGenerando {summary_name}...")
    print(f"Columnas de agrupación: {group_cols}")

    partials = []
    chunk_count = 0

    for chunk in pd.read_csv(
        input_path,
        chunksize=CHUNKSIZE,
        encoding="utf-8-sig",
        low_memory=False,
    ):
        chunk_count += 1
        chunk = prepare_chunk(chunk)

        agg_dict = build_agg_dict(chunk.columns.tolist())

        if "id_observacion" not in chunk.columns:
            chunk["id_observacion"] = 1
            agg_dict["id_observacion"] = "count"

        grouped = (
            chunk
            .groupby(group_cols, dropna=False, as_index=False)
            .agg(agg_dict)
        )

        partials.append(grouped)

        print(f"  Chunk {chunk_count} agregado")

    if not partials:
        return {
            "nombre": summary_name,
            "generado": False,
            "archivo": str(output_path),
            "filas": 0,
            "motivo": "No se generaron parciales",
        }

    combined = pd.concat(partials, ignore_index=True)

    final_agg = build_agg_dict(combined.columns.tolist())

    # Al reagrupar, las columnas tipo first deben seguir como first;
    # las ya agregadas deben conservar semántica correcta.
    for col in [
        "id_observacion",
        "has_firms",
        "has_conafor",
        "has_smn",
        "firms_count",
        "conafor_count",
        "smn_count",
        "frp_sum",
        "precip_mm_sum",
        "evap_mm_sum",
        "total_hectareas_sum",
    ]:
        if col in combined.columns:
            final_agg[col] = "sum"

    for col in [
        "frp_mean",
        "brightness_mean",
        "bright_t31_mean",
        "tmin_c_mean",
        "tmax_c_mean",
        "precip_mm_mean",
        "evap_mm_mean",
    ]:
        if col in combined.columns:
            final_agg[col] = "mean"

    final = (
        combined
        .groupby(group_cols, dropna=False, as_index=False)
        .agg(final_agg)
    )

    final = rename_summary_columns(final)

    # Orden visual si existe
    sort_cols = existing_columns(
        final.columns.tolist(),
        [
            "anio",
            "mes",
            "orden_visualizacion",
            "cluster_id",
            "cve_ent",
            "entidad",
            "cvegeo",
            "municipio",
        ],
    )

    if sort_cols:
        final = final.sort_values(sort_cols).reset_index(drop=True)

    final.to_csv(output_path, index=False, encoding="utf-8-sig")

    return {
        "nombre": summary_name,
        "generado": True,
        "archivo": str(output_path),
        "filas": int(len(final)),
        "motivo": "OK",
    }


# ============================================================
# Proceso principal
# ============================================================

def main():
    print("\nEvaluation 03 | Resúmenes para app")
    print("Flujo: municipio_dia")

    validations = []

    add_validation(
        validations,
        "existe_dataset_app",
        "OK" if INPUT_APP_DATASET.exists() else "ERROR",
        str(INPUT_APP_DATASET),
    )

    if not INPUT_APP_DATASET.exists():
        raise FileNotFoundError(f"No existe archivo requerido: {INPUT_APP_DATASET}")

    print("\nLeyendo encabezado del dataset app...")
    original_cols = pd.read_csv(INPUT_APP_DATASET, nrows=0, encoding="utf-8-sig").columns.tolist()
    all_columns = normalize_columns_list(original_cols)

    print(f"Columnas disponibles: {len(all_columns)}")
    print(all_columns)

    required_min_cols = ["cluster_id"]

    for col in required_min_cols:
        add_validation(
            validations,
            f"columna_requerida_{col}",
            "OK" if col in all_columns else "ERROR",
            col,
        )

    if "cluster_id" not in all_columns:
        raise ValueError("El dataset app no contiene cluster_id. No se pueden generar resúmenes.")

    # Definición flexible de dimensiones
    cluster_dims = ["cluster_id"]

    month_dims = existing_columns(all_columns, ["anio", "mes"])
    if not month_dims and "fecha" in all_columns:
        month_dims = ["fecha"]

    entidad_dims = existing_columns(all_columns, ["cve_ent", "entidad"])
    municipio_dims = existing_columns(all_columns, ["cvegeo", "cve_ent", "entidad", "cve_mun", "municipio"])

    entidad_cluster_dims = entidad_dims + ["cluster_id"] if entidad_dims else []
    municipio_cluster_dims = municipio_dims + ["cluster_id"] if municipio_dims else []

    summaries = []

    summaries.append(
        aggregate_summary(
            INPUT_APP_DATASET,
            cluster_dims,
            OUTPUT_RESUMEN_CLUSTER,
            "app_resumen_cluster",
            all_columns,
        )
    )

    summaries.append(
        aggregate_summary(
            INPUT_APP_DATASET,
            month_dims,
            OUTPUT_RESUMEN_MES,
            "app_resumen_mes",
            all_columns,
        )
    )

    summaries.append(
        aggregate_summary(
            INPUT_APP_DATASET,
            entidad_dims,
            OUTPUT_RESUMEN_ENTIDAD,
            "app_resumen_entidad",
            all_columns,
        )
    )

    summaries.append(
        aggregate_summary(
            INPUT_APP_DATASET,
            municipio_dims,
            OUTPUT_RESUMEN_MUNICIPIO,
            "app_resumen_municipio",
            all_columns,
        )
    )

    summaries.append(
        aggregate_summary(
            INPUT_APP_DATASET,
            entidad_cluster_dims,
            OUTPUT_RESUMEN_ENTIDAD_CLUSTER,
            "app_resumen_entidad_cluster",
            all_columns,
        )
    )

    summaries.append(
        aggregate_summary(
            INPUT_APP_DATASET,
            municipio_cluster_dims,
            OUTPUT_RESUMEN_MUNICIPIO_CLUSTER,
            "app_resumen_municipio_cluster",
            all_columns,
        )
    )

    for item in summaries:
        add_validation(
            validations,
            f"generado_{item['nombre']}",
            "OK" if item["generado"] else "WARNING",
            f"{item['archivo']} | filas={item['filas']} | {item['motivo']}",
        )

    diagnostico = pd.DataFrame(validations)
    diagnostico.to_csv(OUTPUT_DIAGNOSTICO, index=False, encoding="utf-8-sig")

    resumen = {
        "fase_crisp_dm": "Evaluation",
        "flujo_principal": "municipio_dia",
        "modelo_final": "PCA + SOM + KMeans",
        "objetivo": "Generar resúmenes agregados para app web",
        "dataset_origen": str(INPUT_APP_DATASET),
        "resumenes": summaries,
        "archivo_diagnostico": str(OUTPUT_DIAGNOSTICO),
        "validaciones_ok": int((diagnostico["estado"] == "OK").sum()),
        "warnings": int((diagnostico["estado"] == "WARNING").sum()),
        "errores": int((diagnostico["estado"] == "ERROR").sum()),
    }

    with open(OUTPUT_RESUMEN_JSON, "w", encoding="utf-8") as f:
        json.dump(resumen, f, ensure_ascii=False, indent=2)

    print("\nArchivos generados:")
    for item in summaries:
        if item["generado"]:
            print(f"- {item['archivo']}")

    print(f"- {OUTPUT_DIAGNOSTICO}")
    print(f"- {OUTPUT_RESUMEN_JSON}")

    print("\nResumen:")
    print(f"- Resúmenes generados: {sum(1 for x in summaries if x['generado'])}")
    print(f"- Resúmenes omitidos: {sum(1 for x in summaries if not x['generado'])}")
    print(f"- Validaciones OK: {(diagnostico['estado'] == 'OK').sum()}")
    print(f"- Warnings: {(diagnostico['estado'] == 'WARNING').sum()}")
    print(f"- Errores: {(diagnostico['estado'] == 'ERROR').sum()}")

    if (diagnostico["estado"] == "ERROR").any():
        print("\nProceso terminado con errores. Revisa el diagnóstico.")
    else:
        print("\nProceso terminado correctamente.")


if __name__ == "__main__":
    main()