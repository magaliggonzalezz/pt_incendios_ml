# -*- coding: utf-8 -*-
"""
CONAFOR | Data Preparation (DP) tabular
Homologación y consolidación de:
- estadisticasIncendiosForestales2015-2024.xlsx
- 2025_Incendios_forestales.csv

Objetivo
--------
Construir una tabla tabular canónica y consolidada 2015-2025, lista para
etapas posteriores de integración espacial, validación y modelado.

Salidas
-------
- dp01_matriz_homologacion.csv
- dp02_validacion_campos.csv
- dp03_registros_invalidos.csv
- dp04_tabular_consolidado_2015_2025.csv
- dp05_resumen_proceso.csv
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable
import re
import unicodedata

import numpy as np
import pandas as pd


# ============================================================
# CONFIGURACIÓN
# ============================================================

BASE_DIR = Path(r"C:\Users\Hp\OneDrive\Documentos\PT_Analisis")

PATH_XLSX = BASE_DIR / "01_raw-data" / "conafor" / "estadisticasIncendiosForestales2015-2024.xlsx"
PATH_CSV_2025 = BASE_DIR / "01_raw-data" / "conafor" / "2025_Incendios_forestales.csv"

PATH_CATALOGO_ENTIDAD = BASE_DIR / "01_raw-data" / "inegi" / "catun_entidad" / "AGEEML_utf.csv"
PATH_CATALOGO_MUNICIPIO = BASE_DIR / "01_raw-data" / "inegi" / "catun_municipio" / "AGEEML_utf8.csv"

OUT_DIR = BASE_DIR / "03_data-preparation" / "conafor"
OUT_REPORTS = OUT_DIR / "reports" / "tabular"
OUT_DATASETS = OUT_DIR / "datasets"

OUT_REPORTS.mkdir(parents=True, exist_ok=True)
OUT_DATASETS.mkdir(parents=True, exist_ok=True)

OUT_MATRIZ = OUT_REPORTS / "dp01_homologacion_tabular.csv"
OUT_INVALIDOS = OUT_REPORTS / "dp01_incidencias_tabular.csv"
OUT_CONSOLIDADO = OUT_DATASETS / "conafor_tabular_2015_2025_limpio.csv"
OUT_RESUMEN = OUT_REPORTS / "dp01_resumen_tabular.csv"

MEX_BBOX = {
    "min_lon": -118.366667,
    "min_lat": 14.533334,
    "max_lon": -86.708334,
    "max_lat": 32.716667,
}

CSV_ENCODINGS = ("utf-8-sig", "utf-8", "latin-1", "cp1252")


# ============================================================
# ESQUEMA
# ============================================================

FINAL_COLUMNS = [
    "anio",
    "clave_incendio",
    "estado",
    "cve_ent",
    "municipio",
    "cve_mun",
    "region",
    "latitud",
    "longitud",
    "fecha_inicio",
    "fecha_termino",
    "deteccion",
    "llegada",
    "duracion",
    "duracion_categoria",
    "causa",
    "causa_especifica",
    "predio",
    "regimen_fuego",
    "tipo_incendio",
    "tipo_impacto",
    "tipo_vegetacion",
    "superficie_total_ha",
    "superficie_categoria",
    "arbolado_adulto",
    "arbustivo",
    "herbaceo",
    "hojarasca",
    "renuevo",
    "fuente",
]

WORK_COLUMNS = FINAL_COLUMNS + [
    "estado_norm",
    "municipio_norm",
    "predio_norm",
]

MAP_XLSX = {
    "ano": "anio",
    "clave_del_incendio": "clave_incendio",
    "estado": "estado",
    "cve_ent": "cve_ent",
    "municipio": "municipio",
    "cve_mun": "cve_mun",
    "region": "region",
    "latitud": "latitud",
    "longitud": "longitud",
    "fecha_inicio": "fecha_inicio",
    "fecha_termino": "fecha_termino",
    "deteccion": "deteccion",
    "llegada": "llegada",
    "duracion": "duracion",
    "duracion_dias": "duracion_categoria",
    "causa": "causa",
    "causa_especifica": "causa_especifica",
    "predio": "predio",
    "regimen_de_fuego": "regimen_fuego",
    "tipo_de_incendio": "tipo_incendio",
    "tipo_impacto": "tipo_impacto",
    "tipo_vegetacion": "tipo_vegetacion",
    "total_hectareas": "superficie_total_ha",
    "tamano": "superficie_categoria",
    "arbolado_adulto": "arbolado_adulto",
    "arbustivo": "arbustivo",
    "herbaceo": "herbaceo",
    "hojarasca": "hojarasca",
    "renuevo": "renuevo",
    "latitud_grados": "latitud_grados",
    "latitud_minutos": "latitud_minutos",
    "latitud_segundos": "latitud_segundos",
    "longitud_grados": "longitud_grados",
    "longitud_minutos": "longitud_minutos",
    "longitud_segundos": "longitud_segundos",
}

MAP_2025 = {
    "anio": "anio",
    "clave_incendio": "clave_incendio",
    "entidad": "estado",
    "cve_ent": "cve_ent",
    "municipio": "municipio",
    "cve_municipio": "cve_mun",
    "crmf": "region",
    "fecha_inicio": "fecha_inicio",
    "fecha_liquidacion": "fecha_termino",
    "deteccion": "deteccion",
    "llegada": "llegada",
    "duracion": "duracion",
    "categoria_duracion_dias": "duracion_categoria",
    "posible_causa": "causa",
    "posible_causa_especifica": "causa_especifica",
    "predio_paraje": "predio",
    "regimen_fuego": "regimen_fuego",
    "tipo_incendio": "tipo_incendio",
    "clasf_primer_orden": "tipo_impacto",
    "tipo_vegetacion": "tipo_vegetacion",
    "total_ha": "superficie_total_ha",
    "clasificacion_sup_afectada": "superficie_categoria",
    "arbolado_adulto": "arbolado_adulto",
    "arbustivo": "arbustivo",
    "herbaceo": "herbaceo",
    "hojarasca": "hojarasca",
    "renuevo": "renuevo",
    "latitud_grados": "latitud_grados",
    "latitud_minutos": "latitud_minutos",
    "latitud_segundos": "latitud_segundos",
    "longitud_grados": "longitud_grados",
    "longitud_minutos": "longitud_minutos",
    "longitud_segundos": "longitud_segundos",
}


# ============================================================
# UTILIDADES
# ============================================================

def strip_accents(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", text)
    return "".join(ch for ch in normalized if not unicodedata.combining(ch))


def normalize_column_name(name: Any) -> str:
    if pd.isna(name):
        return ""
    s = str(name).strip()
    s = strip_accents(s).lower()
    s = re.sub(r"[\s/\\\-]+", "_", s)
    s = re.sub(r"[^a-z0-9_]", "", s)
    s = re.sub(r"_+", "_", s).strip("_")
    return s


def normalize_text_value(value: Any) -> Any:
    if pd.isna(value):
        return pd.NA

    s = str(value).strip()
    if not s or s.lower() in {"nan", "<na>", "none"}:
        return pd.NA

    s = strip_accents(s).lower()
    s = re.sub(r"\s+", " ", s)

    replacements = {
        "distrito federal": "ciudad de mexico",
        "cdmx": "ciudad de mexico",
        "estado de mexico": "mexico",
        "coahuila": "coahuila de zaragoza",
        "veracruz": "veracruz de ignacio de la llave",
        "michoacan": "michoacan de ocampo",
    }
    return replacements.get(s, s)


def to_title_case(value: Any) -> Any:
    if pd.isna(value):
        return pd.NA

    s = str(value).strip()
    if not s or s.lower() in {"nan", "<na>", "none"}:
        return pd.NA

    s = re.sub(r"\s+", " ", s)
    return s.title()


def canonical_estado_display(series: pd.Series) -> pd.Series:
    s = series.astype("string").str.strip()
    s = s.replace({
        "Ciudad De México": "Ciudad de México",
        "Mexico": "México",
        "Michoacan De Ocampo": "Michoacán de Ocampo",
        "Veracruz De Ignacio De La Llave": "Veracruz de Ignacio de la Llave",
        "Coahuila De Zaragoza": "Coahuila de Zaragoza",
    })
    return s


def read_csv_flexible(path: Path, dtype: Any | None = None) -> pd.DataFrame:
    last_error: Exception | None = None
    for enc in CSV_ENCODINGS:
        try:
            return pd.read_csv(path, encoding=enc, dtype=dtype)
        except Exception as exc:
            last_error = exc
    raise RuntimeError(f"No fue posible leer el CSV: {path}") from last_error


def ensure_columns(df: pd.DataFrame, columns: Iterable[str]) -> pd.DataFrame:
    for col in columns:
        if col not in df.columns:
            df[col] = pd.NA
    return df


def to_numeric(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce")


def normalize_geo_keys(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    if "cve_ent" in df.columns:
        s = df["cve_ent"].astype("string").str.strip()
        s = s.replace({"": pd.NA, "nan": pd.NA, "<NA>": pd.NA})
        df["cve_ent"] = s.where(s.isna(), s.str.zfill(2))

    if "cve_mun" in df.columns:
        s = df["cve_mun"].astype("string").str.strip()
        s = s.replace({"": pd.NA, "nan": pd.NA, "<NA>": pd.NA})
        df["cve_mun"] = s.where(s.isna(), s.str.zfill(3))

    return df


def parse_date_iso(series: pd.Series) -> pd.Series:
    s = series.astype("string").str.strip()
    s = s.replace({"": pd.NA, "nan": pd.NA, "NaN": pd.NA, "<NA>": pd.NA, "None": pd.NA})

    out = pd.Series(pd.NaT, index=s.index, dtype="datetime64[ns]")

    mask_dmy = s.str.match(r"^\d{1,2}/\d{1,2}/\d{4}( \d{1,2}:\d{2}:\d{2})?$", na=False)
    if mask_dmy.any():
        mask_dmy_hms = s.str.match(r"^\d{1,2}/\d{1,2}/\d{4} \d{1,2}:\d{2}:\d{2}$", na=False)
        if mask_dmy_hms.any():
            out.loc[mask_dmy_hms] = pd.to_datetime(
                s.loc[mask_dmy_hms],
                format="%d/%m/%Y %H:%M:%S",
                errors="coerce",
            )
        mask_dmy_date = mask_dmy & (~mask_dmy_hms)
        if mask_dmy_date.any():
            out.loc[mask_dmy_date] = pd.to_datetime(
                s.loc[mask_dmy_date],
                format="%d/%m/%Y",
                errors="coerce",
            )

    mask_ymd = s.str.match(r"^\d{4}-\d{1,2}-\d{1,2}( \d{1,2}:\d{2}:\d{2})?$", na=False)
    if mask_ymd.any():
        mask_ymd_hms = s.str.match(r"^\d{4}-\d{1,2}-\d{1,2} \d{1,2}:\d{2}:\d{2}$", na=False)
        if mask_ymd_hms.any():
            out.loc[mask_ymd_hms] = pd.to_datetime(
                s.loc[mask_ymd_hms],
                format="%Y-%m-%d %H:%M:%S",
                errors="coerce",
            )
        mask_ymd_date = mask_ymd & (~mask_ymd_hms)
        if mask_ymd_date.any():
            out.loc[mask_ymd_date] = pd.to_datetime(
                s.loc[mask_ymd_date],
                format="%Y-%m-%d",
                errors="coerce",
            )

    mask_pending = out.isna() & s.notna()
    if mask_pending.any():
        serial = pd.to_numeric(s.loc[mask_pending], errors="coerce")
        valid_serial = serial.notna()
        if valid_serial.any():
            out.loc[serial.index[valid_serial]] = pd.to_datetime(
                serial.loc[valid_serial],
                unit="D",
                origin="1899-12-30",
                errors="coerce",
            )

    mask_pending = out.isna() & s.notna()
    if mask_pending.any():
        out.loc[mask_pending] = pd.to_datetime(
            s.loc[mask_pending],
            errors="coerce",
            dayfirst=True,
        )

    return out.dt.strftime("%Y-%m-%d").astype("string")


def normalize_hms(series: pd.Series) -> pd.Series:
    s = series.astype("string").str.strip()
    s = s.replace({"": pd.NA, "nan": pd.NA, "NaT": pd.NA, "<NA>": pd.NA})

    def convert_one(x: Any) -> Any:
        if pd.isna(x):
            return pd.NA

        txt = str(x).strip()
        txt = txt.replace(";", ":")
        txt = re.sub(r"(\d{1,5}:\d{1,2}:\d{1,2})\.\d+$", r"\1", txt)
        txt = re.sub(r"(\d+\s+day[s]?,\s*\d{1,5}:\d{1,2}:\d{1,2})\.\d+$", r"\1", txt)

        m_hhmm = re.match(r"^(\d{1,5}):([0-5]?\d)$", txt)
        if m_hhmm:
            hh, mm = m_hhmm.groups()
            return f"{int(hh):02d}:{int(mm):02d}:00"

        m_hms = re.match(r"^(\d{1,5}):([0-5]?\d):([0-5]?\d)$", txt)
        if m_hms:
            hh, mm, ss = m_hms.groups()
            return f"{int(hh):02d}:{int(mm):02d}:{int(ss):02d}"

        m_day = re.match(r"^(\d+)\s+day[s]?,\s*(\d{1,5}):([0-5]?\d):([0-5]?\d)$", txt)
        if m_day:
            days, hh, mm, ss = m_day.groups()
            total_hours = int(days) * 24 + int(hh)
            return f"{total_hours:02d}:{int(mm):02d}:{int(ss):02d}"

        return pd.NA

    return s.map(convert_one).astype("string")


def is_valid_hms(series: pd.Series) -> pd.Series:
    s = series.astype("string").str.strip()
    return s.str.match(r"^\d{2,5}:[0-5]\d:[0-5]\d$", na=False)


def dms_to_decimal(
    degrees: pd.Series,
    minutes: pd.Series,
    seconds: pd.Series,
    *,
    is_longitude: bool,
) -> pd.Series:
    deg = to_numeric(degrees)
    mins = to_numeric(minutes).fillna(0)
    secs = to_numeric(seconds).fillna(0)

    decimal = deg.abs() + (mins / 60.0) + (secs / 3600.0)
    sign = np.where(deg < 0, -1.0, 1.0)
    decimal = decimal * sign

    if is_longitude:
        decimal = np.where(pd.isna(decimal), np.nan, -np.abs(decimal))

    return pd.Series(decimal, index=degrees.index)


def normalize_zero_coordinates(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    lat = pd.to_numeric(df["latitud"], errors="coerce")
    lon = pd.to_numeric(df["longitud"], errors="coerce")

    mask_both_zero = lat.eq(0) & lon.eq(0)
    mask_lat_zero_only = lat.eq(0) & lon.notna()
    mask_lon_zero_only = lon.eq(0) & lat.notna()

    mask_zero_invalid = mask_both_zero | mask_lat_zero_only | mask_lon_zero_only

    df.loc[mask_zero_invalid, "latitud"] = np.nan
    df.loc[mask_zero_invalid, "longitud"] = np.nan

    return df


def validate_bbox_mexico(lat: pd.Series, lon: pd.Series) -> pd.Series:
    return (
        lat.between(MEX_BBOX["min_lat"], MEX_BBOX["max_lat"], inclusive="both")
        & lon.between(MEX_BBOX["min_lon"], MEX_BBOX["max_lon"], inclusive="both")
    )


# ============================================================
# CATÁLOGOS
# ============================================================

def read_entity_catalog(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()

    df = read_csv_flexible(path, dtype=str)
    df.columns = [normalize_column_name(c) for c in df.columns]

    df = df.rename(columns={
        "cve_ent": "cve_ent",
        "nom_ent": "estado",
    })
    df = ensure_columns(df, ["cve_ent", "estado"])

    df["estado"] = df["estado"].astype("string").str.strip()
    df["estado_norm"] = df["estado"].map(normalize_text_value)
    df = normalize_geo_keys(df)

    return df[["cve_ent", "estado", "estado_norm"]].drop_duplicates(subset=["estado_norm"])


def read_municipality_catalog(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()

    df = read_csv_flexible(path, dtype=str)
    df.columns = [normalize_column_name(c) for c in df.columns]

    df = df.rename(columns={
        "cve_ent": "cve_ent",
        "nom_ent": "estado",
        "cve_mun": "cve_mun",
        "nom_mun": "municipio",
    })
    df = ensure_columns(df, ["cve_ent", "estado", "cve_mun", "municipio"])

    for col in ["cve_ent", "estado", "cve_mun", "municipio"]:
        df[col] = df[col].astype("string").str.strip()

    df = normalize_geo_keys(df)
    df["estado_norm"] = df["estado"].map(normalize_text_value)
    df["municipio_norm"] = df["municipio"].map(normalize_text_value)

    return df[
        ["cve_ent", "cve_mun", "estado", "municipio", "estado_norm", "municipio_norm"]
    ].drop_duplicates(subset=["estado_norm", "municipio_norm"])


def enrich_with_entity_catalog(df: pd.DataFrame, entity_catalog: pd.DataFrame) -> pd.DataFrame:
    if entity_catalog.empty:
        return df

    merged = df.merge(
        entity_catalog[["estado_norm", "cve_ent", "estado"]],
        on="estado_norm",
        how="left",
        suffixes=("", "_cat_ent"),
    )

    merged["cve_ent"] = merged["cve_ent"].combine_first(merged["cve_ent_cat_ent"])
    merged = merged.drop(columns=["cve_ent_cat_ent", "estado_cat_ent"])
    merged = normalize_geo_keys(merged)
    return merged


def enrich_with_municipality_catalog(df: pd.DataFrame, municipality_catalog: pd.DataFrame) -> pd.DataFrame:
    if municipality_catalog.empty:
        return df

    merged = df.merge(
        municipality_catalog[["estado_norm", "municipio_norm", "cve_ent", "cve_mun", "estado", "municipio"]],
        on=["estado_norm", "municipio_norm"],
        how="left",
        suffixes=("", "_cat_mun"),
    )

    merged["cve_ent"] = merged["cve_ent"].combine_first(merged["cve_ent_cat_mun"])
    merged["cve_mun"] = merged["cve_mun"].combine_first(merged["cve_mun_cat_mun"])

    merged = merged.drop(columns=[
        "cve_ent_cat_mun",
        "cve_mun_cat_mun",
        "estado_cat_mun",
        "municipio_cat_mun",
    ])

    merged = normalize_geo_keys(merged)
    return merged


# ============================================================
# PREPARACIÓN
# ============================================================

def prepare_source(df: pd.DataFrame, source_name: str, column_map: dict[str, str]) -> pd.DataFrame:
    df = df.copy()
    df.columns = [normalize_column_name(c) for c in df.columns]

    rename_pairs = {col: column_map[col] for col in df.columns if col in column_map}
    df = df.rename(columns=rename_pairs)

    aux_dms = [
        "latitud_grados",
        "latitud_minutos",
        "latitud_segundos",
        "longitud_grados",
        "longitud_minutos",
        "longitud_segundos",
    ]

    df = ensure_columns(df, WORK_COLUMNS + aux_dms)
    df["fuente"] = source_name

    df["fecha_inicio"] = parse_date_iso(df["fecha_inicio"])
    df["fecha_termino"] = parse_date_iso(df["fecha_termino"])

    for col in ["deteccion", "llegada", "duracion"]:
        df[col] = normalize_hms(df[col])

    numeric_fields = [
        "anio",
        "superficie_total_ha",
        "arbolado_adulto",
        "arbustivo",
        "herbaceo",
        "hojarasca",
        "renuevo",
        "latitud",
        "longitud",
        "latitud_grados",
        "latitud_minutos",
        "latitud_segundos",
        "longitud_grados",
        "longitud_minutos",
        "longitud_segundos",
    ]
    for col in numeric_fields:
        df[col] = to_numeric(df[col])

    lat_missing = df["latitud"].isna()
    lon_missing = df["longitud"].isna()

    df.loc[lat_missing, "latitud"] = dms_to_decimal(
        df.loc[lat_missing, "latitud_grados"],
        df.loc[lat_missing, "latitud_minutos"],
        df.loc[lat_missing, "latitud_segundos"],
        is_longitude=False,
    )

    df.loc[lon_missing, "longitud"] = dms_to_decimal(
        df.loc[lon_missing, "longitud_grados"],
        df.loc[lon_missing, "longitud_minutos"],
        df.loc[lon_missing, "longitud_segundos"],
        is_longitude=True,
    )

    df = normalize_zero_coordinates(df)

    df["estado_norm"] = df["estado"].map(normalize_text_value)
    df["municipio_norm"] = df["municipio"].map(normalize_text_value)
    df["predio_norm"] = df["predio"].map(normalize_text_value)

    df["predio"] = df["predio"].map(to_title_case)
    df["municipio"] = df["municipio"].map(to_title_case)
    df["estado"] = df["estado"].map(to_title_case)
    df["estado"] = canonical_estado_display(df["estado"])

    df = normalize_geo_keys(df)
    return df


# ============================================================
# VALIDACIÓN
# ============================================================

def build_invalid_flags(df_work: pd.DataFrame) -> pd.DataFrame:
    tmp = df_work.copy()

    fi = pd.to_datetime(tmp["fecha_inicio"], errors="coerce")
    ft = pd.to_datetime(tmp["fecha_termino"], errors="coerce")

    coord_faltante = tmp["latitud"].isna() | tmp["longitud"].isna()
    coord_fuera_bbox = (~coord_faltante) & (~validate_bbox_mexico(tmp["latitud"], tmp["longitud"]))
    fecha_inconsistente = fi.notna() & ft.notna() & (fi > ft)

    anio_num = pd.to_numeric(tmp["anio"], errors="coerce")
    anio_nulo = anio_num.isna()
    anio_fuera_rango = anio_num.notna() & (~anio_num.between(2015, 2025, inclusive="both"))

    anio_fecha_inicio_diferente = (
        anio_num.notna()
        & fi.notna()
        & (anio_num.astype("Int64") != fi.dt.year.astype("Int64"))
    )

    clave_incendio_nula = tmp["clave_incendio"].isna()
    fecha_inicio_nula = tmp["fecha_inicio"].isna()
    fecha_termino_nula = tmp["fecha_termino"].isna()

    deteccion_invalida = (~is_valid_hms(tmp["deteccion"])) & tmp["deteccion"].notna()
    llegada_invalida = (~is_valid_hms(tmp["llegada"])) & tmp["llegada"].notna()
    duracion_invalida = (~is_valid_hms(tmp["duracion"])) & tmp["duracion"].notna()

    dup_mask = tmp.duplicated(subset=["anio", "clave_incendio"], keep=False)
    dup_mask = dup_mask & tmp["anio"].notna() & tmp["clave_incendio"].notna()

    flags = pd.DataFrame({
        "anio_nulo": anio_nulo,
        "anio_fuera_rango": anio_fuera_rango,
        "fecha_inconsistente": fecha_inconsistente,
        "fecha_inicio_nula": fecha_inicio_nula,
        "fecha_termino_nula": fecha_termino_nula,
        "anio_fecha_inicio_diferente": anio_fecha_inicio_diferente,
        "coord_faltante": coord_faltante,
        "coord_fuera_bbox": coord_fuera_bbox,
        "clave_incendio_nula": clave_incendio_nula,
        "deteccion_hms_invalido": deteccion_invalida,
        "llegada_hms_invalido": llegada_invalida,
        "duracion_hms_invalido": duracion_invalida,
        "duplicado_anio_clave_incendio": dup_mask,
    }, index=tmp.index)

    return flags


def build_invalid_records_report(df_work: pd.DataFrame) -> pd.DataFrame:
    tmp = df_work.copy()
    flags = build_invalid_flags(tmp)

    motivos = []
    for idx in tmp.index:
        cols_true = flags.columns[flags.loc[idx].fillna(False)]
        motivos.append("; ".join(cols_true.tolist()) if len(cols_true) > 0 else pd.NA)

    tmp["motivos_revision"] = motivos

    keep_cols = [
        "fuente",
        "anio",
        "clave_incendio",
        "estado",
        "cve_ent",
        "municipio",
        "cve_mun",
        "latitud",
        "longitud",
        "fecha_inicio",
        "fecha_termino",
        "deteccion",
        "llegada",
        "duracion",
        "motivos_revision",
    ]

    return tmp[tmp["motivos_revision"].notna()][keep_cols].copy()


def filter_valid_records(df_work: pd.DataFrame) -> pd.DataFrame:
    flags = build_invalid_flags(df_work)

    warning_flags = {
        "anio_fecha_inicio_diferente",
    }
    
    invalid_cols = [c for c in flags.columns if c not in warning_flags]

    invalid_mask = flags[invalid_cols].any(axis=1)
    return df_work.loc[~invalid_mask].copy()


# ============================================================
# REPORTES
# ============================================================

def classify_homologation_type(
    canon: str,
    inverse_xlsx: dict[str, list[str]],
    inverse_2025: dict[str, list[str]],
) -> str:
    in_xlsx = canon in inverse_xlsx
    in_csv = canon in inverse_2025

    if canon == "fuente":
        return "derivado"
    
    in_xlsx = canon in inverse_xlsx
    in_csv = canon in inverse_2025

    if canon in {"latitud", "longitud"}:
        return "derivar_o_conservar"

    if canon in {"cve_ent", "cve_mun"}:
        return "directo_o_enriquecer"

    if in_xlsx and in_csv:
        if inverse_xlsx[canon] == inverse_2025[canon]:
            return "directo"
        return "renombrar"

    if in_xlsx or in_csv:
        return "parcial"

    return "ausente"


def build_homologation_matrix() -> pd.DataFrame:
    rows: list[dict[str, Any]] = []

    inverse_xlsx: dict[str, list[str]] = {}
    for src_col, canon_col in MAP_XLSX.items():
        inverse_xlsx.setdefault(canon_col, []).append(src_col)

    inverse_2025: dict[str, list[str]] = {}
    for src_col, canon_col in MAP_2025.items():
        inverse_2025.setdefault(canon_col, []).append(src_col)

    for canon in FINAL_COLUMNS:
        if canon == "fuente":
            rows.append(
                {
                    "campo_canonico": canon,
                    "campo_xlsx": "asignado_por_script",
                    "campo_csv_2025": "asignado_por_script",
                    "presente_xlsx": False,
                    "presente_csv_2025": False,
                    "derivable_csv_2025": True,
                    "tipo_homologacion": "derivado",
                }
            )
            continue

        rows.append(
            {
                "campo_canonico": canon,
                "campo_xlsx": ", ".join(inverse_xlsx.get(canon, [])),
                "campo_csv_2025": ", ".join(inverse_2025.get(canon, [])),
                "presente_xlsx": canon in inverse_xlsx,
                "presente_csv_2025": canon in inverse_2025,
                "derivable_csv_2025": canon in {"latitud", "longitud"},
                "tipo_homologacion": classify_homologation_type(canon, inverse_xlsx, inverse_2025),
            }
        )

    return pd.DataFrame(rows)


def build_validation_report(df_final: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    n = len(df_final)

    for col in df_final.columns:
        nulls = int(df_final[col].isna().sum())
        rows.append(
            {
                "campo": col,
                "registros": n,
                "nulos": nulls,
                "pct_nulos": round((nulls / n) * 100, 4) if n else 0.0,
                "cardinalidad": int(df_final[col].nunique(dropna=True)),
                "tipo_pandas": str(df_final[col].dtype),
            }
        )

    return pd.DataFrame(rows)


def build_summary(
    df_xlsx: pd.DataFrame,
    df_csv: pd.DataFrame,
    df_work_total: pd.DataFrame,
    df_final: pd.DataFrame,
    incidencias: pd.DataFrame,
) -> pd.DataFrame:
    flags_total = build_invalid_flags(df_work_total)

    warning_flags = {
        "anio_fecha_inicio_diferente",
    }

    invalid_cols = [c for c in flags_total.columns if c not in warning_flags]

    invalidos_reales_mask = flags_total[invalid_cols].any(axis=1)

    advertencias_mask = pd.Series(False, index=flags_total.index)
    for col in warning_flags:
        if col in flags_total.columns:
            advertencias_mask = advertencias_mask | flags_total[col].fillna(False)

    summary = [
        {"metrica": "registros_xlsx_2015_2024", "valor": len(df_xlsx)},
        {"metrica": "registros_csv_2025", "valor": len(df_csv)},
        {"metrica": "registros_entrada_total", "valor": len(df_work_total)},

        {"metrica": "registros_con_incidencias", "valor": len(incidencias)},
        {"metrica": "registros_invalidos_reales", "valor": int(invalidos_reales_mask.sum())},
        {"metrica": "registros_advertencia", "valor": int(advertencias_mask.sum())},

        {"metrica": "registros_consolidados_validos", "valor": len(df_final)},
        {"metrica": "columnas_consolidadas", "valor": len(df_final.columns)},

        {"metrica": "registros_coord_faltante", "valor": int(flags_total["coord_faltante"].sum())},
        {"metrica": "registros_coord_fuera_bbox", "valor": int(flags_total["coord_fuera_bbox"].sum())},
        {"metrica": "clave_incendio_nula", "valor": int(flags_total["clave_incendio_nula"].sum())},
        {"metrica": "anio_nulo", "valor": int(flags_total["anio_nulo"].sum())},
        {"metrica": "anio_fuera_rango", "valor": int(flags_total["anio_fuera_rango"].sum())},
        {"metrica": "anio_fecha_inicio_diferente", "valor": int(flags_total["anio_fecha_inicio_diferente"].sum())},
        {"metrica": "fecha_inicio_nula", "valor": int(flags_total["fecha_inicio_nula"].sum())},
        {"metrica": "fecha_termino_nula", "valor": int(flags_total["fecha_termino_nula"].sum())},
        {"metrica": "fecha_inconsistente", "valor": int(flags_total["fecha_inconsistente"].sum())},
        {"metrica": "deteccion_hms_invalido", "valor": int(flags_total["deteccion_hms_invalido"].sum())},
        {"metrica": "llegada_hms_invalido", "valor": int(flags_total["llegada_hms_invalido"].sum())},
        {"metrica": "duracion_hms_invalido", "valor": int(flags_total["duracion_hms_invalido"].sum())},
        {"metrica": "duplicados_anio_clave_incendio", "valor": int(flags_total["duplicado_anio_clave_incendio"].sum())},
        {"metrica": "cve_ent_nula_consolidado", "valor": int(df_final["cve_ent"].isna().sum())},
        {"metrica": "cve_mun_nula_consolidado", "valor": int(df_final["cve_mun"].isna().sum())},
    ]

    return pd.DataFrame(summary)


# ===========================================================
# MAIN
#============================================================

def main() -> None:
    print("CONAFOR | DP tabular 2015-2025")
    print("Leyendo fuentes...")

    if not PATH_XLSX.exists():
        raise FileNotFoundError(f"No existe el archivo XLSX: {PATH_XLSX}")
    if not PATH_CSV_2025.exists():
        raise FileNotFoundError(f"No existe el archivo CSV 2025: {PATH_CSV_2025}")

    df_xlsx_raw = pd.read_excel(PATH_XLSX, dtype=str)
    df_csv_raw = read_csv_flexible(PATH_CSV_2025, dtype=str)

    print(f"Registros XLSX 2015-2024: {len(df_xlsx_raw):,}")
    print(f"Registros CSV 2025:       {len(df_csv_raw):,}")

    print("\nPreparando fuentes...")
    df_xlsx = prepare_source(
        df=df_xlsx_raw,
        source_name="estadisticasIncendiosForestales2015-2024",
        column_map=MAP_XLSX,
    )
    df_csv = prepare_source(
        df=df_csv_raw,
        source_name="2025_Incendios_forestales",
        column_map=MAP_2025,
    )

    print("Leyendo catálogos INEGI...")
    entity_catalog = read_entity_catalog(PATH_CATALOGO_ENTIDAD)
    municipality_catalog = read_municipality_catalog(PATH_CATALOGO_MUNICIPIO)

    if not entity_catalog.empty:
        print(f"Catálogo entidad cargado:   {len(entity_catalog):,}")
        df_xlsx = enrich_with_entity_catalog(df_xlsx, entity_catalog)
        df_csv = enrich_with_entity_catalog(df_csv, entity_catalog)

    if not municipality_catalog.empty:
        print(f"Catálogo municipio cargado: {len(municipality_catalog):,}")
        df_xlsx = enrich_with_municipality_catalog(df_xlsx, municipality_catalog)
        df_csv = enrich_with_municipality_catalog(df_csv, municipality_catalog)

    # Reaplicar normalizaciones tras enriquecimiento
    for name, df in [("xlsx", df_xlsx), ("csv", df_csv)]:
        df["estado_norm"] = df["estado"].map(normalize_text_value)
        df["municipio_norm"] = df["municipio"].map(normalize_text_value)
        df["predio_norm"] = df["predio"].map(normalize_text_value)
        df["predio"] = df["predio"].map(to_title_case)
        df["municipio"] = df["municipio"].map(to_title_case)
        df["estado"] = df["estado"].map(to_title_case)
        df["estado"] = canonical_estado_display(df["estado"])

        if name == "xlsx":
            df_xlsx = normalize_zero_coordinates(df)
            df_xlsx = normalize_geo_keys(df_xlsx)
        else:
            df_csv = normalize_zero_coordinates(df)
            df_csv = normalize_geo_keys(df_csv)

    df_work_total = pd.concat([df_xlsx[WORK_COLUMNS], df_csv[WORK_COLUMNS]], ignore_index=True)

    print("Generando reporte de inválidos...")
    invalidos = build_invalid_records_report(df_work_total)

    print("Filtrando registros válidos...")
    df_work_valid = filter_valid_records(df_work_total)
    df_final = df_work_valid[FINAL_COLUMNS].copy()

    print("Generando reportes...")
    matriz = build_homologation_matrix()
    resumen = build_summary(
        df_xlsx=df_xlsx,
        df_csv=df_csv,
        df_work_total=df_work_total,
        df_final=df_final,
        incidencias=invalidos,
    )

    print("Guardando salidas...")
    matriz.to_csv(OUT_MATRIZ, index=False, encoding="utf-8-sig")
    invalidos.to_csv(OUT_INVALIDOS, index=False, encoding="utf-8-sig")
    df_final.to_csv(OUT_CONSOLIDADO, index=False, encoding="utf-8-sig")
    resumen.to_csv(OUT_RESUMEN, index=False, encoding="utf-8-sig")

    print("\nProceso finalizado.")
    print(f"Tabla consolidada: {OUT_CONSOLIDADO}")
    print(f"Resumen:           {OUT_RESUMEN}")
    print(f"Inválidos:         {OUT_INVALIDOS}")


if __name__ == "__main__":
    main()