# -*- coding: utf-8 -*-
"""
CONAFOR | DP05 - QC final del consolidado 2005-2025

Entrada
-------
- datasets/conafor_eventos_2005_2025_consolidado.csv

Salidas
-------
- datasets/conafor_eventos_2005_2025_limpio.csv
- reports/dp05_resumen_qc_final_2005_2025.csv
- reports/dp05_incidencias_qc_final_2005_2025.csv

Objetivo
--------
Validar el dataset consolidado 2005-2025 generado en DP04 y producir
un dataset limpio/controlado para etapas posteriores.

Este script:
- NO realiza modelado.
- NO escala variables.
- NO selecciona features.
- NO hace PCA, SOM, clustering ni evaluación.
- NO elimina registros por cve_mun faltante.
- NO corrige fechas invertidas automáticamente.
- Genera flags de calidad para decisiones posteriores.

Criterio
--------
Errores bloqueantes:
- clave_incendio nula
- clave_incendio duplicada
- anio nulo
- anio fuera de 2005-2025
- fecha_inicio nula
- latitud/longitud nula
- coordenadas fuera de bbox México
- longitud incorrecta de cve_ent cuando existe
- longitud incorrecta de cve_mun cuando existe

Advertencias:
- fecha_termino nula
- fecha_termino < fecha_inicio
- cve_ent nula
- cve_mun nula
- anio diferente al año de fecha_inicio
- posible mojibake visible
"""

from __future__ import annotations

from pathlib import Path
from typing import Any
import re
import unicodedata

import pandas as pd


# ============================================================
# CONFIGURACIÓN
# ============================================================

BASE_DIR = Path(r"C:\Users\Hp\OneDrive\Documentos\PT_Analisis")

PATH_CONSOLIDADO = (
    BASE_DIR
    / "03_data-preparation"
    / "conafor"
    / "datasets"
    / "conafor_eventos_2005_2025_consolidado.csv"
)

OUT_DIR = BASE_DIR / "03_data-preparation" / "conafor"
OUT_DATASETS = OUT_DIR / "datasets"
OUT_REPORTS = OUT_DIR / "reports"

OUT_DATASETS.mkdir(parents=True, exist_ok=True)
OUT_REPORTS.mkdir(parents=True, exist_ok=True)

OUT_LIMPIO = OUT_DATASETS / "conafor_eventos_2005_2025_limpio.csv"
OUT_RESUMEN = OUT_REPORTS / "dp05_resumen_qc_final_2005_2025.csv"
OUT_INCIDENCIAS = OUT_REPORTS / "dp05_incidencias_qc_final_2005_2025.csv"

ANIO_MIN = 2005
ANIO_MAX = 2025

MEX_BBOX = {
    "min_lon": -118.366667,
    "min_lat": 14.533334,
    "max_lon": -86.708334,
    "max_lat": 32.716667,
}


# ============================================================
# ESQUEMA ESPERADO
# ============================================================

BASE_COLUMNS = [
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
    "estado_integracion",
    "clasificacion_match",
    "score_consistencia",
    "coord_dist_deg",
    "fuente_tabular",
    "fuente_preferente",
]

QC_COLUMNS = [
    "flag_error_bloqueante",
    "flag_advertencia",
    "flag_apto_ml_espacial",
    "flag_apto_agregacion_municipal",
    "flag_apto_variables_duracion",
    "motivos_qc",
]


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


def safe_string(value: Any) -> Any:
    if pd.isna(value):
        return pd.NA

    s = str(value).strip()

    if not s or s.lower() in {"nan", "nan.0", "<na>", "none"}:
        return pd.NA

    return s


def normalize_clave_incendio(value: Any) -> Any:
    s = safe_string(value)

    if pd.isna(s):
        return pd.NA

    s = str(s).upper()
    s = re.sub(r"\s+", "", s)

    return s


