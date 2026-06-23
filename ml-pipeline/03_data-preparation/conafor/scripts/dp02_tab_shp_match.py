# -*- coding: utf-8 -*-
"""
CONAFOR | DP02 - Match tabular <-> SHP puntos

Entrada
-------
1) Dataset tabular limpio 2015-2025:
   - conafor_tabular_2015_2025_limpio.csv

2) SHP histórico de puntos:
   - historico_incendios_activos_2001-2025.shp

Objetivo
--------
Validar la compatibilidad y el empate entre el dataset tabular consolidado
2015-2025 y el histórico geoespacial de incendios activos, usando:

- clave_incendio como llave principal;
- fechas, estado, municipio, predio, superficie y coordenadas como validadores.

Notas metodológicas
-------------------
- Este script sigue perteneciendo a Data Preparation porque integra fuentes CONAFOR de la misma familia de datos.
- Para coordenadas del SHP se privilegia geometry.x / geometry.y, no columnas x/y, porque en versiones previas se detectó inversión latitud/longitud.

Salidas
-------
- datasets/conafor_match_tabular_shp_2015_2025.csv
- reports/dp02_homologacion_tabular_shp.csv
- reports/dp02_resumen_match_tabular_shp.csv
"""

from __future__ import annotations

from pathlib import Path
from typing import Any
import re
import unicodedata

import numpy as np
import pandas as pd

try:
    import geopandas as gpd
except ImportError:
    gpd = None


# ============================================================
# CONFIGURACIÓN
# ============================================================

BASE_DIR = Path(r"C:\Users\Hp\OneDrive\Documentos\PT_Analisis")

PATH_TABULAR = (
    BASE_DIR
    / "03_data-preparation"
    / "conafor"
    / "datasets"
    / "conafor_tabular_2015_2025_limpio.csv"
)

PATH_SHP_PUNTOS = (
    BASE_DIR
    / "01_raw-data"
    / "conafor"
    / "historico_incendios_2001-2025"
    / "historico_incendios_activos_2001-2025.shp"
)

OUT_DIR = BASE_DIR / "03_data-preparation" / "conafor"
OUT_REPORTS = OUT_DIR / "reports"
OUT_DATASETS = OUT_DIR / "datasets"

OUT_REPORTS.mkdir(parents=True, exist_ok=True)
OUT_DATASETS.mkdir(parents=True, exist_ok=True)

OUT_HOMOLOGACION = OUT_REPORTS / "dp02_homologacion_tabular_shp.csv"
OUT_MATCH = OUT_DATASETS / "conafor_match_tabular_shp_2015_2025.csv"
OUT_RESUMEN = OUT_REPORTS / "dp02_resumen_match_tabular_shp.csv"


# ============================================================
# PARÁMETROS
# ============================================================

COORD_TOL_DEG = 0.01
SUP_HA_TOL = 0.5
ANIO_MIN = 2015
ANIO_MAX = 2025

MEX_BBOX = {
    "min_lon": -118.366667,
    "min_lat": 14.533334,
    "max_lon": -86.708334,
    "max_lat": 32.716667,
}


# ============================================================
# UTILIDADES GENERALES
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
        "df": "ciudad de mexico",
        "cdmx": "ciudad de mexico",
        "edo mexico": "mexico",
        "edo. mexico": "mexico",
        "estado de mexico": "mexico",
        "coahuila": "coahuila de zaragoza",
        "veracruz": "veracruz de ignacio de la llave",
        "michoacan": "michoacan de ocampo",
        "tlaxacala": "tlaxcala",
    }

    return replacements.get(s, s)


