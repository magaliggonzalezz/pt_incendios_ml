# -*- coding: utf-8 -*-
"""
NASA FIRMS | Data Preparation (DP) alineado con CRISP-DM
Fuente operativa: productos ARCHIVE de NASA FIRMS

Objetivo
--------
Preparar los archivos archive de NASA FIRMS para integración posterior,
manteniendo trazabilidad de archivo/producto y sin realizar todavía
integración con otras fuentes ni feature engineering.

Este script pertenece a Data Preparation.
No realiza modelado, evaluación ni integración con CONAFOR/SMN/INEGI/CONABIO.

Entradas
--------
Lee archivos CSV desde:
    PT_ANALISIS/01_raw-data/firms/

Procesa únicamente archivos cuyo nombre contenga:
    "archive"

Salidas
-------
1) Dataset limpio:
    PT_ANALISIS/03_data-preparation/firms/datasets/firms_archive_2001_2025_limpio.csv

2) Reporte QC:
    PT_ANALISIS/03_data-preparation/firms/reports/firms_archive_2001_2025_qc_report.csv

Reglas principales
------------------
- Procesa únicamente archivos archive.
- Normaliza nombres de columnas a minúsculas.
- Convierte tokens faltantes a NA.
- Estandariza acq_date a YYYY-MM-DD.
- Estandariza acq_time a HH:MM.
- Convierte columnas numéricas a tipo numérico.
- Valida columnas críticas: latitude, longitude, acq_date, acq_time.
- Valida rango geográfico global.
- Reporta registros fuera del bbox aproximado de México, pero NO los elimina.
- Valida periodo del proyecto 2001-2025.
- Elimina duplicados exactos.
- Elimina duplicados lógicos.
- Ordena cronológicamente con datetime auxiliar interno.
- Exporta columnas originales FIRMS + trazabilidad.

Notas metodológicas
-------------------
- confidence se conserva como texto, porque MODIS y VIIRS no codifican igual este campo.
- type se conserva sin filtrar; la decisión de filtrar tipos queda para una etapa posterior si se justifica.
"""

from __future__ import annotations

import math
import re
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import pandas as pd


# =========================================================
# 1) CONFIGURACIÓN
# =========================================================

BASE_DIR = Path(r"C:\Users\Hp\OneDrive\Documentos\PT_ANALISIS")

ROOT_DIR = BASE_DIR / "01_raw-data" / "firms"
OUT_DIR = BASE_DIR / "03_data-preparation" / "firms"
DATASETS_DIR = OUT_DIR / "datasets"
REPORTS_DIR = OUT_DIR / "reports"

OUT_DATASET = DATASETS_DIR / "firms_archive_2001_2025_limpio.csv"
OUT_QC = REPORTS_DIR / "firms_archive_2001_2025_qc_report.csv"

DATASETS_DIR.mkdir(parents=True, exist_ok=True)
REPORTS_DIR.mkdir(parents=True, exist_ok=True)

PROJECT_START = datetime(2001, 1, 1)
PROJECT_END = datetime(2025, 12, 31)

ENCODINGS = ["utf-8-sig", "utf-8", "latin-1", "cp1252"]

MISSING_TOKENS = {
    "",
    " ",
    "NA",
    "N/A",
    "NULL",
    "NONE",
    "NULO",
    "nan",
    "NaN",
    "-",
    "--",
    "S/D",
    "SD",
    "SIN DATO",
}

EXPECTED_ARCHIVE_COLUMNS = [
    "latitude",
    "longitude",
    "brightness",
    "scan",
    "track",
    "acq_date",
    "acq_time",
    "satellite",
    "instrument",
    "confidence",
    "version",
    "bright_t31",
    "frp",
    "daynight",
    "type",
]

FINAL_COLUMNS = [
    "latitude",
    "longitude",
    "brightness",
    "scan",
    "track",
    "acq_date",
    "acq_time",
    "satellite",
    "instrument",
    "confidence",
    "version",
    "bright_t31",
    "frp",
    "daynight",
    "type",
    "source_file",
    "source_product",
    "product_family",
]