def normalize_code(value: Any, width: int) -> Any:
    s = safe_string(value)

    if pd.isna(s):
        return pd.NA

    num = pd.to_numeric(pd.Series([s]), errors="coerce").iloc[0]

    if pd.notna(num):
        try:
            s = str(int(num))
        except Exception:
            s = str(s)

    digits = re.sub(r"\D", "", str(s))

    if not digits:
        return pd.NA

    if len(digits) > width:
        digits = digits[-width:]

    return digits.zfill(width)


def parse_date_series(series: pd.Series) -> pd.Series:
    """
    Convierte una serie de fechas a datetime de forma robusta.

    Soporta:
    - YYYY-MM-DD
    - YYYY-MM-DD HH:MM:SS
    - DD/MM/YYYY
    - DD/MM/YYYY HH:MM:SS
    - seriales de Excel

    Esta versión evita que pandas infiera mal formatos mixtos y marque
    como nulas fechas válidas como 2015-01-14.
    """
    s = series.astype("string").str.strip()
    s = s.replace(
        {
            "": pd.NA,
            "nan": pd.NA,
            "NaN": pd.NA,
            "<NA>": pd.NA,
            "None": pd.NA,
            "NaT": pd.NA,
        }
    )

    out = pd.Series(pd.NaT, index=s.index, dtype="datetime64[ns]")

    # YYYY-MM-DD
    mask_ymd = s.str.match(r"^\d{4}-\d{1,2}-\d{1,2}$", na=False)
    if mask_ymd.any():
        out.loc[mask_ymd] = pd.to_datetime(
            s.loc[mask_ymd],
            format="%Y-%m-%d",
            errors="coerce",
        )

    # YYYY-MM-DD HH:MM:SS
    mask_ymd_hms = s.str.match(
        r"^\d{4}-\d{1,2}-\d{1,2} \d{1,2}:\d{2}:\d{2}$",
        na=False,
    )
    if mask_ymd_hms.any():
        out.loc[mask_ymd_hms] = pd.to_datetime(
            s.loc[mask_ymd_hms],
            format="%Y-%m-%d %H:%M:%S",
            errors="coerce",
        )

    # DD/MM/YYYY
    mask_dmy = s.str.match(r"^\d{1,2}/\d{1,2}/\d{4}$", na=False)
    if mask_dmy.any():
        out.loc[mask_dmy] = pd.to_datetime(
            s.loc[mask_dmy],
            format="%d/%m/%Y",
            errors="coerce",
        )

    # DD/MM/YYYY HH:MM:SS
    mask_dmy_hms = s.str.match(
        r"^\d{1,2}/\d{1,2}/\d{4} \d{1,2}:\d{2}:\d{2}$",
        na=False,
    )
    if mask_dmy_hms.any():
        out.loc[mask_dmy_hms] = pd.to_datetime(
            s.loc[mask_dmy_hms],
            format="%d/%m/%Y %H:%M:%S",
            errors="coerce",
        )

    # Seriales de Excel
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

    # Último intento genérico, solo para lo que aún no se pudo convertir.
    mask_pending = out.isna() & s.notna()
    if mask_pending.any():
        out.loc[mask_pending] = pd.to_datetime(
            s.loc[mask_pending],
            errors="coerce",
            dayfirst=True,
        )

    return out


def has_mojibake(value: Any) -> bool:
    if pd.isna(value):
        return False

    s = str(value)

    return any(token in s for token in ["Ã", "Â", "�"])


def validate_bbox_mexico(lat: pd.Series, lon: pd.Series) -> pd.Series:
    lat_num = pd.to_numeric(lat, errors="coerce")
    lon_num = pd.to_numeric(lon, errors="coerce")

    return (
        lat_num.between(MEX_BBOX["min_lat"], MEX_BBOX["max_lat"], inclusive="both")
        & lon_num.between(MEX_BBOX["min_lon"], MEX_BBOX["max_lon"], inclusive="both")
    )


