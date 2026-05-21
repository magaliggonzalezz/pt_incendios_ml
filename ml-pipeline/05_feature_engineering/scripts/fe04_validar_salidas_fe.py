# -*- coding: utf-8 -*-
"""
Feature Engineering | 04 Validación de salidas FE
-------------------------------------------------
Valida formalmente las salidas generadas en 05_feature_engineering.

Este script:
- valida existencia de matrices FE,
- valida columnas mínimas,
- valida duplicados por llave espacio-temporal,
- valida fechas nulas o fuera del periodo del proyecto,
- valida llaves espaciales nulas,
- valida columnas totalmente nulas,
- valida columnas constantes,
- valida presencia de variables clave,
- genera un report de cierre en 05_feature_engineering/reports.

No modifica Integration.
No modifica datasets fuente.
No entrena modelos.
No evalúa modelos.
"""

from __future__ import annotations

import sys
import math
import importlib.util
from pathlib import Path

import pandas as pd


# =========================================================
# 1) CARGA DE CONFIGURACIÓN
# =========================================================

SCRIPT_DIR = Path(__file__).resolve().parent
CONFIG_PATH = SCRIPT_DIR / "fe00_config.py"

spec = importlib.util.spec_from_file_location("fe_config", CONFIG_PATH)
fe_config = importlib.util.module_from_spec(spec)

if spec is None or spec.loader is None:
    raise ImportError(f"No se pudo cargar configuración desde: {CONFIG_PATH}")

spec.loader.exec_module(fe_config)


ensure_fe_directories = fe_config.ensure_fe_directories

PROJECT_START_DATE = fe_config.PROJECT_START_DATE
PROJECT_END_DATE = fe_config.PROJECT_END_DATE

PATH_MUNICIPIO_DIA_BASE = fe_config.PATH_MUNICIPIO_DIA_BASE
PATH_ENTIDAD_DIA_BASE = fe_config.PATH_ENTIDAD_DIA_BASE

PATH_FE_MUNICIPIO_DIA_MATRIZ = fe_config.PATH_FE_MUNICIPIO_DIA_MATRIZ
PATH_FE_ENTIDAD_DIA_MATRIZ = fe_config.PATH_FE_ENTIDAD_DIA_MATRIZ
PATH_FE_VALIDACION_SALIDAS = fe_config.PATH_FE_VALIDACION_SALIDAS

MUNICIPIO_DUPLICATE_KEY = fe_config.MUNICIPIO_DUPLICATE_KEY
ENTIDAD_DUPLICATE_KEY = fe_config.ENTIDAD_DUPLICATE_KEY


# =========================================================
# 2) PARÁMETROS DE VALIDACIÓN
# =========================================================

CHUNKSIZE = 300_000

DATASETS_TO_VALIDATE = {
    "fe_municipio_dia_matriz": {
        "path": PATH_FE_MUNICIPIO_DIA_MATRIZ,
        "source_base_path": PATH_MUNICIPIO_DIA_BASE,
        "grain": "municipio_dia",
        "duplicate_key": MUNICIPIO_DUPLICATE_KEY,
        "required_cols": [
            "cve_ent",
            "nom_ent",
            "cve_mun",
            "nom_mun",
            "cvegeo",
            "fecha",
            "anio",
            "mes",
            "dia",
            "dia_del_anio",
            "semana_iso",
            "trimestre",
            "es_temporada_incendios",
            "has_conafor",
            "has_firms",
            "has_smn",
            "conafor_event_count",
        ],
        "spatial_key_cols": ["cve_ent", "cve_mun", "cvegeo"],
    },
    "fe_entidad_dia_matriz": {
        "path": PATH_FE_ENTIDAD_DIA_MATRIZ,
        "source_base_path": PATH_ENTIDAD_DIA_BASE,
        "grain": "entidad_dia",
        "duplicate_key": ENTIDAD_DUPLICATE_KEY,
        "required_cols": [
            "cve_ent",
            "nom_ent",
            "fecha",
            "anio",
            "mes",
            "dia",
            "dia_del_anio",
            "semana_iso",
            "trimestre",
            "es_temporada_incendios",
            "has_conafor",
            "has_firms",
            "has_smn",
            "conafor_event_count",
        ],
        "spatial_key_cols": ["cve_ent"],
    },
}