NUMERIC_FLOAT_COLUMNS = [
    "latitude",
    "longitude",
    "brightness",
    "scan",
    "track",
    "bright_t31",
    "frp",
]

NUMERIC_INT_COLUMNS = [
    "type",
]

STRING_COLUMNS = [
    "satellite",
    "instrument",
    "confidence",
    "version",
    "daynight",
    "source_file",
    "source_product",
    "product_family",
]

DATE_COLUMN = "acq_date"
TIME_COLUMN = "acq_time"

# BBOX aproximado de México
MEXICO_BBOX = {
    "lat_min": 14.0,
    "lat_max": 33.5,
    "lon_min": -118.5,
    "lon_max": -86.0,
}


# =========================================================
# 2) UTILIDADES GENERALES
# =========================================================

def normalize_column_name(col: str) -> str:
    return str(col).strip().lower()


def normalize_missing_value(v):
    if pd.isna(v):
        return pd.NA

    s = str(v).strip()

    if s in MISSING_TOKENS:
        return pd.NA

    return s


def safe_pct(num: int, den: int) -> float:
    return round((num / den) * 100.0, 4) if den else 0.0


def serialize_counter(counter: Counter, n: int = 10) -> str:
    return str(counter.most_common(n))


def try_read_csv(path: Path) -> Tuple[pd.DataFrame, str]:
    last_error = None

    for enc in ENCODINGS:
        try:
            df = pd.read_csv(path, encoding=enc, dtype=str, low_memory=False)
            return df, enc
        except Exception as e:
            last_error = e

    raise RuntimeError(
        f"No se pudo leer {path.name} con los encodings configurados. "
        f"Último error: {last_error}"
    )


def infer_product_metadata(path: Path) -> Tuple[str, str]:
    """
    Devuelve:
    - source_product: MODIS_ARCHIVE, SUOMI_VIIRS_ARCHIVE, J1_VIIRS_ARCHIVE, J2_VIIRS_ARCHIVE o UNKNOWN_ARCHIVE
    - product_family: MODIS, SUOMI_VIIRS, J1_VIIRS, J2_VIIRS o UNKNOWN
    """

    p = str(path).lower()

    if "m-c61" in p or "modis" in p:
        family = "MODIS"
    elif "sv-c2" in p or "snpp" in p or "suomi" in p:
        family = "SUOMI_VIIRS"
    elif "j1v-c2" in p or "j1" in p:
        family = "J1_VIIRS"
    elif "j2v-c2" in p or "j2" in p:
        family = "J2_VIIRS"
    elif "viirs" in p:
        family = "VIIRS"
    else:
        family = "UNKNOWN"

    source_product = f"{family}_ARCHIVE"

    return source_product, family


def ensure_expected_columns(df: pd.DataFrame) -> pd.DataFrame:
    for col in EXPECTED_ARCHIVE_COLUMNS:
        if col not in df.columns:
            df[col] = pd.NA

    return df


def normalize_text_columns(df: pd.DataFrame) -> pd.DataFrame:
    for col in df.columns:
        df[col] = df[col].map(normalize_missing_value)

    for col in STRING_COLUMNS:
        if col in df.columns:
            df[col] = df[col].astype("string").str.strip()

    return df


def parse_date_to_iso(v) -> Optional[str]:
    if pd.isna(v):
        return None

    s = str(v).strip()

    if s in MISSING_TOKENS or s == "":
        return None

    formats = [
        "%Y-%m-%d",
        "%Y/%m/%d",
        "%d/%m/%Y",
        "%d-%m-%Y",
        "%Y%m%d",
    ]

    for fmt in formats:
        try:
            dt = datetime.strptime(s, fmt)
            return dt.strftime("%Y-%m-%d")
        except Exception:
            pass

    return None


def parse_time_to_hhmm(v) -> Optional[str]:
    if pd.isna(v):
        return None

    s = str(v).strip()

    if s in MISSING_TOKENS or s == "":
        return None

    # Caso FIRMS típico: 0000, 0135, 2359
    if re.fullmatch(r"\d{4}", s):
        hh = int(s[:2])
        mm = int(s[2:])

        if 0 <= hh <= 23 and 0 <= mm <= 59:
            return f"{hh:02d}:{mm:02d}"

        return None

    # Caso alterno: H:MM o HH:MM
    if re.fullmatch(r"\d{1,2}:\d{2}", s):
        hh, mm = s.split(":")

        if hh.isdigit() and mm.isdigit():
            hh_i = int(hh)
            mm_i = int(mm)

            if 0 <= hh_i <= 23 and 0 <= mm_i <= 59:
                return f"{hh_i:02d}:{mm_i:02d}"

    return None


