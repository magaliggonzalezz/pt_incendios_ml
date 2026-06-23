# -*- coding: utf-8 -*-
"""
Feature Engineering | 02 Construcción de matriz municipio-día
------------------------------------------------------------
Construye la matriz principal de Feature Engineering a granularidad municipio-día
a partir de las salidas validadas de Integration.

Este script:
- lee la base dinámica municipio-día,
- une contexto municipal INEGI,
- une contexto municipal INFyS,
- genera variables temporales derivadas,
- genera variables meteorológicas básicas,
- excluye columnas problemáticas, constantes, totalmente nulas o de trazabilidad interna,
- conserva columnas de identificación para trazabilidad,
- conserva variables CONAFOR como target/proxy potencial, no como features directas,
- escribe la matriz en 05_feature_engineering/datasets.
"""

from __future__ import annotations

import gc
import sys
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
PATH_INEGI_MUNICIPIO_CONTEXTO = fe_config.PATH_INEGI_MUNICIPIO_CONTEXTO
PATH_INFYS_MUNICIPIO_CONTEXTO = fe_config.PATH_INFYS_MUNICIPIO_CONTEXTO

PATH_FE_MUNICIPIO_DIA_MATRIZ = fe_config.PATH_FE_MUNICIPIO_DIA_MATRIZ
PATH_FE_DIAGNOSTICO_VARIABLES_BASE = fe_config.PATH_FE_DIAGNOSTICO_VARIABLES_BASE

MUNICIPIO_KEY_COLS = fe_config.MUNICIPIO_KEY_COLS
MUNICIPIO_DUPLICATE_KEY = fe_config.MUNICIPIO_DUPLICATE_KEY

TRACEABILITY_COL_PATTERNS = fe_config.TRACEABILITY_COL_PATTERNS


# =========================================================
# 2) PARÁMETROS DEL SCRIPT
# =========================================================

CHUNKSIZE = 500_000

DATASET_BASE_NAME = "municipio_dia_base"
DATASET_INEGI_NAME = "inegi_municipio_contexto"
DATASET_INFYS_NAME = "infys_municipio_contexto"

EXCLUDE_EXPLICIT_COLS = {
    # CONAFOR superficie no usable por diagnóstico FE-01
    "conafor_total_hectareas_mean",
    "conafor_total_hectareas_sum",

    # columnas que no deben duplicarse desde contexto
    "nom_ent",
    "nom_mun",
}

TARGET_PROXY_COLS = {
    "has_conafor",
    "conafor_event_count",
}

SOURCE_FLAG_COLS = {
    "has_conafor",
    "has_firms",
    "has_smn",
}

BASE_REQUIRED_COLS = {
    "cve_ent",
    "nom_ent",
    "cve_mun",
    "nom_mun",
    "cvegeo",
    "fecha",
}

CONTEXT_KEY_COL = "cvegeo"


# =========================================================
# 3) UTILIDADES
# =========================================================

def normalize_key_cvegeo(series: pd.Series) -> pd.Series:
    """
    Normaliza cvegeo como texto de 5 caracteres.
    """
    s = series.astype(str).str.strip()
    s = s.str.replace(r"\.0$", "", regex=True)
    return s.str.zfill(5)


def normalize_cve_ent(series: pd.Series) -> pd.Series:
    """
    Normaliza clave de entidad como texto de 2 caracteres.
    """
    s = series.astype(str).str.strip()
    s = s.str.replace(r"\.0$", "", regex=True)
    return s.str.zfill(2)


def normalize_cve_mun(series: pd.Series) -> pd.Series:
    """
    Normaliza clave de municipio como texto de 3 caracteres.
    """
    s = series.astype(str).str.strip()
    s = s.str.replace(r"\.0$", "", regex=True)
    return s.str.zfill(3)


def contains_traceability_pattern(col: str) -> bool:
    """
    Detecta columnas de trazabilidad interna por nombre.
    """
    low = col.lower()
    return any(pattern.lower() in low for pattern in TRACEABILITY_COL_PATTERNS)