def join_motivos(row: pd.Series, flag_cols: list[str]) -> Any:
    motivos = [col for col in flag_cols if bool(row.get(col, False))]

    if not motivos:
        return pd.NA

    return "; ".join(motivos)


# ============================================================
# LECTURA Y NORMALIZACIÓN
# ============================================================

def read_consolidado(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"No existe el consolidado: {path}")

    df = pd.read_csv(path, encoding="utf-8-sig", dtype=str)
    df.columns = [normalize_column_name(c) for c in df.columns]

    for col in BASE_COLUMNS:
        if col not in df.columns:
            df[col] = pd.NA

    df = df[BASE_COLUMNS].copy()

    # Normalización de tipos mínimos.
    df["anio"] = pd.to_numeric(df["anio"], errors="coerce").astype("Int64")
    df["clave_incendio"] = df["clave_incendio"].map(normalize_clave_incendio)

    df["cve_ent"] = df["cve_ent"].map(lambda x: normalize_code(x, 2))
    df["cve_mun"] = df["cve_mun"].map(lambda x: normalize_code(x, 3))

    df["latitud"] = pd.to_numeric(df["latitud"], errors="coerce")
    df["longitud"] = pd.to_numeric(df["longitud"], errors="coerce")
    df["superficie_total_ha"] = pd.to_numeric(df["superficie_total_ha"], errors="coerce")
    df["score_consistencia"] = pd.to_numeric(df["score_consistencia"], errors="coerce")
    df["coord_dist_deg"] = pd.to_numeric(df["coord_dist_deg"], errors="coerce")

    text_cols = [
        "estado",
        "municipio",
        "region",
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
        "superficie_categoria",
        "estado_integracion",
        "clasificacion_match",
        "fuente_tabular",
        "fuente_preferente",
    ]

    for col in text_cols:
        df[col] = df[col].map(safe_string)

    return df


# ============================================================
# FLAGS QC
# ============================================================