# =========================================================
# 3) UTILIDADES
# =========================================================

def add_result(
    rows: list[dict],
    dataset: str,
    validation: str,
    status: str,
    detail: str,
    value=None,
) -> None:
    rows.append({
        "dataset": dataset,
        "validacion": validation,
        "estatus": status,
        "detalle": detail,
        "valor": value,
    })


def safe_read_header(path: Path) -> list[str]:
    if not path.exists():
        return []

    return list(pd.read_csv(path, encoding="utf-8-sig", nrows=0).columns)


def count_rows_csv(path: Path, usecols: list[str] | None = None) -> int:
    total = 0

    reader = pd.read_csv(
        path,
        encoding="utf-8-sig",
        low_memory=False,
        chunksize=CHUNKSIZE,
        usecols=usecols,
    )

    for chunk in reader:
        total += len(chunk)

    return total


def validate_file_exists(rows: list[dict], dataset: str, path: Path) -> bool:
    if path.exists():
        add_result(rows, dataset, "existencia_archivo", "OK", "El archivo existe.", str(path))
        return True

    add_result(rows, dataset, "existencia_archivo", "ERROR", "El archivo no existe.", str(path))
    return False


def validate_required_columns(
    rows: list[dict],
    dataset: str,
    columns: list[str],
    required_cols: list[str],
) -> None:
    missing = sorted(set(required_cols) - set(columns))

    if missing:
        add_result(
            rows,
            dataset,
            "columnas_requeridas",
            "ERROR",
            "Faltan columnas requeridas.",
            "; ".join(missing),
        )
    else:
        add_result(
            rows,
            dataset,
            "columnas_requeridas",
            "OK",
            "Todas las columnas requeridas están presentes.",
            len(required_cols),
        )


def validate_duplicate_column_names(
    rows: list[dict],
    dataset: str,
    columns: list[str],
) -> None:
    duplicated = pd.Series(columns)[pd.Series(columns).duplicated()].tolist()

    if duplicated:
        add_result(
            rows,
            dataset,
            "columnas_duplicadas_por_nombre",
            "ERROR",
            "Existen nombres de columnas duplicados.",
            "; ".join(duplicated),
        )
    else:
        add_result(
            rows,
            dataset,
            "columnas_duplicadas_por_nombre",
            "OK",
            "No hay nombres de columnas duplicados.",
            0,
        )


def validate_row_count_against_base(
    rows: list[dict],
    dataset: str,
    fe_path: Path,
    source_base_path: Path,
    duplicate_key: list[str],
) -> None:
    fe_rows = count_rows_csv(fe_path, usecols=duplicate_key)
    base_rows = count_rows_csv(source_base_path, usecols=duplicate_key)

    if fe_rows == base_rows:
        add_result(
            rows,
            dataset,
            "conteo_filas_vs_base_integracion",
            "OK",
            "La matriz FE conserva el mismo número de filas que la base de Integration.",
            fe_rows,
        )
    else:
        add_result(
            rows,
            dataset,
            "conteo_filas_vs_base_integracion",
            "ERROR",
            "La matriz FE no conserva el mismo número de filas que la base de Integration.",
            f"FE={fe_rows}; Integration={base_rows}",
        )