def to_float_or_na(v):
    if pd.isna(v):
        return pd.NA

    s = str(v).strip()

    if s in MISSING_TOKENS or s == "":
        return pd.NA

    try:
        return float(s)
    except Exception:
        return pd.NA


def to_int_or_na(v):
    if pd.isna(v):
        return pd.NA

    s = str(v).strip()

    if s in MISSING_TOKENS or s == "":
        return pd.NA

    try:
        f = float(s)

        if math.isnan(f):
            return pd.NA

        return int(f)
    except Exception:
        return pd.NA


def within_global_geo_range(lat, lon) -> bool:
    if pd.isna(lat) or pd.isna(lon):
        return False

    return (-90 <= lat <= 90) and (-180 <= lon <= 180)


def within_mexico_bbox_aprox(lat, lon) -> Optional[bool]:
    if pd.isna(lat) or pd.isna(lon):
        return None

    return (
        MEXICO_BBOX["lat_min"] <= lat <= MEXICO_BBOX["lat_max"]
        and MEXICO_BBOX["lon_min"] <= lon <= MEXICO_BBOX["lon_max"]
    )


def within_project_period(date_iso: Optional[str]) -> bool:
    if date_iso is None:
        return False

    try:
        dt = datetime.strptime(date_iso, "%Y-%m-%d")
    except Exception:
        return False

    return PROJECT_START <= dt <= PROJECT_END


# =========================================================
# 3) CARGA DE ARCHIVOS ARCHIVE
# =========================================================

def load_archive_files() -> Tuple[pd.DataFrame, List[Dict[str, object]]]:
    if not ROOT_DIR.exists():
        raise FileNotFoundError(f"No existe ROOT_DIR: {ROOT_DIR}")

    csv_files = sorted([
        p for p in ROOT_DIR.rglob("*.csv")
        if p.is_file() and "archive" in p.name.lower()
    ])

    if not csv_files:
        raise FileNotFoundError(
            f"No se encontraron archivos archive en: {ROOT_DIR}"
        )

    frames = []
    load_log = []

    print("\nNASA FIRMS | Data Preparation")
    print(f"Directorio raíz: {ROOT_DIR}")
    print(f"Archivos archive detectados: {len(csv_files)}")

    for path in csv_files:
        df, enc = try_read_csv(path)

        original_rows = len(df)
        original_columns = len(df.columns)
        original_column_names = [str(c).strip() for c in df.columns]

        df.columns = [normalize_column_name(c) for c in df.columns]
        normalized_column_names = list(df.columns)

        missing_expected = [
            col for col in EXPECTED_ARCHIVE_COLUMNS
            if col not in normalized_column_names
        ]

        extra_columns = [
            col for col in normalized_column_names
            if col not in EXPECTED_ARCHIVE_COLUMNS
        ]

        df = ensure_expected_columns(df)

        source_product, product_family = infer_product_metadata(path)

        df["source_file"] = path.name
        df["source_product"] = source_product
        df["product_family"] = product_family
        df["source_encoding"] = enc

        frames.append(df)

        load_log.append({
            "file_name": path.name,
            "source_product": source_product,
            "product_family": product_family,
            "encoding": enc,
            "rows_loaded": original_rows,
            "original_columns_loaded": original_columns,
            "original_column_names": original_column_names,
            "normalized_column_names": normalized_column_names,
            "missing_expected_columns": missing_expected,
            "extra_columns": extra_columns,
        })

        print(f"\nCargando: {path.name}")
        print(f"  Producto: {source_product}")
        print(f"  Familia: {product_family}")
        print(f"  Registros: {original_rows:,}")
        print(f"  Columnas originales: {original_columns}")
        print(f"  Encoding: {enc}")

        if missing_expected:
            print(f"  Columnas esperadas faltantes: {missing_expected}")

        if extra_columns:
            print(f"  Columnas extra: {extra_columns}")

    full_df = pd.concat(frames, ignore_index=True)

    return full_df, load_log