def add_qc_flags(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()

    fecha_inicio_dt = parse_date_series(out["fecha_inicio"])
    fecha_termino_dt = parse_date_series(out["fecha_termino"])

    anio_inicio = fecha_inicio_dt.dt.year.astype("Int64")

    coord_valida_mexico = validate_bbox_mexico(out["latitud"], out["longitud"])

    clave_dup = (
        out["clave_incendio"].duplicated(keep=False)
        & out["clave_incendio"].notna()
    )

    # --------------------------------------------------------
    # Errores bloqueantes
    # --------------------------------------------------------
    out["qc_clave_incendio_nula"] = out["clave_incendio"].isna()
    out["qc_clave_incendio_duplicada"] = clave_dup

    out["qc_anio_nulo"] = out["anio"].isna()
    out["qc_anio_fuera_periodo"] = (
        out["anio"].notna()
        & ~out["anio"].between(ANIO_MIN, ANIO_MAX, inclusive="both")
    )

    out["qc_fecha_inicio_nula"] = fecha_inicio_dt.isna()

    out["qc_latitud_nula"] = out["latitud"].isna()
    out["qc_longitud_nula"] = out["longitud"].isna()

    out["qc_coord_fuera_bbox_mexico"] = (
        out["latitud"].notna()
        & out["longitud"].notna()
        & ~coord_valida_mexico
    )

    out["qc_cve_ent_longitud_incorrecta"] = (
        out["cve_ent"].notna()
        & ~out["cve_ent"].astype("string").str.match(r"^\d{2}$", na=False)
    )

    out["qc_cve_mun_longitud_incorrecta"] = (
        out["cve_mun"].notna()
        & ~out["cve_mun"].astype("string").str.match(r"^\d{3}$", na=False)
    )

    # --------------------------------------------------------
    # Advertencias
    # --------------------------------------------------------
    out["qc_fecha_termino_nula"] = fecha_termino_dt.isna()

    out["qc_fecha_invertida"] = (
        fecha_inicio_dt.notna()
        & fecha_termino_dt.notna()
        & (fecha_termino_dt < fecha_inicio_dt)
    )

    out["qc_cve_ent_nula"] = out["cve_ent"].isna()
    out["qc_cve_mun_nula"] = out["cve_mun"].isna()

    out["qc_anio_fecha_inicio_diferente"] = (
        out["anio"].notna()
        & anio_inicio.notna()
        & (out["anio"] != anio_inicio)
    )

    text_cols_for_mojibake = [
        "estado",
        "municipio",
        "region",
        "predio",
        "causa",
        "causa_especifica",
        "tipo_incendio",
        "tipo_impacto",
        "tipo_vegetacion",
    ]

    mojibake_mask = pd.Series(False, index=out.index)

    for col in text_cols_for_mojibake:
        if col in out.columns:
            mojibake_mask = mojibake_mask | out[col].map(has_mojibake).fillna(False)

    out["qc_mojibake_visible"] = mojibake_mask

    error_cols = [
        "qc_clave_incendio_nula",
        "qc_clave_incendio_duplicada",
        "qc_anio_nulo",
        "qc_anio_fuera_periodo",
        "qc_fecha_inicio_nula",
        "qc_latitud_nula",
        "qc_longitud_nula",
        "qc_coord_fuera_bbox_mexico",
        "qc_cve_ent_longitud_incorrecta",
        "qc_cve_mun_longitud_incorrecta",
    ]

    warning_cols = [
        "qc_fecha_termino_nula",
        "qc_fecha_invertida",
        "qc_cve_ent_nula",
        "qc_cve_mun_nula",
        "qc_anio_fecha_inicio_diferente",
        "qc_mojibake_visible",
    ]

    out["flag_error_bloqueante"] = out[error_cols].fillna(False).any(axis=1)
    out["flag_advertencia"] = out[warning_cols].fillna(False).any(axis=1)

    out["flag_apto_ml_espacial"] = ~out["flag_error_bloqueante"]

    out["flag_apto_agregacion_municipal"] = (
        ~out["flag_error_bloqueante"]
        & out["cve_ent"].notna()
        & out["cve_mun"].notna()
    )

    out["flag_apto_variables_duracion"] = (
        ~out["flag_error_bloqueante"]
        & fecha_inicio_dt.notna()
        & fecha_termino_dt.notna()
        & (fecha_termino_dt >= fecha_inicio_dt)
    )

    out["motivos_qc"] = out.apply(
        lambda row: join_motivos(row, error_cols + warning_cols),
        axis=1,
    )

    return out


# ============================================================
# REPORTES
# ============================================================

def build_summary(df_qc: pd.DataFrame, df_limpio: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []

    rows.extend([
        {"metrica": "registros_entrada_consolidado", "valor": len(df_qc)},
        {"metrica": "registros_limpios_salida", "valor": len(df_limpio)},
        {"metrica": "columnas_limpio_salida", "valor": len(df_limpio.columns)},
        {"metrica": "registros_con_error_bloqueante", "valor": int(df_qc["flag_error_bloqueante"].sum())},
        {"metrica": "registros_con_advertencia", "valor": int(df_qc["flag_advertencia"].sum())},
        {"metrica": "registros_aptos_ml_espacial", "valor": int(df_qc["flag_apto_ml_espacial"].sum())},
        {"metrica": "registros_aptos_agregacion_municipal", "valor": int(df_qc["flag_apto_agregacion_municipal"].sum())},
        {"metrica": "registros_aptos_variables_duracion", "valor": int(df_qc["flag_apto_variables_duracion"].sum())},
    ])

    qc_cols = [c for c in df_qc.columns if c.startswith("qc_")]

    for col in qc_cols:
        rows.append({
            "metrica": col,
            "valor": int(df_qc[col].fillna(False).sum()),
        })

    if "estado_integracion" in df_qc.columns:
        for value, count in df_qc["estado_integracion"].value_counts(dropna=False).items():
            rows.append({
                "metrica": f"estado_integracion_{value}",
                "valor": int(count),
            })

    if "clasificacion_match" in df_qc.columns:
        for value, count in df_qc["clasificacion_match"].value_counts(dropna=False).items():
            rows.append({
                "metrica": f"clasificacion_match_{value}",
                "valor": int(count),
            })

    return pd.DataFrame(rows)


def build_incidencias(df_qc: pd.DataFrame) -> pd.DataFrame:
    incidencias = df_qc[
        df_qc["flag_error_bloqueante"]
        | df_qc["flag_advertencia"]
    ].copy()

    keep_cols = [
        "anio",
        "clave_incendio",
        "estado",
        "municipio",
        "cve_ent",
        "cve_mun",
        "fecha_inicio",
        "fecha_termino",
        "latitud",
        "longitud",
        "estado_integracion",
        "clasificacion_match",
        "flag_error_bloqueante",
        "flag_advertencia",
        "flag_apto_ml_espacial",
        "flag_apto_agregacion_municipal",
        "flag_apto_variables_duracion",
        "motivos_qc",
    ]

    for col in keep_cols:
        if col not in incidencias.columns:
            incidencias[col] = pd.NA

    incidencias = incidencias[keep_cols].copy()

    incidencias = incidencias.sort_values(
        by=[
            "flag_error_bloqueante",
            "flag_advertencia",
            "estado_integracion",
            "estado",
            "municipio",
            "anio",
        ],
        ascending=[False, False, True, True, True, True],
        na_position="last",
    )

    return incidencias


# ============================================================
# MAIN
# ============================================================

def main() -> None:
    print("CONAFOR | DP05 - QC final 2005-2025")
    print("Leyendo consolidado DP04...")

    df = read_consolidado(PATH_CONSOLIDADO)

    print(f"Registros de entrada: {len(df):,}")

    print("Generando flags QC...")
    df_qc = add_qc_flags(df)

    # Dataset limpio/controlado:
    # solo se excluyen errores bloqueantes.
    # Las advertencias se conservan con flags para tratamiento posterior.
    df_limpio = df_qc[~df_qc["flag_error_bloqueante"]].copy()

    output_cols = BASE_COLUMNS + QC_COLUMNS

    for col in output_cols:
        if col not in df_limpio.columns:
            df_limpio[col] = pd.NA

    df_limpio = df_limpio[output_cols].copy()

    print("Construyendo reportes...")
    resumen = build_summary(df_qc, df_limpio)
    incidencias = build_incidencias(df_qc)

    print("Guardando salidas...")
    df_limpio.to_csv(OUT_LIMPIO, index=False, encoding="utf-8-sig")
    resumen.to_csv(OUT_RESUMEN, index=False, encoding="utf-8-sig")
    incidencias.to_csv(OUT_INCIDENCIAS, index=False, encoding="utf-8-sig")

    print("\nProceso finalizado.")
    print(f"Dataset limpio: {OUT_LIMPIO}")
    print(f"Resumen QC:     {OUT_RESUMEN}")
    print(f"Incidencias:    {OUT_INCIDENCIAS}")

    print("\nResumen rápido:")
    print(f"- Registros entrada:             {len(df_qc):,}")
    print(f"- Registros salida limpio:       {len(df_limpio):,}")
    print(f"- Errores bloqueantes:           {int(df_qc['flag_error_bloqueante'].sum()):,}")
    print(f"- Advertencias:                  {int(df_qc['flag_advertencia'].sum()):,}")
    print(f"- Aptos ML espacial:             {int(df_qc['flag_apto_ml_espacial'].sum()):,}")
    print(f"- Aptos agregación municipal:    {int(df_qc['flag_apto_agregacion_municipal'].sum()):,}")
    print(f"- Aptos variables duración:      {int(df_qc['flag_apto_variables_duracion'].sum()):,}")


if __name__ == "__main__":
    main()