def validate_keys_dates_and_duplicates(
    rows: list[dict],
    dataset: str,
    path: Path,
    duplicate_key: list[str],
    spatial_key_cols: list[str],
) -> None:
    start = pd.to_datetime(PROJECT_START_DATE)
    end = pd.to_datetime(PROJECT_END_DATE)

    total_rows = 0
    null_spatial_keys = 0
    null_dates = 0
    invalid_dates = 0
    outside_period = 0
    duplicate_rows = 0

    seen_hashes = set()

    usecols = list(dict.fromkeys(duplicate_key + spatial_key_cols + ["fecha"]))

    reader = pd.read_csv(
        path,
        encoding="utf-8-sig",
        low_memory=False,
        chunksize=CHUNKSIZE,
        usecols=usecols,
    )

    for chunk in reader:
        total_rows += len(chunk)

        for col in spatial_key_cols:
            if col in chunk.columns:
                null_spatial_keys += int(chunk[col].isna().sum())

        fechas = pd.to_datetime(chunk["fecha"], errors="coerce")
        null_dates += int(chunk["fecha"].isna().sum())
        invalid_dates += int(fechas.isna().sum())

        outside_period += int(((fechas < start) | (fechas > end)).sum())

        key_frame = chunk[duplicate_key].astype(str)
        hashes = pd.util.hash_pandas_object(key_frame, index=False).astype("uint64")

        for h in hashes:
            h_int = int(h)
            if h_int in seen_hashes:
                duplicate_rows += 1
            else:
                seen_hashes.add(h_int)

    if total_rows > 0:
        add_result(rows, dataset, "filas_totales", "OK", "El dataset contiene filas.", total_rows)
    else:
        add_result(rows, dataset, "filas_totales", "ERROR", "El dataset no contiene filas.", total_rows)

    if null_spatial_keys == 0:
        add_result(rows, dataset, "llaves_espaciales_nulas", "OK", "No hay llaves espaciales nulas.", 0)
    else:
        add_result(rows, dataset, "llaves_espaciales_nulas", "ERROR", "Hay llaves espaciales nulas.", null_spatial_keys)

    if null_dates == 0 and invalid_dates == 0:
        add_result(rows, dataset, "fechas_nulas_o_invalidas", "OK", "No hay fechas nulas o inválidas.", 0)
    else:
        add_result(
            rows,
            dataset,
            "fechas_nulas_o_invalidas",
            "ERROR",
            "Hay fechas nulas o inválidas.",
            f"nulas={null_dates}; invalidas={invalid_dates}",
        )

    if outside_period == 0:
        add_result(rows, dataset, "fechas_fuera_periodo", "OK", "No hay fechas fuera del periodo 2001-2025.", 0)
    else:
        add_result(rows, dataset, "fechas_fuera_periodo", "ERROR", "Hay fechas fuera del periodo 2001-2025.", outside_period)

    if duplicate_rows == 0:
        add_result(
            rows,
            dataset,
            "duplicados_llave_espacio_temporal",
            "OK",
            f"No hay duplicados por llave {duplicate_key}.",
            0,
        )
    else:
        add_result(
            rows,
            dataset,
            "duplicados_llave_espacio_temporal",
            "ERROR",
            f"Hay duplicados por llave {duplicate_key}.",
            duplicate_rows,
        )


def validate_null_and_constant_columns(
    rows: list[dict],
    dataset: str,
    path: Path,
    columns: list[str],
) -> None:
    non_null_counts = {col: 0 for col in columns}
    first_value = {col: None for col in columns}
    has_first_value = {col: False for col in columns}
    changed_value = {col: False for col in columns}

    reader = pd.read_csv(
        path,
        encoding="utf-8-sig",
        low_memory=False,
        chunksize=CHUNKSIZE,
    )

    for chunk in reader:
        for col in columns:
            s = chunk[col]
            non_null = s.dropna()
            non_null_counts[col] += len(non_null)

            if non_null.empty:
                continue

            if not has_first_value[col]:
                first_value[col] = str(non_null.iloc[0])
                has_first_value[col] = True

            if not changed_value[col]:
                different = non_null.astype(str) != first_value[col]
                if different.any():
                    changed_value[col] = True

    all_null_cols = [col for col in columns if non_null_counts[col] == 0]
    constant_cols = [
        col
        for col in columns
        if non_null_counts[col] > 0 and not changed_value[col]
    ]

    if all_null_cols:
        add_result(
            rows,
            dataset,
            "columnas_totalmente_nulas",
            "WARNING",
            "Existen columnas totalmente nulas. Revisar si deben excluirse.",
            "; ".join(all_null_cols[:50]),
        )
    else:
        add_result(
            rows,
            dataset,
            "columnas_totalmente_nulas",
            "OK",
            "No hay columnas totalmente nulas.",
            0,
        )

    if constant_cols:
        add_result(
            rows,
            dataset,
            "columnas_constantes",
            "WARNING",
            "Existen columnas constantes. Revisar si deben excluirse antes de Modeling.",
            f"{len(constant_cols)} columnas",
        )
    else:
        add_result(
            rows,
            dataset,
            "columnas_constantes",
            "OK",
            "No hay columnas constantes.",
            0,
        )