def safe_read_csv(path: Path, **kwargs) -> pd.DataFrame:
    """
    Lee un CSV validando existencia.
    """
    if not path.exists():
        raise FileNotFoundError(f"No existe archivo de entrada: {path}")

    return pd.read_csv(path, encoding="utf-8-sig", low_memory=False, **kwargs)


def validate_required_columns(df: pd.DataFrame, required_cols: set[str], dataset_name: str) -> None:
    """
    Valida columnas requeridas.
    """
    missing = sorted(required_cols - set(df.columns))
    if missing:
        raise ValueError(f"{dataset_name} no contiene columnas requeridas: {missing}")


def load_diagnostic() -> pd.DataFrame:
    """
    Carga el diagnóstico FE-01 para tomar decisiones de exclusión.
    """
    if not PATH_FE_DIAGNOSTICO_VARIABLES_BASE.exists():
        raise FileNotFoundError(
            "No existe el diagnóstico FE-01. Ejecuta primero "
            f"{PATH_FE_DIAGNOSTICO_VARIABLES_BASE}"
        )

    return pd.read_csv(
        PATH_FE_DIAGNOSTICO_VARIABLES_BASE,
        encoding="utf-8-sig",
        low_memory=False,
    )


def select_context_columns(
    diagnostic: pd.DataFrame,
    dataset_name: str,
    context_df: pd.DataFrame,
    key_col: str,
) -> list[str]:
    """
    Selecciona columnas de contexto a conservar según diagnóstico FE-01.
    """
    diag = diagnostic[diagnostic["dataset"] == dataset_name].copy()

    if diag.empty:
        raise ValueError(f"No hay diagnóstico disponible para: {dataset_name}")

    keep_cols = [key_col]

    for _, row in diag.iterrows():
        col = row["columna"]

        if col not in context_df.columns:
            continue

        if col == key_col:
            continue

        if col in EXCLUDE_EXPLICIT_COLS:
            continue

        if bool(row.get("columna_totalmente_nula", False)):
            continue

        if bool(row.get("es_constante", False)):
            continue

        if str(row.get("estatus_feature", "")) == "no_feature_trazabilidad":
            continue

        if contains_traceability_pattern(col):
            continue

        keep_cols.append(col)

    keep_cols = list(dict.fromkeys(keep_cols))
    return keep_cols


def select_base_columns(
    diagnostic: pd.DataFrame,
    base_columns: list[str],
) -> list[str]:
    """
    Selecciona columnas de la base municipio-día a conservar.
    """
    diag = diagnostic[diagnostic["dataset"] == DATASET_BASE_NAME].copy()

    if diag.empty:
        raise ValueError(f"No hay diagnóstico disponible para: {DATASET_BASE_NAME}")

    keep_cols = []

    for col in base_columns:
        if col in BASE_REQUIRED_COLS:
            keep_cols.append(col)
            continue

        if col in EXCLUDE_EXPLICIT_COLS:
            continue

        if contains_traceability_pattern(col):
            continue

        row = diag[diag["columna"] == col]

        if row.empty:
            keep_cols.append(col)
            continue

        row0 = row.iloc[0]

        if bool(row0.get("columna_totalmente_nula", False)):
            continue

        if bool(row0.get("es_constante", False)) and col not in SOURCE_FLAG_COLS:
            continue

        keep_cols.append(col)

    keep_cols = list(dict.fromkeys(keep_cols))
    return keep_cols