# =========================================================
# 4) PREPARACIÓN
# =========================================================

def prepare_firms_archive(
    df: pd.DataFrame
) -> Tuple[pd.DataFrame, pd.DataFrame, Dict[str, int], Dict[str, Counter]]:
    """
    Regresa:
    - df_final: dataset final exportable
    - df_prepared_internal: dataset depurado con columnas auxiliares para QC
    - metrics: métricas globales
    - domains: dominios observados
    """

    metrics = defaultdict(int)

    domains = {
        "source_file": Counter(),
        "source_product": Counter(),
        "product_family": Counter(),
        "satellite": Counter(),
        "instrument": Counter(),
        "version": Counter(),
        "daynight": Counter(),
        "type": Counter(),
        "confidence": Counter(),
    }

    metrics["rows_initial"] = len(df)

    df = df.copy()
    df = normalize_text_columns(df)

    # Dominios antes de eliminar registros
    for col in domains:
        if col in df.columns:
            domains[col].update(df[col].dropna().astype(str).tolist())

    # Estandarización de fecha y hora
    df["acq_date_std"] = df[DATE_COLUMN].map(parse_date_to_iso)
    df["acq_time_std"] = df[TIME_COLUMN].map(parse_time_to_hhmm)

    metrics["rows_invalid_acq_date"] = int(df["acq_date_std"].isna().sum())
    metrics["rows_invalid_acq_time"] = int(df["acq_time_std"].isna().sum())

    # Validación explícita del periodo del proyecto
    project_period_mask = df["acq_date_std"].map(within_project_period)
    outside_project_period_mask = ~project_period_mask
    outside_project_period_mask = outside_project_period_mask & df["acq_date_std"].notna()

    metrics["rows_outside_project_period"] = int(outside_project_period_mask.sum())

    # Conversión de tipos numéricos
    for col in NUMERIC_FLOAT_COLUMNS:
        if col in df.columns:
            df[col] = df[col].map(to_float_or_na)

    for col in NUMERIC_INT_COLUMNS:
        if col in df.columns:
            df[col] = df[col].map(to_int_or_na)

    # Faltantes críticos
    critical_missing_mask = pd.Series(False, index=df.index)

    for col in ["latitude", "longitude"]:
        critical_missing_mask = critical_missing_mask | df[col].isna()

    critical_missing_mask = (
        critical_missing_mask
        | df["acq_date_std"].isna()
        | df["acq_time_std"].isna()
    )

    metrics["rows_missing_critical"] = int(critical_missing_mask.sum())

    # Coordenadas fuera del rango global válido
    global_geo_invalid_mask = ~df.apply(
        lambda r: within_global_geo_range(
            r.get("latitude"),
            r.get("longitude")
        ),
        axis=1
    )

    global_geo_invalid_mask = (
        global_geo_invalid_mask
        & ~(df["latitude"].isna() | df["longitude"].isna())
    )

    metrics["rows_invalid_global_geo"] = int(global_geo_invalid_mask.sum())

    # BBOX aproximado de México: solo reportable, no se elimina
    bbox_results = df.apply(
        lambda r: within_mexico_bbox_aprox(
            r.get("latitude"),
            r.get("longitude")
        ),
        axis=1
    )

    metrics["rows_outside_mexico_bbox_aprox"] = int(
        sum(x is False for x in bbox_results)
    )

    # Duplicados exactos sobre columnas originales FIRMS
    exact_dup_subset = [
        c for c in EXPECTED_ARCHIVE_COLUMNS
        if c in df.columns
    ]

    exact_dup_mask = df.duplicated(
        subset=exact_dup_subset,
        keep="first"
    )

    metrics["rows_exact_duplicates"] = int(exact_dup_mask.sum())

    # Eliminación base
    # Nota: fuera de bbox México aprox. NO se elimina aquí.
    # Nota: fuera de periodo proyecto SÍ se elimina, porque el dataset final es 2001-2025.
    remove_base_mask = (
        critical_missing_mask
        | global_geo_invalid_mask
        | exact_dup_mask
        | outside_project_period_mask
    )

    df_base = df.loc[~remove_base_mask].copy()

    metrics["rows_after_base_filters"] = len(df_base)

    # Datetime auxiliar interno para validar y ordenar
    df_base["acq_datetime_aux"] = pd.to_datetime(
        df_base["acq_date_std"] + " " + df_base["acq_time_std"],
        errors="coerce",
        format="%Y-%m-%d %H:%M"
    )

    invalid_datetime_mask = df_base["acq_datetime_aux"].isna()
    metrics["rows_invalid_acq_datetime"] = int(invalid_datetime_mask.sum())

    df_base = df_base.loc[~invalid_datetime_mask].copy()

    # Duplicados lógicos
    logical_key = [
        "latitude",
        "longitude",
        "acq_date_std",
        "acq_time_std",
        "satellite",
        "instrument",
    ]

    logical_dup_mask = df_base.duplicated(
        subset=logical_key,
        keep="first"
    )

    metrics["rows_logical_duplicates"] = int(logical_dup_mask.sum())

    df_prepared_internal = df_base.loc[~logical_dup_mask].copy()

    # Reemplazar fecha/hora originales por versiones estandarizadas
    df_prepared_internal["acq_date"] = df_prepared_internal["acq_date_std"]
    df_prepared_internal["acq_time"] = df_prepared_internal["acq_time_std"]

    # Orden cronológico
    df_prepared_internal = df_prepared_internal.sort_values(
        by=[
            "acq_datetime_aux",
            "source_product",
            "satellite",
            "instrument",
            "source_file",
        ],
        kind="stable"
    ).copy()

    # Dataset final exportable
    for col in FINAL_COLUMNS:
        if col not in df_prepared_internal.columns:
            df_prepared_internal[col] = pd.NA

    df_final = df_prepared_internal[FINAL_COLUMNS].copy()

    metrics["rows_final"] = len(df_final)
    metrics["rows_removed_total"] = metrics["rows_initial"] - metrics["rows_final"]

    return df_final, df_prepared_internal, dict(metrics), domains