def validate_forbidden_columns(
    rows: list[dict],
    dataset: str,
    columns: list[str],
) -> None:
    forbidden_cols = [
        "conafor_total_hectareas_mean",
        "conafor_total_hectareas_sum",
    ]

    present = [col for col in forbidden_cols if col in columns]

    if present:
        add_result(
            rows,
            dataset,
            "columnas_excluidas_por_decision_metodologica",
            "ERROR",
            "Columnas excluidas metodológicamente siguen presentes.",
            "; ".join(present),
        )
    else:
        add_result(
            rows,
            dataset,
            "columnas_excluidas_por_decision_metodologica",
            "OK",
            "No están presentes columnas excluidas metodológicamente.",
            0,
        )


def validate_dataset(dataset_name: str, cfg: dict) -> list[dict]:
    rows = []

    path = cfg["path"]
    source_base_path = cfg["source_base_path"]
    duplicate_key = cfg["duplicate_key"]
    required_cols = cfg["required_cols"]
    spatial_key_cols = cfg["spatial_key_cols"]

    print(f"\nValidando: {dataset_name}")
    print(f"Archivo: {path}")

    if not validate_file_exists(rows, dataset_name, path):
        return rows

    columns = safe_read_header(path)

    add_result(
        rows,
        dataset_name,
        "numero_columnas",
        "OK",
        "Número de columnas detectadas.",
        len(columns),
    )

    validate_duplicate_column_names(rows, dataset_name, columns)
    validate_required_columns(rows, dataset_name, columns, required_cols)
    validate_forbidden_columns(rows, dataset_name, columns)

    print("Validando conteo de filas contra base Integration...")
    validate_row_count_against_base(
        rows=rows,
        dataset=dataset_name,
        fe_path=path,
        source_base_path=source_base_path,
        duplicate_key=duplicate_key,
    )

    print("Validando llaves, fechas y duplicados...")
    validate_keys_dates_and_duplicates(
        rows=rows,
        dataset=dataset_name,
        path=path,
        duplicate_key=duplicate_key,
        spatial_key_cols=spatial_key_cols,
    )

    print("Validando columnas nulas y constantes...")
    validate_null_and_constant_columns(
        rows=rows,
        dataset=dataset_name,
        path=path,
        columns=columns,
    )

    return rows


# =========================================================
# 4) PIPELINE PRINCIPAL
# =========================================================

def main() -> None:
    print("\nFeature Engineering 04 | Validación de salidas FE")

    ensure_fe_directories()

    all_rows = []

    for dataset_name, cfg in DATASETS_TO_VALIDATE.items():
        rows = validate_dataset(dataset_name, cfg)
        all_rows.extend(rows)

    report = pd.DataFrame(all_rows)

    report.to_csv(
        PATH_FE_VALIDACION_SALIDAS,
        index=False,
        encoding="utf-8-sig",
    )

    total = len(report)
    errors = int((report["estatus"] == "ERROR").sum())
    warnings = int((report["estatus"] == "WARNING").sum())
    ok = int((report["estatus"] == "OK").sum())

    print("\nArchivo generado:")
    print(f"- {PATH_FE_VALIDACION_SALIDAS}")

    print("\nResumen:")
    print(f"- Validaciones totales: {total:,}")
    print(f"- OK: {ok:,}")
    print(f"- Warnings: {warnings:,}")
    print(f"- Errores: {errors:,}")

    if errors > 0:
        print("\nResultado: Feature Engineering NO queda cerrado. Revisar errores.")
    elif warnings > 0:
        print("\nResultado: Feature Engineering queda técnicamente generado, pero requiere revisar warnings.")
    else:
        print("\nResultado: Feature Engineering queda validado sin errores ni warnings.")

    print("\nProceso terminado.")


if __name__ == "__main__":
    main()