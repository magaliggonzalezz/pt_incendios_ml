# -*- coding: utf-8 -*-
"""
CONAFOR | DP03 - Integración tabular + SHP 2015-2025

Entrada
-------
- conafor_match_tabular_shp_2015_2025.csv

Salida
------
- datasets/conafor_eventos_2015_2025_integrado.csv
- reports/dp03_resumen_integracion_2015_2025.csv

Objetivo
--------
Construir un dataset integrado único para el universo comparable 2015-2025:

- both: registros presentes en tabular y SHP.
- solo_tabular: registros presentes solo en el tabular CONAFOR.
- solo_shp: registros presentes solo en el SHP histórico de puntos.

Notas metodológicas
-------------------
- No corrige coordenadas invertidas porque DP02 ya lee el SHP usando geometry.x / geometry.y.
- Conserva trazabilidad mínima para justificar la integración:
  estado_integracion, clasificacion_match, score_consistencia y coord_dist_deg.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any
import re
import unicodedata

import numpy as np
import pandas as pd


# ============================================================
# CONFIGURACIÓN
# ============================================================

BASE_DIR = Path(r"C:\Users\Hp\OneDrive\Documentos\PT_Analisis")

PATH_MATCH = (
    BASE_DIR
    / "03_data-preparation"
    / "conafor"
    / "datasets"
    / "conafor_match_tabular_shp_2015_2025.csv"
)

OUT_DIR = BASE_DIR / "03_data-preparation" / "conafor"
OUT_DATASETS = OUT_DIR / "datasets"
OUT_REPORTS = OUT_DIR / "reports"

OUT_DATASETS.mkdir(parents=True, exist_ok=True)
OUT_REPORTS.mkdir(parents=True, exist_ok=True)

OUT_INTEGRADO = OUT_DATASETS / "conafor_eventos_2015_2025_integrado.csv"
OUT_RESUMEN = OUT_REPORTS / "dp03_resumen_integracion_2015_2025.csv"


# ============================================================
# ESQUEMA FINAL
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
    "estado_integracion",
    "clasificacion_match",
    "score_consistencia",
    "coord_dist_deg",
    "fuente_tabular",
    "fuente_preferente",
]


# ============================================================
# UTILIDADES
# ============================================================

def strip_accents(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", text)
    return "".join(ch for ch in normalized if not unicodedata.combining(ch))


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
        "df": "ciudad de mexico",
        "cdmx": "ciudad de mexico",
        "estado de mexico": "mexico",
        "edo mexico": "mexico",
        "edo. mexico": "mexico",
        "coahuila": "coahuila de zaragoza",
        "veracruz": "veracruz de ignacio de la llave",
        "michoacan": "michoacan de ocampo",
        "tlaxacala": "tlaxcala",
    }

    return replacements.get(s, s)


def safe_string(value: Any) -> Any:
    if pd.isna(value):
        return pd.NA

    s = str(value).strip()
    if not s or s.lower() in {"nan", "nan.0", "<na>", "none"}:
        return pd.NA

    return s


def choose_first_non_null(*values: Any) -> Any:
    for value in values:
        if pd.notna(value):
            return value
    return pd.NA


def to_numeric_scalar(value: Any) -> Any:
    if pd.isna(value):
        return pd.NA

    try:
        num = pd.to_numeric(pd.Series([value]), errors="coerce").iloc[0]
        return pd.NA if pd.isna(num) else num
    except Exception:
        return pd.NA


def normalize_code(value: Any, width: int) -> Any:
    s = safe_string(value)
    if pd.isna(s):
        return pd.NA

    num = pd.to_numeric(pd.Series([s]), errors="coerce").iloc[0]
    if pd.notna(num):
        try:
            return str(int(num)).zfill(width)
        except Exception:
            pass

    digits = re.sub(r"\D", "", str(s))
    if not digits:
        return pd.NA

    if len(digits) > width:
        digits = digits[-width:]

    return digits.zfill(width)


def normalize_clave_incendio(value: Any) -> Any:
    s = safe_string(value)
    if pd.isna(s):
        return pd.NA

    s = str(s).upper()
    s = re.sub(r"\s+", "", s)
    return s


def parse_date_scalar(value: Any) -> Any:
    s = safe_string(value)
    if pd.isna(s):
        return pd.NA

    s = str(s).strip()

    patterns = [
        ("%d/%m/%Y %H:%M:%S", r"^\d{1,2}/\d{1,2}/\d{4} \d{1,2}:\d{2}:\d{2}$"),
        ("%d/%m/%Y", r"^\d{1,2}/\d{1,2}/\d{4}$"),
        ("%Y-%m-%d %H:%M:%S", r"^\d{4}-\d{1,2}-\d{1,2} \d{1,2}:\d{2}:\d{2}$"),
        ("%Y-%m-%d", r"^\d{4}-\d{1,2}-\d{1,2}$"),
    ]

    for fmt, pattern in patterns:
        if re.match(pattern, s):
            dt = pd.to_datetime(s, format=fmt, errors="coerce")
            return pd.NA if pd.isna(dt) else dt.strftime("%Y-%m-%d")

    serial = pd.to_numeric(pd.Series([s]), errors="coerce").iloc[0]
    if pd.notna(serial):
        dt = pd.to_datetime(serial, unit="D", origin="1899-12-30", errors="coerce")
        return pd.NA if pd.isna(dt) else dt.strftime("%Y-%m-%d")

    dt = pd.to_datetime(s, errors="coerce", dayfirst=True)
    return pd.NA if pd.isna(dt) else dt.strftime("%Y-%m-%d")


def is_valid_lat(lat: Any) -> bool:
    lat_num = to_numeric_scalar(lat)
    return pd.notna(lat_num) and (-90 <= lat_num <= 90)


def is_valid_lon(lon: Any) -> bool:
    lon_num = to_numeric_scalar(lon)
    return pd.notna(lon_num) and (-180 <= lon_num <= 180)


# ============================================================
# RESCATE SEMÁNTICO DE CLASIFICACIONES SHP
# ============================================================

IMPACTO_MAP = {
    "impacto minimo": "Impacto Mínimo",
    "impacto moderado": "Impacto Moderado",
    "impacto severo": "Impacto Severo",
    "minimo": "Impacto Mínimo",
    "moderado": "Impacto Moderado",
    "severo": "Impacto Severo",
}

REGIMEN_MAP = {
    "adaptado": "Adaptado",
    "dependiente": "Dependiente",
    "sensible": "Sensible",
    "influidos": "Influidos",
    "independiente": "Independiente",
    "otros": "Otros",
    "condiciones especiales": "Condiciones Especiales",
}


def recover_shp_impacto_regimen(value_a: Any, value_b: Any) -> tuple[Any, Any]:
    impacto = pd.NA
    regimen = pd.NA

    for value in [value_a, value_b]:
        if pd.isna(value):
            continue

        s = normalize_text_value(value)
        if pd.isna(s):
            continue

        if s in IMPACTO_MAP and pd.isna(impacto):
            impacto = IMPACTO_MAP[s]

        if s in REGIMEN_MAP and pd.isna(regimen):
            regimen = REGIMEN_MAP[s]

    return impacto, regimen


# ============================================================
# RESOLUCIÓN DE CAMPOS
# ============================================================

def resolve_estado_integracion(merge_value: Any) -> str:
    if merge_value == "both":
        return "both"
    if merge_value == "left_only":
        return "solo_tabular"
    if merge_value == "right_only":
        return "solo_shp"
    return "desconocido"


def resolve_coords(row: pd.Series) -> tuple[Any, Any]:
    """
    DP02 ya corrigió la lectura del SHP:
    - shp_longitud = geometry.x
    - shp_latitud  = geometry.y

    Por tanto, aquí NO se invierten coordenadas.
    Se prioriza tabular cuando está disponible y válido;
    si no, se usa SHP.
    """
    tab_lat = to_numeric_scalar(row.get("tab_latitud"))
    tab_lon = to_numeric_scalar(row.get("tab_longitud"))
    shp_lat = to_numeric_scalar(row.get("shp_latitud"))
    shp_lon = to_numeric_scalar(row.get("shp_longitud"))

    tab_ok = is_valid_lat(tab_lat) and is_valid_lon(tab_lon)
    shp_ok = is_valid_lat(shp_lat) and is_valid_lon(shp_lon)

    if tab_ok:
        return tab_lat, tab_lon

    if shp_ok:
        return shp_lat, shp_lon

    return choose_first_non_null(tab_lat, shp_lat), choose_first_non_null(tab_lon, shp_lon)


def resolve_cve_ent(row: pd.Series) -> Any:
    return choose_first_non_null(
        normalize_code(row.get("tab_cve_ent"), 2),
        normalize_code(row.get("shp_cve_ent"), 2),
    )


def resolve_cve_mun(row: pd.Series) -> Any:
    return choose_first_non_null(
        normalize_code(row.get("tab_cve_mun"), 3),
        normalize_code(row.get("shp_cve_mun"), 3),
    )


def resolve_predio(row: pd.Series) -> Any:
    return choose_first_non_null(
        safe_string(row.get("tab_predio")),
        safe_string(row.get("shp_predio")),
    )


def resolve_superficie(row: pd.Series) -> Any:
    return choose_first_non_null(
        to_numeric_scalar(row.get("tab_superficie_total_ha")),
        to_numeric_scalar(row.get("shp_superficie_total_ha")),
    )


def resolve_tipo_impacto(row: pd.Series) -> Any:
    tab_value = safe_string(row.get("tab_tipo_impacto"))
    if pd.notna(tab_value):
        return tab_value

    shp_impacto, _ = recover_shp_impacto_regimen(
        row.get("shp_clasificac"),
        row.get("shp_clasifi_01"),
    )
    return shp_impacto


def resolve_regimen_fuego(row: pd.Series) -> Any:
    tab_value = safe_string(row.get("tab_regimen_fuego"))
    if pd.notna(tab_value):
        return tab_value

    _, shp_regimen = recover_shp_impacto_regimen(
        row.get("shp_clasificac"),
        row.get("shp_clasifi_01"),
    )
    return shp_regimen


def get_trace_values(row: pd.Series) -> dict[str, Any]:
    return {
        "clasificacion_match": safe_string(row.get("clasificacion_match")),
        "score_consistencia": to_numeric_scalar(row.get("score_consistencia")),
        "coord_dist_deg": to_numeric_scalar(row.get("coord_dist_deg")),
        "fuente_tabular": safe_string(row.get("tab_fuente")),
    }


# ============================================================
# CONSTRUCCIÓN DE FILAS
# ============================================================

def build_row_both(row: pd.Series) -> dict[str, Any]:
    latitud, longitud = resolve_coords(row)
    trace = get_trace_values(row)

    return {
        "anio": choose_first_non_null(
            to_numeric_scalar(row.get("tab_anio")),
            to_numeric_scalar(row.get("shp_anio")),
        ),
        "clave_incendio": choose_first_non_null(
            normalize_clave_incendio(row.get("tab_clave_incendio")),
            normalize_clave_incendio(row.get("shp_clave_incendio")),
        ),
        "estado": choose_first_non_null(
            safe_string(row.get("tab_estado")),
            safe_string(row.get("shp_estado")),
        ),
        "cve_ent": resolve_cve_ent(row),
        "municipio": choose_first_non_null(
            safe_string(row.get("tab_municipio")),
            safe_string(row.get("shp_municipio")),
        ),
        "cve_mun": resolve_cve_mun(row),
        "region": choose_first_non_null(
            safe_string(row.get("tab_region")),
            safe_string(row.get("shp_region")),
        ),
        "latitud": latitud,
        "longitud": longitud,
        "fecha_inicio": choose_first_non_null(
            parse_date_scalar(row.get("tab_fecha_inicio")),
            parse_date_scalar(row.get("shp_fecha_inicio")),
        ),
        "fecha_termino": choose_first_non_null(
            parse_date_scalar(row.get("tab_fecha_termino")),
            parse_date_scalar(row.get("shp_fecha_termino")),
        ),
        "deteccion": safe_string(row.get("tab_deteccion")),
        "llegada": safe_string(row.get("tab_llegada")),
        "duracion": safe_string(row.get("tab_duracion")),
        "duracion_categoria": safe_string(row.get("tab_duracion_categoria")),
        "causa": safe_string(row.get("tab_causa")),
        "causa_especifica": safe_string(row.get("tab_causa_especifica")),
        "predio": resolve_predio(row),
        "regimen_fuego": resolve_regimen_fuego(row),
        "tipo_incendio": choose_first_non_null(
            safe_string(row.get("tab_tipo_incendio")),
            safe_string(row.get("shp_tipo_incendio")),
        ),
        "tipo_impacto": resolve_tipo_impacto(row),
        "tipo_vegetacion": choose_first_non_null(
            safe_string(row.get("tab_tipo_vegetacion")),
            safe_string(row.get("shp_tipo_vegetacion")),
        ),
        "superficie_total_ha": resolve_superficie(row),
        "superficie_categoria": safe_string(row.get("tab_superficie_categoria")),
        "arbolado_adulto": to_numeric_scalar(row.get("tab_arbolado_adulto")),
        "arbustivo": to_numeric_scalar(row.get("tab_arbustivo")),
        "herbaceo": to_numeric_scalar(row.get("tab_herbaceo")),
        "hojarasca": to_numeric_scalar(row.get("tab_hojarasca")),
        "renuevo": to_numeric_scalar(row.get("tab_renuevo")),
        "estado_integracion": "both",
        "clasificacion_match": trace["clasificacion_match"],
        "score_consistencia": trace["score_consistencia"],
        "coord_dist_deg": trace["coord_dist_deg"],
        "fuente_tabular": trace["fuente_tabular"],
        "fuente_preferente": "tabular",
    }


def build_row_solo_tabular(row: pd.Series) -> dict[str, Any]:
    trace = get_trace_values(row)

    return {
        "anio": to_numeric_scalar(row.get("tab_anio")),
        "clave_incendio": normalize_clave_incendio(row.get("tab_clave_incendio")),
        "estado": safe_string(row.get("tab_estado")),
        "cve_ent": normalize_code(row.get("tab_cve_ent"), 2),
        "municipio": safe_string(row.get("tab_municipio")),
        "cve_mun": normalize_code(row.get("tab_cve_mun"), 3),
        "region": safe_string(row.get("tab_region")),
        "latitud": to_numeric_scalar(row.get("tab_latitud")),
        "longitud": to_numeric_scalar(row.get("tab_longitud")),
        "fecha_inicio": parse_date_scalar(row.get("tab_fecha_inicio")),
        "fecha_termino": parse_date_scalar(row.get("tab_fecha_termino")),
        "deteccion": safe_string(row.get("tab_deteccion")),
        "llegada": safe_string(row.get("tab_llegada")),
        "duracion": safe_string(row.get("tab_duracion")),
        "duracion_categoria": safe_string(row.get("tab_duracion_categoria")),
        "causa": safe_string(row.get("tab_causa")),
        "causa_especifica": safe_string(row.get("tab_causa_especifica")),
        "predio": safe_string(row.get("tab_predio")),
        "regimen_fuego": safe_string(row.get("tab_regimen_fuego")),
        "tipo_incendio": safe_string(row.get("tab_tipo_incendio")),
        "tipo_impacto": safe_string(row.get("tab_tipo_impacto")),
        "tipo_vegetacion": safe_string(row.get("tab_tipo_vegetacion")),
        "superficie_total_ha": to_numeric_scalar(row.get("tab_superficie_total_ha")),
        "superficie_categoria": safe_string(row.get("tab_superficie_categoria")),
        "arbolado_adulto": to_numeric_scalar(row.get("tab_arbolado_adulto")),
        "arbustivo": to_numeric_scalar(row.get("tab_arbustivo")),
        "herbaceo": to_numeric_scalar(row.get("tab_herbaceo")),
        "hojarasca": to_numeric_scalar(row.get("tab_hojarasca")),
        "renuevo": to_numeric_scalar(row.get("tab_renuevo")),
        "estado_integracion": "solo_tabular",
        "clasificacion_match": trace["clasificacion_match"],
        "score_consistencia": trace["score_consistencia"],
        "coord_dist_deg": trace["coord_dist_deg"],
        "fuente_tabular": trace["fuente_tabular"],
        "fuente_preferente": "tabular",
    }


def build_row_solo_shp(row: pd.Series) -> dict[str, Any]:
    shp_impacto, shp_regimen = recover_shp_impacto_regimen(
        row.get("shp_clasificac"),
        row.get("shp_clasifi_01"),
    )

    trace = get_trace_values(row)

    return {
        "anio": to_numeric_scalar(row.get("shp_anio")),
        "clave_incendio": normalize_clave_incendio(row.get("shp_clave_incendio")),
        "estado": safe_string(row.get("shp_estado")),
        "cve_ent": normalize_code(row.get("shp_cve_ent"), 2),
        "municipio": safe_string(row.get("shp_municipio")),
        "cve_mun": normalize_code(row.get("shp_cve_mun"), 3),
        "region": safe_string(row.get("shp_region")),
        "latitud": to_numeric_scalar(row.get("shp_latitud")),
        "longitud": to_numeric_scalar(row.get("shp_longitud")),
        "fecha_inicio": parse_date_scalar(row.get("shp_fecha_inicio")),
        "fecha_termino": parse_date_scalar(row.get("shp_fecha_termino")),
        "deteccion": pd.NA,
        "llegada": pd.NA,
        "duracion": pd.NA,
        "duracion_categoria": pd.NA,
        "causa": pd.NA,
        "causa_especifica": pd.NA,
        "predio": safe_string(row.get("shp_predio")),
        "regimen_fuego": shp_regimen,
        "tipo_incendio": safe_string(row.get("shp_tipo_incendio")),
        "tipo_impacto": shp_impacto,
        "tipo_vegetacion": safe_string(row.get("shp_tipo_vegetacion")),
        "superficie_total_ha": to_numeric_scalar(row.get("shp_superficie_total_ha")),
        "superficie_categoria": pd.NA,
        "arbolado_adulto": pd.NA,
        "arbustivo": pd.NA,
        "herbaceo": pd.NA,
        "hojarasca": pd.NA,
        "renuevo": pd.NA,
        "estado_integracion": "solo_shp",
        "clasificacion_match": trace["clasificacion_match"],
        "score_consistencia": trace["score_consistencia"],
        "coord_dist_deg": trace["coord_dist_deg"],
        "fuente_tabular": pd.NA,
        "fuente_preferente": "shp",
    }


# ============================================================
# VALIDACIÓN Y RESUMEN
# ============================================================

def apply_final_schema(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()

    for col in FINAL_COLUMNS:
        if col not in out.columns:
            out[col] = pd.NA

    return out[FINAL_COLUMNS].copy()


def build_summary(out: pd.DataFrame) -> pd.DataFrame:
    fi = pd.to_datetime(out["fecha_inicio"], errors="coerce")
    ft = pd.to_datetime(out["fecha_termino"], errors="coerce")

    fechas_invertidas = fi.notna() & ft.notna() & (ft < fi)

    rows = [
        {"metrica": "registros_integrados", "valor": len(out)},
        {"metrica": "columnas_integradas", "valor": len(out.columns)},
        {"metrica": "periodo_min", "valor": int(pd.to_numeric(out["anio"], errors="coerce").min())},
        {"metrica": "periodo_max", "valor": int(pd.to_numeric(out["anio"], errors="coerce").max())},
        {"metrica": "estado_integracion_both", "valor": int((out["estado_integracion"] == "both").sum())},
        {"metrica": "estado_integracion_solo_tabular", "valor": int((out["estado_integracion"] == "solo_tabular").sum())},
        {"metrica": "estado_integracion_solo_shp", "valor": int((out["estado_integracion"] == "solo_shp").sum())},
        {"metrica": "clave_incendio_nula", "valor": int(out["clave_incendio"].isna().sum())},
        {"metrica": "duplicados_clave_incendio", "valor": int(out["clave_incendio"].duplicated(keep=False).fillna(False).sum())},
        {"metrica": "fecha_inicio_nula", "valor": int(out["fecha_inicio"].isna().sum())},
        {"metrica": "fecha_termino_nula", "valor": int(out["fecha_termino"].isna().sum())},
        {"metrica": "fechas_invertidas", "valor": int(fechas_invertidas.sum())},
        {"metrica": "latitud_nula", "valor": int(out["latitud"].isna().sum())},
        {"metrica": "longitud_nula", "valor": int(out["longitud"].isna().sum())},
        {"metrica": "cve_ent_nula", "valor": int(out["cve_ent"].isna().sum())},
        {"metrica": "cve_mun_nula", "valor": int(out["cve_mun"].isna().sum())},
        {"metrica": "clasificacion_match_consistente_alto", "valor": int((out["clasificacion_match"] == "match_consistente_alto").sum())},
        {"metrica": "clasificacion_match_consistente_medio", "valor": int((out["clasificacion_match"] == "match_consistente_medio").sum())},
        {"metrica": "clasificacion_match_debil", "valor": int((out["clasificacion_match"] == "match_debil").sum())},
        {"metrica": "clasificacion_match_conflictivo", "valor": int((out["clasificacion_match"] == "match_conflictivo").sum())},
        {"metrica": "clasificacion_match_solo_tabular", "valor": int((out["clasificacion_match"] == "solo_tabular").sum())},
        {"metrica": "clasificacion_match_solo_shp", "valor": int((out["clasificacion_match"] == "solo_shp").sum())},
    ]

    return pd.DataFrame(rows)


# ============================================================
# MAIN
# ============================================================

def main() -> None:
    print("CONAFOR | DP03 - Integración tabular + SHP 2015-2025")
    print("Leyendo match DP02...")

    if not PATH_MATCH.exists():
        raise FileNotFoundError(f"No existe el archivo de match: {PATH_MATCH}")

    df = pd.read_csv(PATH_MATCH, encoding="utf-8-sig", dtype=str)

    if "_merge" not in df.columns:
        raise ValueError("El archivo de match no contiene la columna '_merge'.")

    print(f"Registros en match DP02: {len(df):,}")

    rows: list[dict[str, Any]] = []

    print("Construyendo dataset integrado 2015-2025...")

    for _, row in df.iterrows():
        merge_value = row.get("_merge")

        if merge_value == "both":
            rows.append(build_row_both(row))
        elif merge_value == "left_only":
            rows.append(build_row_solo_tabular(row))
        elif merge_value == "right_only":
            rows.append(build_row_solo_shp(row))
        else:
            row_out = {col: pd.NA for col in FINAL_COLUMNS}
            row_out["estado_integracion"] = resolve_estado_integracion(merge_value)
            row_out["clave_incendio"] = choose_first_non_null(
                normalize_clave_incendio(row.get("tab_clave_incendio")),
                normalize_clave_incendio(row.get("shp_clave_incendio")),
            )
            row_out["clasificacion_match"] = safe_string(row.get("clasificacion_match"))
            rows.append(row_out)

    out = pd.DataFrame(rows)
    out = apply_final_schema(out)

    print("Construyendo resumen...")
    resumen = build_summary(out)

    print("Guardando salidas...")
    out.to_csv(OUT_INTEGRADO, index=False, encoding="utf-8-sig")
    resumen.to_csv(OUT_RESUMEN, index=False, encoding="utf-8-sig")

    print("\nProceso finalizado.")
    print(f"Dataset integrado: {OUT_INTEGRADO}")
    print(f"Resumen:           {OUT_RESUMEN}")

    print("\nResumen rápido:")
    print(out["estado_integracion"].value_counts(dropna=False))


if __name__ == "__main__":
    main()