# =========================================================
# 5) QC REPORT
# =========================================================

def summarize_subset(
    scope_type: str,
    scope_value,
    df_loaded_subset: pd.DataFrame,
    df_final_subset: pd.DataFrame,
    notes: str,
) -> Dict[str, object]:

    rows_loaded = len(df_loaded_subset)
    rows_final = len(df_final_subset)

    period_min = None
    period_max = None

    if rows_final > 0 and "acq_date" in df_final_subset.columns:
        period_min = df_final_subset["acq_date"].min()
        period_max = df_final_subset["acq_date"].max()

    return {
        "scope_type": scope_type,
        "scope_value": scope_value,
        "rows_loaded": rows_loaded,
        "rows_final": rows_final,
        "rows_removed_total": rows_loaded - rows_final,
        "pct_removed_total": safe_pct(rows_loaded - rows_final, rows_loaded),
        "period_min": period_min,
        "period_max": period_max,
        "top_source_file": serialize_counter(
            Counter(df_final_subset["source_file"].dropna().astype(str).tolist())
        ) if "source_file" in df_final_subset.columns else None,
        "top_source_product": serialize_counter(
            Counter(df_final_subset["source_product"].dropna().astype(str).tolist())
        ) if "source_product" in df_final_subset.columns else None,
        "top_product_family": serialize_counter(
            Counter(df_final_subset["product_family"].dropna().astype(str).tolist())
        ) if "product_family" in df_final_subset.columns else None,
        "top_satellite": serialize_counter(
            Counter(df_final_subset["satellite"].dropna().astype(str).tolist())
        ) if "satellite" in df_final_subset.columns else None,
        "top_instrument": serialize_counter(
            Counter(df_final_subset["instrument"].dropna().astype(str).tolist())
        ) if "instrument" in df_final_subset.columns else None,
        "top_version": serialize_counter(
            Counter(df_final_subset["version"].dropna().astype(str).tolist())
        ) if "version" in df_final_subset.columns else None,
        "top_confidence": serialize_counter(
            Counter(df_final_subset["confidence"].dropna().astype(str).tolist())
        ) if "confidence" in df_final_subset.columns else None,
        "top_daynight": serialize_counter(
            Counter(df_final_subset["daynight"].dropna().astype(str).tolist())
        ) if "daynight" in df_final_subset.columns else None,
        "top_type": serialize_counter(
            Counter(df_final_subset["type"].dropna().astype(str).tolist())
        ) if "type" in df_final_subset.columns else None,
        "notes": notes,
    }