def load_context(
    path: Path,
    diagnostic: pd.DataFrame,
    dataset_name: str,
) -> pd.DataFrame:
    """
    Carga y depura un contexto municipal.
    """
    df = safe_read_csv(path)

    if CONTEXT_KEY_COL not in df.columns:
        raise ValueError(f"{dataset_name} no contiene llave {CONTEXT_KEY_COL}")

    df[CONTEXT_KEY_COL] = normalize_key_cvegeo(df[CONTEXT_KEY_COL])

    dup = df.duplicated(subset=[CONTEXT_KEY_COL], keep=False).sum()
    if dup > 0:
        raise ValueError(
            f"{dataset_name} tiene llaves duplicadas por {CONTEXT_KEY_COL}: {dup:,}"
        )

    keep_cols = select_context_columns(
        diagnostic=diagnostic,
        dataset_name=dataset_name,
        context_df=df,
        key_col=CONTEXT_KEY_COL,
    )

    df = df[keep_cols].copy()

    print(f"{dataset_name}: columnas conservadas {len(df.columns):,}")

    return df


def add_temporal_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Agrega variables temporales derivadas desde fecha.
    """
    fecha = pd.to_datetime(df["fecha"], errors="coerce")

    df["anio"] = fecha.dt.year.astype("Int64")
    df["mes"] = fecha.dt.month.astype("Int64")
    df["dia"] = fecha.dt.day.astype("Int64")
    df["dia_del_anio"] = fecha.dt.dayofyear.astype("Int64")
    df["semana_iso"] = fecha.dt.isocalendar().week.astype("Int64")
    df["trimestre"] = fecha.dt.quarter.astype("Int64")

    # Temporada operativa simple para México:
    # meses 1-6 suelen concentrar la temporada crítica de incendios.
    df["es_temporada_incendios"] = df["mes"].isin([1, 2, 3, 4, 5, 6]).astype("int8")

    return df


def add_meteo_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Agrega variables meteorológicas básicas sin imputar datos.
    """
    tmax_col = "smn_tmax_c_mean"
    tmin_col = "smn_tmin_c_mean"

    if tmax_col in df.columns and tmin_col in df.columns:
        tmax = pd.to_numeric(df[tmax_col], errors="coerce")
        tmin = pd.to_numeric(df[tmin_col], errors="coerce")

        df["smn_temp_media_c"] = (tmax + tmin) / 2
        df["smn_amplitud_termica_c"] = tmax - tmin

    return df


def add_log_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Agrega transformaciones log1p para conteos y acumulados seleccionados.
    """
    candidate_cols = [
        "firms_count",
        "firms_frp_sum",
        "firms_day_count",
        "firms_night_count",
        "conafor_event_count",
    ]

    for col in candidate_cols:
        if col not in df.columns:
            continue

        values = pd.to_numeric(df[col], errors="coerce")

        # Evita log de negativos si existiera algún valor inválido.
        if (values.dropna() < 0).any():
            continue

        df[f"{col}_log1p"] = values.apply(lambda x: pd.NA if pd.isna(x) else __import__("math").log1p(x))

    return df


def reorder_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    Ordena columnas por trazabilidad, tiempo y variables.
    """
    preferred_first = [
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
    ]

    first_cols = [c for c in preferred_first if c in df.columns]
    other_cols = [c for c in df.columns if c not in first_cols]

    return df[first_cols + other_cols]


def validate_chunk_keys(df: pd.DataFrame) -> None:
    """
    Valida llaves básicas del chunk.
    """
    validate_required_columns(df, BASE_REQUIRED_COLS, "chunk municipio_dia_base")

    if df["cvegeo"].isna().any():
        raise ValueError("Hay cvegeo nulos en un chunk de municipio_dia_base.")

    if df["fecha"].isna().any():
        raise ValueError("Hay fechas nulas en un chunk de municipio_dia_base.")