def to_numeric(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce")


def safe_string(series: pd.Series) -> pd.Series:
    s = series.astype("string").str.strip()
    s = s.replace({"": pd.NA, "nan": pd.NA, "NaN": pd.NA, "<NA>": pd.NA, "None": pd.NA})
    return s


def normalize_clave_incendio(series: pd.Series) -> pd.Series:
    s = safe_string(series)
    s = s.str.upper()
    s = s.str.replace(r"\s+", "", regex=True)
    return s


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


def compare_exact(a: pd.Series, b: pd.Series) -> pd.Series:
    return a.notna() & b.notna() & (a == b)


def compare_numeric_tol(a: pd.Series, b: pd.Series, tol: float) -> pd.Series:
    a_num = pd.to_numeric(a, errors="coerce")
    b_num = pd.to_numeric(b, errors="coerce")
    return a_num.notna() & b_num.notna() & ((a_num - b_num).abs() <= tol)


def coord_distance_deg(
    lat1: pd.Series,
    lon1: pd.Series,
    lat2: pd.Series,
    lon2: pd.Series,
) -> pd.Series:
    lat1 = pd.to_numeric(lat1, errors="coerce")
    lon1 = pd.to_numeric(lon1, errors="coerce")
    lat2 = pd.to_numeric(lat2, errors="coerce")
    lon2 = pd.to_numeric(lon2, errors="coerce")

    return np.sqrt((lat1 - lat2) ** 2 + (lon1 - lon2) ** 2)


def validate_bbox_mexico(lat: pd.Series, lon: pd.Series) -> pd.Series:
    return (
        lat.between(MEX_BBOX["min_lat"], MEX_BBOX["max_lat"], inclusive="both")
        & lon.between(MEX_BBOX["min_lon"], MEX_BBOX["max_lon"], inclusive="both")
    )


# ============================================================
# LECTURA TABULAR
# ============================================================

def read_tabular(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"No existe el tabular limpio: {path}")

    df = pd.read_csv(path, encoding="utf-8-sig", dtype=str)
    df.columns = [normalize_column_name(c) for c in df.columns]

    required = [
        "anio",
        "clave_incendio",
        "estado",
        "municipio",
        "predio",
        "latitud",
        "longitud",
        "fecha_inicio",
        "fecha_termino",
        "superficie_total_ha",
    ]

    for col in required:
        if col not in df.columns:
            df[col] = pd.NA

    df["anio"] = to_numeric(df["anio"])
    df["clave_incendio"] = normalize_clave_incendio(df["clave_incendio"])
    df["estado_norm"] = df["estado"].map(normalize_text_value)
    df["municipio_norm"] = df["municipio"].map(normalize_text_value)
    df["predio_norm"] = df["predio"].map(normalize_text_value)
    df["fecha_inicio"] = parse_date_iso(df["fecha_inicio"])
    df["fecha_termino"] = parse_date_iso(df["fecha_termino"])
    df["latitud"] = to_numeric(df["latitud"])
    df["longitud"] = to_numeric(df["longitud"])
    df["superficie_total_ha"] = to_numeric(df["superficie_total_ha"])

    df["coord_valida_mexico"] = validate_bbox_mexico(df["latitud"], df["longitud"])

    return df


# ============================================================
# LECTURA SHP PUNTOS
# ============================================================

def read_shp_points(path: Path) -> pd.DataFrame:
    if gpd is None:
        raise ImportError("No está disponible geopandas. Instálalo para leer el SHP.")

    if not path.exists():
        raise FileNotFoundError(f"No existe el SHP de puntos: {path}")

    gdf = gpd.read_file(path)
    gdf.columns = [normalize_column_name(c) for c in gdf.columns]

    rename_map = {
        "clave_ince": "clave_incendio",
        "f_inicio": "fecha_inicio",
        "f_fin": "fecha_termino",
        "predio_par": "predio",
        "sup_ha": "superficie_total_ha",
        "clvmun": "cve_mun",
        "clvent": "cve_ent",
    }

    gdf = gdf.rename(columns={k: v for k, v in rename_map.items() if k in gdf.columns})

    needed = [
        "clave_incendio",
        "estado",
        "municipio",
        "predio",
        "latitud",
        "longitud",
        "fecha_inicio",
        "fecha_termino",
        "superficie_total_ha",
        "cve_ent",
        "cve_mun",
    ]

    for col in needed:
        if col not in gdf.columns:
            gdf[col] = pd.NA

    # Fuente principal de coordenadas: geometría del SHP.
    # Esto evita la inversión de x/y detectada en versiones previas.
    if "geometry" in gdf.columns:
        gdf["longitud"] = gdf.geometry.x
        gdf["latitud"] = gdf.geometry.y
    else:
        # Respaldo solo si no existe geometry.
        if "x" in gdf.columns and "y" in gdf.columns:
            x_num = pd.to_numeric(gdf["x"], errors="coerce")
            y_num = pd.to_numeric(gdf["y"], errors="coerce")

            x_as_lon_score = x_num.between(MEX_BBOX["min_lon"], MEX_BBOX["max_lon"]).mean()
            y_as_lon_score = y_num.between(MEX_BBOX["min_lon"], MEX_BBOX["max_lon"]).mean()

            if x_as_lon_score >= y_as_lon_score:
                gdf["longitud"] = x_num
                gdf["latitud"] = y_num
            else:
                gdf["longitud"] = y_num
                gdf["latitud"] = x_num
        else:
            gdf["longitud"] = pd.NA
            gdf["latitud"] = pd.NA

    gdf["clave_incendio"] = normalize_clave_incendio(gdf["clave_incendio"])
    gdf["estado_norm"] = gdf["estado"].map(normalize_text_value)
    gdf["municipio_norm"] = gdf["municipio"].map(normalize_text_value)
    gdf["predio_norm"] = gdf["predio"].map(normalize_text_value)
    gdf["fecha_inicio"] = parse_date_iso(gdf["fecha_inicio"])
    gdf["fecha_termino"] = parse_date_iso(gdf["fecha_termino"])
    gdf["latitud"] = to_numeric(gdf["latitud"])
    gdf["longitud"] = to_numeric(gdf["longitud"])
    gdf["superficie_total_ha"] = to_numeric(gdf["superficie_total_ha"])

    gdf["coord_valida_mexico"] = validate_bbox_mexico(gdf["latitud"], gdf["longitud"])

    fi = pd.to_datetime(gdf["fecha_inicio"], errors="coerce")
    gdf["anio"] = fi.dt.year.astype("Int64")

    gdf["id_punto"] = np.arange(1, len(gdf) + 1)

    if "geometry" in gdf.columns:
        gdf = pd.DataFrame(gdf.drop(columns=["geometry"]))

    return gdf


# ============================================================
# MATRIZ DE HOMOLOGACIÓN
# ============================================================

def build_homologation_matrix() -> pd.DataFrame:
    rows = [
        ["anio", "derivado de fecha_inicio / f_inicio", "derivado", "fuerte", "sí"],
        ["clave_incendio", "clave_ince", "renombrar", "muy_fuerte", "sí"],
        ["estado", "estado", "directo", "fuerte", "sí"],
        ["municipio", "municipio", "directo", "fuerte", "sí"],
        ["predio", "predio_par", "renombrar", "medio", "sí"],
        ["latitud", "geometry.y", "derivado_geometria", "muy_fuerte", "sí"],
        ["longitud", "geometry.x", "derivado_geometria", "muy_fuerte", "sí"],
        ["fecha_inicio", "f_inicio", "renombrar", "muy_fuerte", "sí"],
        ["fecha_termino", "f_fin", "renombrar", "fuerte", "sí"],
        ["superficie_total_ha", "sup_ha", "renombrar", "medio", "sí"],
        ["cve_ent", "clvent", "renombrar", "medio", "parcial"],
        ["cve_mun", "clvmun", "renombrar", "medio", "parcial"],
    ]

    return pd.DataFrame(
        rows,
        columns=[
            "campo_tabular",
            "campo_shp_puntos",
            "tipo_equivalencia",
            "fuerza_para_matching",
            "usable",
        ],
    )


# ============================================================
# VALIDACIÓN DE CARDINALIDAD
# ============================================================

def build_uniqueness_stats(df: pd.DataFrame, key_col: str, prefix: str) -> list[dict[str, Any]]:
    key = safe_string(df[key_col])

    n_total = len(df)
    n_nulos = int(key.isna().sum())
    n_no_nulos = int(key.notna().sum())
    n_unicos = int(key.nunique(dropna=True))
    dup_mask = key.duplicated(keep=False) & key.notna()
    n_duplicados = int(dup_mask.sum())

    return [
        {"metrica": f"{prefix}_registros", "valor": n_total},
        {"metrica": f"{prefix}_clave_nula", "valor": n_nulos},
        {"metrica": f"{prefix}_clave_no_nula", "valor": n_no_nulos},
        {"metrica": f"{prefix}_clave_unica_distinta", "valor": n_unicos},
        {"metrica": f"{prefix}_registros_clave_duplicada", "valor": n_duplicados},
    ]


def validate_merge_readiness(df: pd.DataFrame, key_col: str, dataset_name: str) -> None:
    key = safe_string(df[key_col])
    dup_mask = key.duplicated(keep=False) & key.notna()
    n_dups = int(dup_mask.sum())

    if n_dups > 0:
        raise ValueError(
            f"El dataset {dataset_name} tiene {n_dups} registros con clave duplicada en '{key_col}'. "
            "Resuelve la cardinalidad antes de hacer un merge 1:1 por clave."
        )


# ============================================================
# MATCH Y CONSISTENCIA
# ============================================================

def build_match(tab: pd.DataFrame, shp: pd.DataFrame) -> pd.DataFrame:
    tab = tab.copy()
    shp = shp.copy()

    tab["id_tabular"] = np.arange(1, len(tab) + 1)

    validate_merge_readiness(tab, "clave_incendio", "tabular")
    validate_merge_readiness(shp, "clave_incendio", "shp_puntos_comparable")

    tab_pref = tab.add_prefix("tab_")
    shp_pref = shp.add_prefix("shp_")

    merged = tab_pref.merge(
        shp_pref,
        left_on="tab_clave_incendio",
        right_on="shp_clave_incendio",
        how="outer",
        indicator=True,
        validate="1:1",
    )

    merged["match_por_clave"] = merged["_merge"].eq("both")

    merged["cons_fecha_inicio"] = compare_exact(
        merged["tab_fecha_inicio"],
        merged["shp_fecha_inicio"],
    )

    merged["cons_fecha_termino"] = compare_exact(
        merged["tab_fecha_termino"],
        merged["shp_fecha_termino"],
    )

    merged["cons_estado"] = compare_exact(
        merged["tab_estado_norm"],
        merged["shp_estado_norm"],
    )

    merged["cons_municipio"] = compare_exact(
        merged["tab_municipio_norm"],
        merged["shp_municipio_norm"],
    )

    merged["cons_predio"] = compare_exact(
        merged["tab_predio_norm"],
        merged["shp_predio_norm"],
    )

    merged["cons_superficie"] = compare_numeric_tol(
        merged["tab_superficie_total_ha"],
        merged["shp_superficie_total_ha"],
        SUP_HA_TOL,
    )

    merged["coord_dist_deg"] = coord_distance_deg(
        merged["tab_latitud"],
        merged["tab_longitud"],
        merged["shp_latitud"],
        merged["shp_longitud"],
    )

    merged["cons_coordenadas"] = (
        merged["coord_dist_deg"].notna()
        & (merged["coord_dist_deg"] <= COORD_TOL_DEG)
    )

    score_cols = [
        "cons_fecha_inicio",
        "cons_fecha_termino",
        "cons_estado",
        "cons_municipio",
        "cons_predio",
        "cons_superficie",
        "cons_coordenadas",
    ]

    merged["score_consistencia"] = merged[score_cols].fillna(False).sum(axis=1)

    def classify_row(row: pd.Series) -> str:
        if row["_merge"] == "left_only":
            return "solo_tabular"

        if row["_merge"] == "right_only":
            return "solo_shp"

        score = row["score_consistencia"]

        if score >= 5:
            return "match_consistente_alto"

        if score >= 3:
            return "match_consistente_medio"

        if score >= 1:
            return "match_debil"

        return "match_conflictivo"

    merged["clasificacion_match"] = merged.apply(classify_row, axis=1)

    return merged


# ============================================================
# RESUMEN
# ============================================================

def build_summary(match_df: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []

    both = match_df["_merge"].eq("both")
    left_only = match_df["_merge"].eq("left_only")
    right_only = match_df["_merge"].eq("right_only")

    rows.extend([
        {"metrica": "registros_match_total", "valor": len(match_df)},
        {"metrica": "solo_tabular", "valor": int(left_only.sum())},
        {"metrica": "solo_shp", "valor": int(right_only.sum())},
        {"metrica": "match_en_ambos", "valor": int(both.sum())},

        {"metrica": "match_consistente_alto", "valor": int((match_df["clasificacion_match"] == "match_consistente_alto").sum())},
        {"metrica": "match_consistente_medio", "valor": int((match_df["clasificacion_match"] == "match_consistente_medio").sum())},
        {"metrica": "match_debil", "valor": int((match_df["clasificacion_match"] == "match_debil").sum())},
        {"metrica": "match_conflictivo", "valor": int((match_df["clasificacion_match"] == "match_conflictivo").sum())},

        {"metrica": "fecha_inicio_consistente", "valor": int(match_df["cons_fecha_inicio"].fillna(False).sum())},
        {"metrica": "fecha_termino_consistente", "valor": int(match_df["cons_fecha_termino"].fillna(False).sum())},
        {"metrica": "estado_consistente", "valor": int(match_df["cons_estado"].fillna(False).sum())},
        {"metrica": "municipio_consistente", "valor": int(match_df["cons_municipio"].fillna(False).sum())},
        {"metrica": "predio_consistente", "valor": int(match_df["cons_predio"].fillna(False).sum())},
        {"metrica": "superficie_consistente", "valor": int(match_df["cons_superficie"].fillna(False).sum())},
        {"metrica": "coordenadas_consistentes", "valor": int(match_df["cons_coordenadas"].fillna(False).sum())},

        {"metrica": "both_coordenadas_consistentes", "valor": int((both & match_df["cons_coordenadas"].fillna(False)).sum())},
        {"metrica": "both_coordenadas_no_consistentes", "valor": int((both & ~match_df["cons_coordenadas"].fillna(False)).sum())},
        {"metrica": "coordenadas_no_comparables", "valor": int(match_df["coord_dist_deg"].isna().sum())},
    ])

    coord_vals = pd.to_numeric(match_df["coord_dist_deg"], errors="coerce")
    score_vals = pd.to_numeric(match_df["score_consistencia"], errors="coerce")

    rows.extend([
        {"metrica": "coord_dist_deg_media", "valor": float(coord_vals.mean()) if coord_vals.notna().any() else np.nan},
        {"metrica": "coord_dist_deg_mediana", "valor": float(coord_vals.median()) if coord_vals.notna().any() else np.nan},
        {"metrica": "score_consistencia_medio", "valor": float(score_vals.mean()) if score_vals.notna().any() else np.nan},
        {"metrica": "score_consistencia_min", "valor": float(score_vals.min()) if score_vals.notna().any() else np.nan},
        {"metrica": "score_consistencia_max", "valor": float(score_vals.max()) if score_vals.notna().any() else np.nan},
    ])

    return pd.DataFrame(rows)


# ============================================================
# MAIN
# ============================================================

def main() -> None:
    print("CONAFOR | DP02 - Match tabular ↔ SHP puntos")
    print("Leyendo datasets...")

    tab = read_tabular(PATH_TABULAR)
    shp = read_shp_points(PATH_SHP_PUNTOS)

    print(f"Tabular limpio 2015-2025: {len(tab):,}")
    print(f"SHP puntos original:       {len(shp):,}")

    shp_comp = shp[shp["anio"].between(ANIO_MIN, ANIO_MAX, inclusive="both")].copy()

    print(f"SHP puntos comparable {ANIO_MIN}-{ANIO_MAX}: {len(shp_comp):,}")

    print("Construyendo homologación tabular-SHP...")
    homologacion = build_homologation_matrix()

    print("Validando cardinalidad de clave...")
    stats: list[dict[str, Any]] = []
    stats.extend(build_uniqueness_stats(tab, "clave_incendio", "tabular"))
    stats.extend(build_uniqueness_stats(shp, "clave_incendio", "shp_puntos_total"))
    stats.extend(build_uniqueness_stats(shp_comp, "clave_incendio", "shp_puntos_comparable"))

    fuera_periodo = (~shp["anio"].between(ANIO_MIN, ANIO_MAX, inclusive="both")).fillna(True).sum()
    stats.append({
        "metrica": f"shp_puntos_fuera_periodo_{ANIO_MIN}_{ANIO_MAX}",
        "valor": int(fuera_periodo),
    })

    print("Realizando match por clave_incendio...")
    match_df = build_match(tab, shp_comp)

    print("Construyendo resumen de match...")
    resumen_match = build_summary(match_df)
    resumen = pd.concat([pd.DataFrame(stats), resumen_match], ignore_index=True)

    print("Guardando salidas...")
    homologacion.to_csv(OUT_HOMOLOGACION, index=False, encoding="utf-8-sig")
    match_df.to_csv(OUT_MATCH, index=False, encoding="utf-8-sig")
    resumen.to_csv(OUT_RESUMEN, index=False, encoding="utf-8-sig")

    print("\nProceso finalizado.")
    print(f"Homologación: {OUT_HOMOLOGACION}")
    print(f"Match:        {OUT_MATCH}")
    print(f"Resumen:      {OUT_RESUMEN}")


if __name__ == "__main__":
    main()