def build_qc_report(
    df_final: pd.DataFrame,
    df_prepared_internal: pd.DataFrame,
    df_raw_archive: pd.DataFrame,
    metrics: Dict[str, int],
    load_log: List[Dict[str, object]],
    domains: Dict[str, Counter],
) -> pd.DataFrame:

    rows = []

    # -----------------------------------------------------
    # TOTAL
    # -----------------------------------------------------
    rows.append({
        "scope_type": "TOTAL",
        "scope_value": "ALL_ARCHIVE",
        "rows_loaded": metrics.get("rows_initial", 0),
        "rows_final": metrics.get("rows_final", 0),
        "rows_removed_total": metrics.get("rows_removed_total", 0),
        "pct_removed_total": safe_pct(
            metrics.get("rows_removed_total", 0),
            metrics.get("rows_initial", 0)
        ),
        "period_min": df_final["acq_date"].min() if len(df_final) else None,
        "period_max": df_final["acq_date"].max() if len(df_final) else None,
        "rows_missing_critical": metrics.get("rows_missing_critical", 0),
        "rows_invalid_acq_date": metrics.get("rows_invalid_acq_date", 0),
        "rows_invalid_acq_time": metrics.get("rows_invalid_acq_time", 0),
        "rows_invalid_acq_datetime": metrics.get("rows_invalid_acq_datetime", 0),
        "rows_outside_project_period": metrics.get("rows_outside_project_period", 0),
        "rows_invalid_global_geo": metrics.get("rows_invalid_global_geo", 0),
        "rows_outside_mexico_bbox_aprox": metrics.get("rows_outside_mexico_bbox_aprox", 0),
        "rows_exact_duplicates": metrics.get("rows_exact_duplicates", 0),
        "rows_logical_duplicates": metrics.get("rows_logical_duplicates", 0),
        "top_source_file": serialize_counter(domains["source_file"]),
        "top_source_product": serialize_counter(domains["source_product"]),
        "top_product_family": serialize_counter(domains["product_family"]),
        "top_satellite": serialize_counter(domains["satellite"]),
        "top_instrument": serialize_counter(domains["instrument"]),
        "top_version": serialize_counter(domains["version"]),
        "top_confidence": serialize_counter(domains["confidence"]),
        "top_daynight": serialize_counter(domains["daynight"]),
        "top_type": serialize_counter(domains["type"]),
        "notes": (
            "Resumen global del Data Preparation de NASA FIRMS archive. "
            "El bbox de México es aproximado y solo reportable; no sustituye validación por polígono."
        ),
    })

    # -----------------------------------------------------
    # PRODUCT
    # -----------------------------------------------------
    products = sorted(df_raw_archive["source_product"].dropna().astype(str).unique())

    for product in products:
        loaded_subset = df_raw_archive[df_raw_archive["source_product"] == product].copy()
        final_subset = df_final[df_final["source_product"] == product].copy()

        row = summarize_subset(
            scope_type="PRODUCT",
            scope_value=product,
            df_loaded_subset=loaded_subset,
            df_final_subset=final_subset,
            notes="Resumen por producto archive después de DP."
        )

        row.update({
            "rows_missing_critical": None,
            "rows_invalid_acq_date": None,
            "rows_invalid_acq_time": None,
            "rows_invalid_acq_datetime": None,
            "rows_outside_project_period": None,
            "rows_invalid_global_geo": None,
            "rows_outside_mexico_bbox_aprox": None,
            "rows_exact_duplicates": None,
            "rows_logical_duplicates": None,
        })

        rows.append(row)

    # -----------------------------------------------------
    # PRODUCT FAMILY
    # -----------------------------------------------------
    families = sorted(df_raw_archive["product_family"].dropna().astype(str).unique())

    for family in families:
        loaded_subset = df_raw_archive[df_raw_archive["product_family"] == family].copy()
        final_subset = df_final[df_final["product_family"] == family].copy()

        row = summarize_subset(
            scope_type="PRODUCT_FAMILY",
            scope_value=family,
            df_loaded_subset=loaded_subset,
            df_final_subset=final_subset,
            notes="Resumen por familia de producto después de DP."
        )

        row.update({
            "rows_missing_critical": None,
            "rows_invalid_acq_date": None,
            "rows_invalid_acq_time": None,
            "rows_invalid_acq_datetime": None,
            "rows_outside_project_period": None,
            "rows_invalid_global_geo": None,
            "rows_outside_mexico_bbox_aprox": None,
            "rows_exact_duplicates": None,
            "rows_logical_duplicates": None,
        })

        rows.append(row)

    # -----------------------------------------------------
    # YEAR
    # -----------------------------------------------------
    raw_year = (
        df_raw_archive[DATE_COLUMN]
        .map(parse_date_to_iso)
        .dropna()
        .map(lambda x: int(x[:4]))
        .value_counts()
        .to_dict()
    )

    final_year = (
        df_final["acq_date"]
        .dropna()
        .map(lambda x: int(str(x)[:4]))
        .value_counts()
        .to_dict()
    )

    years = sorted(set(raw_year.keys()) | set(final_year.keys()))

    for year in years:
        raw_n = int(raw_year.get(year, 0))
        final_n = int(final_year.get(year, 0))

        final_subset = df_final[
            df_final["acq_date"].astype("string").str.startswith(str(year), na=False)
        ].copy()

        rows.append({
            "scope_type": "YEAR",
            "scope_value": year,
            "rows_loaded": raw_n,
            "rows_final": final_n,
            "rows_removed_total": raw_n - final_n,
            "pct_removed_total": safe_pct(raw_n - final_n, raw_n),
            "period_min": final_subset["acq_date"].min() if len(final_subset) else None,
            "period_max": final_subset["acq_date"].max() if len(final_subset) else None,
            "rows_missing_critical": None,
            "rows_invalid_acq_date": None,
            "rows_invalid_acq_time": None,
            "rows_invalid_acq_datetime": None,
            "rows_outside_project_period": None,
            "rows_invalid_global_geo": None,
            "rows_outside_mexico_bbox_aprox": None,
            "rows_exact_duplicates": None,
            "rows_logical_duplicates": None,
            "top_source_file": serialize_counter(
                Counter(final_subset["source_file"].dropna().astype(str).tolist())
            ),
            "top_source_product": serialize_counter(
                Counter(final_subset["source_product"].dropna().astype(str).tolist())
            ),
            "top_product_family": serialize_counter(
                Counter(final_subset["product_family"].dropna().astype(str).tolist())
            ),
            "top_satellite": serialize_counter(
                Counter(final_subset["satellite"].dropna().astype(str).tolist())
            ),
            "top_instrument": serialize_counter(
                Counter(final_subset["instrument"].dropna().astype(str).tolist())
            ),
            "top_version": serialize_counter(
                Counter(final_subset["version"].dropna().astype(str).tolist())
            ),
            "top_confidence": serialize_counter(
                Counter(final_subset["confidence"].dropna().astype(str).tolist())
            ),
            "top_daynight": serialize_counter(
                Counter(final_subset["daynight"].dropna().astype(str).tolist())
            ),
            "top_type": serialize_counter(
                Counter(final_subset["type"].dropna().astype(str).tolist())
            ),
            "notes": "Resumen anual del dataset preparado.",
        })

    # -----------------------------------------------------
    # SOURCE FILE
    # -----------------------------------------------------
    for item in load_log:
        file_name = item["file_name"]

        loaded_subset = df_raw_archive[df_raw_archive["source_file"] == file_name].copy()
        final_subset = df_final[df_final["source_file"] == file_name].copy()

        row = summarize_subset(
            scope_type="SOURCE_FILE",
            scope_value=file_name,
            df_loaded_subset=loaded_subset,
            df_final_subset=final_subset,
            notes=(
                f"encoding={item['encoding']}; "
                f"original_columns_loaded={item['original_columns_loaded']}; "
                f"missing_expected_columns={item['missing_expected_columns']}; "
                f"extra_columns={item['extra_columns']}"
            )
        )

        row.update({
            "rows_missing_critical": None,
            "rows_invalid_acq_date": None,
            "rows_invalid_acq_time": None,
            "rows_invalid_acq_datetime": None,
            "rows_outside_project_period": None,
            "rows_invalid_global_geo": None,
            "rows_outside_mexico_bbox_aprox": None,
            "rows_exact_duplicates": None,
            "rows_logical_duplicates": None,
        })

        rows.append(row)

    qc_df = pd.DataFrame(rows)

    # Orden sugerido de columnas
    ordered_cols = [
        "scope_type",
        "scope_value",
        "rows_loaded",
        "rows_final",
        "rows_removed_total",
        "pct_removed_total",
        "period_min",
        "period_max",
        "rows_missing_critical",
        "rows_invalid_acq_date",
        "rows_invalid_acq_time",
        "rows_invalid_acq_datetime",
        "rows_outside_project_period",
        "rows_invalid_global_geo",
        "rows_outside_mexico_bbox_aprox",
        "rows_exact_duplicates",
        "rows_logical_duplicates",
        "top_source_file",
        "top_source_product",
        "top_product_family",
        "top_satellite",
        "top_instrument",
        "top_version",
        "top_confidence",
        "top_daynight",
        "top_type",
        "notes",
    ]

    for col in ordered_cols:
        if col not in qc_df.columns:
            qc_df[col] = None

    qc_df = qc_df[ordered_cols].copy()

    return qc_df