def process_chunk(
    chunk: pd.DataFrame,
    base_keep_cols: list[str],
    inegi_context: pd.DataFrame,
    infys_context: pd.DataFrame,
) -> pd.DataFrame:
    """
    Procesa un chunk de la base municipio-día.
    """
    chunk = chunk[base_keep_cols].copy()

    chunk["cve_ent"] = normalize_cve_ent(chunk["cve_ent"])
    chunk["cve_mun"] = normalize_cve_mun(chunk["cve_mun"])
    chunk["cvegeo"] = normalize_key_cvegeo(chunk["cvegeo"])

    chunk["fecha"] = pd.to_datetime(chunk["fecha"], errors="coerce").dt.strftime("%Y-%m-%d")

    validate_chunk_keys(chunk)

    chunk = add_temporal_features(chunk)
    chunk = add_meteo_features(chunk)
    chunk = add_log_features(chunk)

    chunk = chunk.merge(
        inegi_context,
        on=CONTEXT_KEY_COL,
        how="left",
        validate="many_to_one",
    )

    chunk = chunk.merge(
        infys_context,
        on=CONTEXT_KEY_COL,
        how="left",
        validate="many_to_one",
    )

    chunk = reorder_columns(chunk)

    return chunk


# =========================================================
# 4) PIPELINE PRINCIPAL
# =========================================================

def main() -> None:
    print("\nFeature Engineering 02 | Construcción matriz municipio-día")

    ensure_fe_directories()

    print("\nCargando diagnóstico FE-01...")
    diagnostic = load_diagnostic()

    print("Cargando contexto INEGI municipal...")
    inegi_context = load_context(
        path=PATH_INEGI_MUNICIPIO_CONTEXTO,
        diagnostic=diagnostic,
        dataset_name=DATASET_INEGI_NAME,
    )

    print("Cargando contexto INFyS municipal...")
    infys_context = load_context(
        path=PATH_INFYS_MUNICIPIO_CONTEXTO,
        diagnostic=diagnostic,
        dataset_name=DATASET_INFYS_NAME,
    )

    print("\nRevisando columnas de base municipio-día...")
    base_header = pd.read_csv(
        PATH_MUNICIPIO_DIA_BASE,
        encoding="utf-8-sig",
        nrows=0,
    )

    base_keep_cols = select_base_columns(
        diagnostic=diagnostic,
        base_columns=list(base_header.columns),
    )

    missing_base = BASE_REQUIRED_COLS - set(base_keep_cols)
    if missing_base:
        raise ValueError(f"Columnas base requeridas excluidas por error: {sorted(missing_base)}")

    print(f"Columnas base conservadas: {len(base_keep_cols):,}")

    if PATH_FE_MUNICIPIO_DIA_MATRIZ.exists():
        PATH_FE_MUNICIPIO_DIA_MATRIZ.unlink()

    total_rows = 0
    total_chunks = 0
    output_columns = None

    print("\nProcesando municipio-día por chunks...")

    reader = pd.read_csv(
        PATH_MUNICIPIO_DIA_BASE,
        encoding="utf-8-sig",
        low_memory=False,
        chunksize=CHUNKSIZE,
    )

    for chunk_idx, chunk in enumerate(reader, start=1):
        processed = process_chunk(
            chunk=chunk,
            base_keep_cols=base_keep_cols,
            inegi_context=inegi_context,
            infys_context=infys_context,
        )

        if output_columns is None:
            output_columns = list(processed.columns)
        else:
            if list(processed.columns) != output_columns:
                raise ValueError("Las columnas de salida cambiaron entre chunks.")

        write_header = chunk_idx == 1

        processed.to_csv(
            PATH_FE_MUNICIPIO_DIA_MATRIZ,
            index=False,
            encoding="utf-8-sig",
            mode="w" if write_header else "a",
            header=write_header,
        )

        total_rows += len(processed)
        total_chunks += 1

        print(
            f"Chunk {chunk_idx:,} procesado | "
            f"filas chunk: {len(processed):,} | "
            f"filas acumuladas: {total_rows:,}"
        )

        del chunk
        del processed
        gc.collect()

    print("\nArchivo generado:")
    print(f"- {PATH_FE_MUNICIPIO_DIA_MATRIZ}")

    print("\nResumen:")
    print(f"- Chunks procesados: {total_chunks:,}")
    print(f"- Filas escritas: {total_rows:,}")
    print(f"- Columnas finales: {len(output_columns) if output_columns else 0:,}")

    print("\nProceso terminado.")


if __name__ == "__main__":
    main()