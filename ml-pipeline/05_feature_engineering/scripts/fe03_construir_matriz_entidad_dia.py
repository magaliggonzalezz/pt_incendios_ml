# -*- coding: utf-8 -*-
"""
Feature Engineering | 03 Construcción de matriz entidad-día
----------------------------------------------------------
Construye la matriz complementaria de Feature Engineering a granularidad entidad-día
a partir de las salidas validadas de Integration.

Este script:
- lee la base dinámica entidad-día,
- une contexto estatal INEGI,
- une contexto estatal INFyS,
- genera variables temporales derivadas,
- genera variables meteorológicas básicas,
- excluye columnas problemáticas, constantes, totalmente nulas o de trazabilidad interna,
- conserva columnas de identificación para trazabilidad,
- conserva variables CONAFOR como target/proxy potencial, no como features directas,
- escribe la matriz en 05_feature_engineering/datasets.
"""

from __future__ import annotations

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

PATH_ENTIDAD_DIA_BASE = fe_config.PATH_ENTIDAD_DIA_BASE
PATH_INEGI_ENTIDAD_CONTEXTO = fe_config.PATH_INEGI_ENTIDAD_CONTEXTO
PATH_INFYS_ENTIDAD_CONTEXTO = fe_config.PATH_INFYS_ENTIDAD_CONTEXTO

PATH_FE_ENTIDAD_DIA_MATRIZ = fe_config.PATH_FE_ENTIDAD_DIA_MATRIZ
PATH_FE_DIAGNOSTICO_VARIABLES_BASE = fe_config.PATH_FE_DIAGNOSTICO_VARIABLES_BASE

ENTIDAD_KEY_COLS = fe_config.ENTIDAD_KEY_COLS
ENTIDAD_DUPLICATE_KEY = fe_config.ENTIDAD_DUPLICATE_KEY

TRACEABILITY_COL_PATTERNS = fe_config.TRACEABILITY_COL_PATTERNS


# =========================================================
# 2) PARÁMETROS DEL SCRIPT
# =========================================================

DATASET_BASE_NAME = "entidad_dia_base"
DATASET_INEGI_NAME = "inegi_entidad_contexto"
DATASET_INFYS_NAME = "infys_entidad_contexto"

EXCLUDE_EXPLICIT_COLS = {
    # CONAFOR superficie no usable por diagnóstico FE-01
    "conafor_total_hectareas_mean",
    "conafor_total_hectareas_sum",

    # columnas que no deben duplicarse desde contexto
    "nom_ent",
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
    "fecha",
}

CONTEXT_KEY_COL = "cve_ent"


# =========================================================
# 3) UTILIDADES
# =========================================================

def normalize_cve_ent(series: pd.Series) -> pd.Series:
    """
    Normaliza clave de entidad como texto de 2 caracteres.
    """
    s = series.astype(str).str.strip()
    s = s.str.replace(r"\.0$", "", regex=True)
    return s.str.zfill(2)


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
    Selecciona columnas de la base entidad-día a conservar.
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
    Carga y depura un contexto estatal.
    """
    df = safe_read_csv(path)

    if CONTEXT_KEY_COL not in df.columns:
        raise ValueError(f"{dataset_name} no contiene llave {CONTEXT_KEY_COL}")

    df[CONTEXT_KEY_COL] = normalize_cve_ent(df[CONTEXT_KEY_COL])

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
    import numpy as np

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

        df[f"{col}_log1p"] = np.log1p(values)

    return df


def reorder_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    Ordena columnas por trazabilidad, tiempo y variables.
    """
    preferred_first = [
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
    ]

    first_cols = [c for c in preferred_first if c in df.columns]
    other_cols = [c for c in df.columns if c not in first_cols]

    return df[first_cols + other_cols]