# =========================================================
# 6) PIPELINE PRINCIPAL
# =========================================================

def main():
    df_raw_archive, load_log = load_archive_files()

    print("\nUnificando archivos archive...")
    print(f"Registros iniciales totales: {len(df_raw_archive):,}")

    df_final, df_prepared_internal, metrics, domains = prepare_firms_archive(df_raw_archive)

    qc_df = build_qc_report(
        df_final=df_final,
        df_prepared_internal=df_prepared_internal,
        df_raw_archive=df_raw_archive,
        metrics=metrics,
        load_log=load_log,
        domains=domains,
    )

    df_final.to_csv(OUT_DATASET, index=False, encoding="utf-8-sig")
    qc_df.to_csv(OUT_QC, index=False, encoding="utf-8-sig")

    print("\n=== RESUMEN DP FIRMS ===")
    print(f"Registros iniciales: {metrics.get('rows_initial', 0):,}")
    print(f"Registros finales: {metrics.get('rows_final', 0):,}")
    print(f"Registros removidos totales: {metrics.get('rows_removed_total', 0):,}")
    print(f"Faltantes críticos: {metrics.get('rows_missing_critical', 0):,}")
    print(f"Fechas inválidas: {metrics.get('rows_invalid_acq_date', 0):,}")
    print(f"Horas inválidas: {metrics.get('rows_invalid_acq_time', 0):,}")
    print(f"Datetime auxiliar inválido: {metrics.get('rows_invalid_acq_datetime', 0):,}")
    print(f"Fuera periodo 2001-2025: {metrics.get('rows_outside_project_period', 0):,}")
    print(f"Coordenadas fuera rango global: {metrics.get('rows_invalid_global_geo', 0):,}")
    print(f"Fuera bbox México aprox.: {metrics.get('rows_outside_mexico_bbox_aprox', 0):,}")
    print(f"Duplicados exactos: {metrics.get('rows_exact_duplicates', 0):,}")
    print(f"Duplicados lógicos: {metrics.get('rows_logical_duplicates', 0):,}")

    print("\nArchivos generados:")
    print(f"- Dataset limpio: {OUT_DATASET}")
    print(f"- Reporte QC: {OUT_QC}")

    print("\nColumnas exportadas en dataset limpio:")
    for col in FINAL_COLUMNS:
        print(f"  - {col}")


if __name__ == "__main__":
    main()