def validate_final_matrix(df: pd.DataFrame) -> None:
    """
    Valida la matriz entidad-día antes de exportar.
    """
    validate_required_columns(df, BASE_REQUIRED_COLS, "fe_entidad_dia_matriz")

    if df["cve_ent"].isna().any():
        raise ValueError("Hay cve_ent nulos en fe_entidad_dia_matriz.")

    if df["fecha"].isna().any():
        raise ValueError("Hay fechas nulas en fe_entidad_dia_matriz.")

    duplicate_rows = df.duplicated(subset=ENTIDAD_DUPLICATE_KEY, keep=False).sum()
    if duplicate_rows > 0:
        raise ValueError(
            f"Hay filas duplicadas por {ENTIDAD_DUPLICATE_KEY}: {duplicate_rows:,}"
        )

    fechas = pd.to_datetime(df["fecha"], errors="coerce")
    start = pd.to_datetime(PROJECT_START_DATE)
    end = pd.to_datetime(PROJECT_END_DATE)

    fuera_periodo = ((fechas < start) | (fechas > end)).sum()
    if fuera_periodo > 0:
        raise ValueError(f"Hay fechas fuera del periodo del proyecto: {fuera_periodo:,}")


# =========================================================
# 4) PIPELINE PRINCIPAL
# =========================================================

def main() -> None:
    print("\nFeature Engineering 03 | Construcción matriz entidad-día")

    ensure_fe_directories()

    print("\nCargando diagnóstico FE-01...")
    diagnostic = load_diagnostic()

    print("Cargando contexto INEGI estatal...")
    inegi_context = load_context(
        path=PATH_INEGI_ENTIDAD_CONTEXTO,
        diagnostic=diagnostic,
        dataset_name=DATASET_INEGI_NAME,
    )

    print("Cargando contexto INFyS estatal...")
    infys_context = load_context(
        path=PATH_INFYS_ENTIDAD_CONTEXTO,
        diagnostic=diagnostic,
        dataset_name=DATASET_INFYS_NAME,
    )

    print("\nCargando base entidad-día...")
    base = safe_read_csv(PATH_ENTIDAD_DIA_BASE)

    validate_required_columns(base, BASE_REQUIRED_COLS, "entidad_dia_base")

    base_keep_cols = select_base_columns(
        diagnostic=diagnostic,
        base_columns=list(base.columns),
    )

    missing_base = BASE_REQUIRED_COLS - set(base_keep_cols)
    if missing_base:
        raise ValueError(f"Columnas base requeridas excluidas por error: {sorted(missing_base)}")

    print(f"Columnas base conservadas: {len(base_keep_cols):,}")

    df = base[base_keep_cols].copy()

    del base

    df["cve_ent"] = normalize_cve_ent(df["cve_ent"])
    df["fecha"] = pd.to_datetime(df["fecha"], errors="coerce").dt.strftime("%Y-%m-%d")

    print("Generando variables temporales...")
    df = add_temporal_features(df)

    print("Generando variables meteorológicas básicas...")
    df = add_meteo_features(df)

    print("Generando variables log1p seleccionadas...")
    df = add_log_features(df)

    print("Uniendo contexto INEGI estatal...")
    df = df.merge(
        inegi_context,
        on=CONTEXT_KEY_COL,
        how="left",
        validate="many_to_one",
    )

    print("Uniendo contexto INFyS estatal...")
    df = df.merge(
        infys_context,
        on=CONTEXT_KEY_COL,
        how="left",
        validate="many_to_one",
    )

    df = reorder_columns(df)

    print("Validando matriz final entidad-día...")
    validate_final_matrix(df)

    df.to_csv(
        PATH_FE_ENTIDAD_DIA_MATRIZ,
        index=False,
        encoding="utf-8-sig",
    )

    print("\nArchivo generado:")
    print(f"- {PATH_FE_ENTIDAD_DIA_MATRIZ}")

    print("\nResumen:")
    print(f"- Filas escritas: {len(df):,}")
    print(f"- Columnas finales: {len(df.columns):,}")

    print("\nProceso terminado.")


if __name__ == "__main__":
    main()