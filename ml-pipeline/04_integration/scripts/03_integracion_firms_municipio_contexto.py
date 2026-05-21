# -*- coding: utf-8 -*-
"""
Integration 03 | FIRMS contexto municipal y agregación municipio-día

Este script integra el dataset limpio de NASA FIRMS con el catálogo municipal
de INEGI para construir una versión contextualizada de detecciones satelitales
y una agregación diaria municipal.

Salidas
-------
1) 04_integration/datasets/integracion_firms_puntos_contexto.csv
2) 04_integration/datasets/integracion_firms_municipio_dia.csv
3) 04_integration/reports/integracion_03_validacion_firms_contexto.csv

Objetivo
--------
- Asignar cvegeo municipal a cada punto FIRMS mediante join espacial.
- Agregar detecciones FIRMS por cvegeo + fecha.
- Mantener trazabilidad de la asignación municipal.
- Procesar por chunks para evitar uso excesivo de memoria.

Notas metodológicas
-------------------
FIRMS representa detecciones satelitales/puntos de calor, no incendios
confirmados. Por ello, la agregación municipio-día no debe interpretarse como
conteo de incendios, sino como conteo de detecciones.
"""

from __future__ import annotations

from pathlib import Path
import unicodedata
import pandas as pd
import geopandas as gpd


# =========================================================
# 1) CONFIGURACIÓN
# =========================================================

BASE_DIR = Path(r"C:\Users\Hp\OneDrive\Documentos\PT_Analisis")

PATH_FIRMS = (
    BASE_DIR
    / "03_data-preparation"
    / "firms"
    / "datasets"
    / "firms_archive_2001_2025_limpio.csv"
)

PATH_INEGI_GPKG = (
    BASE_DIR
    / "03_data-preparation"
    / "inegi"
    / "datasets"
    / "inegi_capas_limpias.gpkg"
)

PATH_CATALOGO_MUNICIPIOS = (
    BASE_DIR
    / "04_integration"
    / "datasets"
    / "integracion_catalogo_municipios.csv"
)

OUT_DATASETS_DIR = BASE_DIR / "04_integration" / "datasets"
OUT_REPORTS_DIR = BASE_DIR / "04_integration" / "reports"

OUT_DATASETS_DIR.mkdir(parents=True, exist_ok=True)
OUT_REPORTS_DIR.mkdir(parents=True, exist_ok=True)

OUT_PUNTOS_CONTEXTO = OUT_DATASETS_DIR / "integracion_firms_puntos_contexto.csv"
OUT_MUNICIPIO_DIA = OUT_DATASETS_DIR / "integracion_firms_municipio_dia.csv"
OUT_VALIDACION = OUT_REPORTS_DIR / "integracion_03_validacion_firms_contexto.csv"

LAYER_MUNICIPIOS = "municipios_limpio"

PROJECT_START = "2001-01-01"
PROJECT_END = "2025-12-31"

CHUNK_SIZE = 250_000

# Fuente: INEGI, Marco Geoestadístico Nacional 2025.
# Calculado con get_mexico_bbox.py a partir de 00ent.shp.
# CRS: WGS84 / EPSG:4326.
MEXICO_BBOX = {
    "lat_min": 14.532098,
    "lat_max": 32.718649,
    "lon_min": -118.365251,
    "lon_max": -86.710401,
}


# =========================================================
# 2) UTILIDADES
# =========================================================

def normalize_for_detection(value: str) -> str:
    s = str(value).strip().lower()
    s = unicodedata.normalize("NFKD", s)
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    s = s.replace(" ", "").replace("_", "").replace("-", "")
    return s


def detect_column(df: pd.DataFrame, candidates: list[str], label: str, required: bool = True) -> str | None:
    normalized_cols = {
        normalize_for_detection(col): col
        for col in df.columns
    }

    for candidate in candidates:
        key = normalize_for_detection(candidate)
        if key in normalized_cols:
            return normalized_cols[key]

    if required:
        raise ValueError(
            f"No se pudo detectar la columna requerida para '{label}'. "
            f"Columnas disponibles: {list(df.columns)}"
        )

    return None


def normalize_text(value) -> str:
    if pd.isna(value):
        return ""
    s = str(value).strip()
    s = " ".join(s.split())
    return s


def normalize_code(series: pd.Series, width: int) -> pd.Series:
    s = series.astype(str).str.strip()
    s = s.str.replace(r"\.0$", "", regex=True)
    extracted = s.str.extract(r"(\d+)", expand=False)
    return extracted.where(extracted.notna(), pd.NA).str.zfill(width)


def normalize_cvegeo(series: pd.Series) -> pd.Series:
    return normalize_code(series, 5)


def normalize_cve_ent(series: pd.Series) -> pd.Series:
    return normalize_code(series, 2)


def normalize_cve_mun(series: pd.Series) -> pd.Series:
    return normalize_code(series, 3)


def clean_numeric(series: pd.Series) -> pd.Series:
    s = series.astype(str).str.strip()
    s = s.str.replace(",", ".", regex=False)
    s = s.str.replace(r"[^\d\.\-]", "", regex=True)
    return pd.to_numeric(s, errors="coerce")


def build_report_row(indicador: str, valor, estatus: str, observacion: str) -> dict:
    return {
        "indicador": indicador,
        "valor": valor,
        "estatus": estatus,
        "observacion": observacion,
    }


def coordenada_en_bbox_mexico(lat: pd.Series, lon: pd.Series) -> pd.Series:
    """
    Valida si las coordenadas caen dentro del BBOX nacional calculado
    a partir del Marco Geoestadístico Nacional 2025 de INEGI.

    Esta validación solo funciona como filtro previo. La asignación municipal
    real se realiza mediante join espacial contra polígonos municipales.
    """
    return (
        lat.between(MEXICO_BBOX["lat_min"], MEXICO_BBOX["lat_max"])
        & lon.between(MEXICO_BBOX["lon_min"], MEXICO_BBOX["lon_max"])
    )

# =========================================================
# 3) CARGA DE INSUMOS
# =========================================================

def load_catalogo_municipios() -> pd.DataFrame:
    if not PATH_CATALOGO_MUNICIPIOS.exists():
        raise FileNotFoundError(
            f"No existe el catálogo municipal. Ejecuta primero 01_build_geo_catalogs.py: "
            f"{PATH_CATALOGO_MUNICIPIOS}"
        )

    cat = pd.read_csv(PATH_CATALOGO_MUNICIPIOS, encoding="utf-8-sig", dtype=str)

    required = {"cve_ent", "nom_ent", "cve_mun", "nom_mun", "cvegeo"}
    missing = required - set(cat.columns)
    if missing:
        raise ValueError(f"El catálogo municipal no contiene columnas requeridas. Faltan: {missing}")

    cat["cve_ent"] = normalize_cve_ent(cat["cve_ent"])
    cat["cve_mun"] = normalize_cve_mun(cat["cve_mun"])
    cat["cvegeo"] = normalize_cvegeo(cat["cvegeo"])
    cat["nom_ent"] = cat["nom_ent"].map(normalize_text)
    cat["nom_mun"] = cat["nom_mun"].map(normalize_text)

    if cat["cvegeo"].duplicated().any():
        raise ValueError("El catálogo municipal contiene cvegeo duplicadas.")

    return cat


def load_municipios_geometry() -> gpd.GeoDataFrame:
    if not PATH_INEGI_GPKG.exists():
        raise FileNotFoundError(f"No existe GeoPackage INEGI limpio: {PATH_INEGI_GPKG}")

    municipios = gpd.read_file(PATH_INEGI_GPKG, layer=LAYER_MUNICIPIOS)

    if municipios.crs is None:
        raise ValueError("La capa municipios_limpio no tiene CRS definido.")

    cvegeo_col = detect_column(
        municipios,
        ["cvegeo", "clavegeo", "clave_geografica"],
        "cvegeo municipal"
    )

    municipios["cvegeo_spatial"] = normalize_cvegeo(municipios[cvegeo_col])

    municipios = municipios[["cvegeo_spatial", "geometry"]].copy()
    municipios = municipios[municipios.geometry.notna()].copy()
    municipios = municipios[~municipios.geometry.is_empty].copy()

    if municipios["cvegeo_spatial"].duplicated().any():
        raise ValueError("La geometría municipal tiene cvegeo_spatial duplicadas.")

    return municipios


def validate_input_exists() -> None:
    if not PATH_FIRMS.exists():
        raise FileNotFoundError(f"No existe el dataset FIRMS limpio: {PATH_FIRMS}")


# =========================================================
# 4) PROCESAMIENTO POR CHUNKS
# =========================================================

def prepare_firms_chunk(chunk: pd.DataFrame) -> pd.DataFrame:
    lat_col = detect_column(chunk, ["latitude", "latitud", "lat"], "latitud")
    lon_col = detect_column(chunk, ["longitude", "longitud", "lon", "lng"], "longitud")
    fecha_col = detect_column(chunk, ["acq_date", "fecha", "date"], "fecha de adquisición")

    chunk = chunk.copy()

    chunk["latitude_int"] = clean_numeric(chunk[lat_col])
    chunk["longitude_int"] = clean_numeric(chunk[lon_col])
    chunk["fecha"] = pd.to_datetime(chunk[fecha_col], errors="coerce").dt.date

    chunk["coordenada_valida"] = coordenada_en_bbox_mexico(
        chunk["latitude_int"],
        chunk["longitude_int"]
    )

    return chunk


def spatial_join_firms_chunk(
    chunk: pd.DataFrame,
    municipios_geom: gpd.GeoDataFrame
) -> pd.DataFrame:
    valid_coords = chunk[chunk["coordenada_valida"]].copy()
    invalid_coords = chunk[~chunk["coordenada_valida"]].copy()

    if valid_coords.empty:
        chunk["cvegeo_spatial"] = pd.NA
        chunk["asignacion_municipio_metodo"] = "sin_asignacion"
        return chunk

    gdf = gpd.GeoDataFrame(
        valid_coords,
        geometry=gpd.points_from_xy(valid_coords["longitude_int"], valid_coords["latitude_int"]),
        crs="EPSG:4326"
    )

    if gdf.crs != municipios_geom.crs:
        gdf = gdf.to_crs(municipios_geom.crs)

    joined = gpd.sjoin(
        gdf,
        municipios_geom,
        how="left",
        predicate="within"
    ).drop(columns=["index_right", "geometry"], errors="ignore")

    joined["asignacion_municipio_metodo"] = "spatial_join"
    joined.loc[joined["cvegeo_spatial"].isna(), "asignacion_municipio_metodo"] = "sin_asignacion"

    if not invalid_coords.empty:
        invalid_coords["cvegeo_spatial"] = pd.NA
        invalid_coords["asignacion_municipio_metodo"] = "coordenada_invalida"
        output = pd.concat([joined, invalid_coords], ignore_index=True)
    else:
        output = joined.copy()

    return pd.DataFrame(output)


def attach_catalogo_municipal(chunk: pd.DataFrame, catalogo: pd.DataFrame) -> pd.DataFrame:
    chunk = chunk.copy()
    chunk["cvegeo"] = normalize_cvegeo(chunk["cvegeo_spatial"])

    cat_merge = catalogo[["cvegeo", "cve_ent", "nom_ent", "cve_mun", "nom_mun"]].copy()

    chunk = chunk.merge(
        cat_merge,
        on="cvegeo",
        how="left"
    )

    return chunk


def add_numeric_fields(chunk: pd.DataFrame) -> pd.DataFrame:
    chunk = chunk.copy()

    for col in ["frp", "brightness", "bright_t31", "confidence"]:
        if col in chunk.columns:
            chunk[f"{col}_num"] = clean_numeric(chunk[col])
        else:
            chunk[f"{col}_num"] = pd.NA

    if "daynight" in chunk.columns:
        daynight = chunk["daynight"].astype(str).str.upper().str.strip()
        chunk["firms_day_flag"] = (daynight == "D").astype(int)
        chunk["firms_night_flag"] = (daynight == "N").astype(int)
    else:
        chunk["firms_day_flag"] = 0
        chunk["firms_night_flag"] = 0

    return chunk


def build_chunk_aggregation(chunk: pd.DataFrame) -> pd.DataFrame:
    base = chunk.dropna(subset=["cvegeo", "fecha"]).copy()

    if base.empty:
        return pd.DataFrame()

    grouped = (
        base.groupby(["cve_ent", "nom_ent", "cve_mun", "nom_mun", "cvegeo", "fecha"], as_index=False)
        .agg(
            firms_count=("fecha", "size"),
            firms_frp_sum=("frp_num", "sum"),
            firms_frp_valid_count=("frp_num", "count"),
            firms_brightness_sum=("brightness_num", "sum"),
            firms_brightness_valid_count=("brightness_num", "count"),
            firms_bright_t31_sum=("bright_t31_num", "sum"),
            firms_bright_t31_valid_count=("bright_t31_num", "count"),
            firms_confidence_sum=("confidence_num", "sum"),
            firms_confidence_valid_count=("confidence_num", "count"),
            firms_day_count=("firms_day_flag", "sum"),
            firms_night_count=("firms_night_flag", "sum"),
        )
    )

    return grouped


def finalize_municipio_dia(partials: list[pd.DataFrame]) -> pd.DataFrame:
    if not partials:
        return pd.DataFrame()

    combined = pd.concat(partials, ignore_index=True)

    grouped = (
        combined.groupby(["cve_ent", "nom_ent", "cve_mun", "nom_mun", "cvegeo", "fecha"], as_index=False)
        .agg(
            firms_count=("firms_count", "sum"),
            firms_frp_sum=("firms_frp_sum", "sum"),
            firms_frp_valid_count=("firms_frp_valid_count", "sum"),
            firms_brightness_sum=("firms_brightness_sum", "sum"),
            firms_brightness_valid_count=("firms_brightness_valid_count", "sum"),
            firms_bright_t31_sum=("firms_bright_t31_sum", "sum"),
            firms_bright_t31_valid_count=("firms_bright_t31_valid_count", "sum"),
            firms_confidence_sum=("firms_confidence_sum", "sum"),
            firms_confidence_valid_count=("firms_confidence_valid_count", "sum"),
            firms_day_count=("firms_day_count", "sum"),
            firms_night_count=("firms_night_count", "sum"),
        )
    )

    grouped["firms_frp_mean"] = grouped["firms_frp_sum"] / grouped["firms_frp_valid_count"].replace(0, pd.NA)
    grouped["firms_brightness_mean"] = grouped["firms_brightness_sum"] / grouped["firms_brightness_valid_count"].replace(0, pd.NA)
    grouped["firms_bright_t31_mean"] = grouped["firms_bright_t31_sum"] / grouped["firms_bright_t31_valid_count"].replace(0, pd.NA)
    grouped["firms_confidence_mean"] = grouped["firms_confidence_sum"] / grouped["firms_confidence_valid_count"].replace(0, pd.NA)

    grouped["has_firms"] = 1

    ordered_cols = [
        "cve_ent",
        "nom_ent",
        "cve_mun",
        "nom_mun",
        "cvegeo",
        "fecha",
        "firms_count",
        "firms_frp_sum",
        "firms_frp_mean",
        "firms_brightness_mean",
        "firms_bright_t31_mean",
        "firms_confidence_mean",
        "firms_day_count",
        "firms_night_count",
        "has_firms",
        "firms_frp_valid_count",
        "firms_brightness_valid_count",
        "firms_bright_t31_valid_count",
        "firms_confidence_valid_count",
    ]

    grouped = grouped[ordered_cols].copy()
    grouped = grouped.sort_values(["fecha", "cvegeo"]).reset_index(drop=True)

    return grouped


def select_context_output_columns(chunk: pd.DataFrame, original_cols: list[str]) -> pd.DataFrame:
    extra_cols = [
        "fecha",
        "latitude_int",
        "longitude_int",
        "coordenada_valida",
        "cvegeo",
        "cve_ent",
        "nom_ent",
        "cve_mun",
        "nom_mun",
        "asignacion_municipio_metodo",
    ]

    cols = []
    for col in original_cols + extra_cols:
        if col in chunk.columns and col not in cols:
            cols.append(col)

    return chunk[cols].copy()


# =========================================================
# 5) VALIDACIÓN
# =========================================================

def build_validation_report(stats: dict, municipio_dia: pd.DataFrame) -> pd.DataFrame:
    rows = []

    total = stats["total_leidos"]
    fecha_nula = stats["fecha_nula"]
    coords_invalidas = stats["coords_invalidas"]
    cvegeo_nula = stats["cvegeo_nula"]
    sin_catalogo = stats["sin_catalogo"]
    fuera_periodo = stats["fuera_periodo"]

    dup_mun_dia = 0
    if not municipio_dia.empty:
        dup_mun_dia = int(municipio_dia.duplicated(subset=["cvegeo", "fecha"]).sum())

    rows.append(build_report_row(
        "firms_registros_leidos",
        total,
        "ok" if total > 0 else "error",
        "Total de registros FIRMS leídos desde DP."
    ))

    rows.append(build_report_row(
        "fecha_min",
        stats["fecha_min"],
        "ok",
        "Fecha mínima detectada en FIRMS."
    ))

    rows.append(build_report_row(
        "fecha_max",
        stats["fecha_max"],
        "ok",
        "Fecha máxima detectada en FIRMS."
    ))

    rows.append(build_report_row(
        "firms_fecha_nula",
        fecha_nula,
        "ok" if fecha_nula == 0 else "warning",
        "Registros FIRMS sin fecha válida."
    ))

    rows.append(build_report_row(
        "firms_coordenada_invalida",
        coords_invalidas,
        "ok" if coords_invalidas == 0 else "warning",
        "Registros FIRMS sin coordenadas válidas para México."
    ))

    rows.append(build_report_row(
        "firms_cvegeo_nula",
        cvegeo_nula,
        "ok" if cvegeo_nula == 0 else "warning",
        "Registros FIRMS sin municipio asignado por join espacial."
    ))

    rows.append(build_report_row(
        "firms_sin_catalogo_municipal",
        sin_catalogo,
        "ok" if sin_catalogo == 0 else "warning",
        "Registros cuyo cvegeo no encontró correspondencia en catálogo municipal."
    ))

    rows.append(build_report_row(
        "firms_fuera_periodo_proyecto_2001_2025",
        fuera_periodo,
        "ok" if fuera_periodo == 0 else "warning",
        "Registros FIRMS fuera del periodo general del proyecto."
    ))

    rows.append(build_report_row(
        "municipio_dia_registros",
        len(municipio_dia),
        "ok" if len(municipio_dia) > 0 else "error",
        "Registros generados en integration_firms_municipio_dia.csv."
    ))

    rows.append(build_report_row(
        "municipio_dia_duplicados_cvegeo_fecha",
        dup_mun_dia,
        "ok" if dup_mun_dia == 0 else "error",
        "Duplicados por clave cvegeo + fecha en agregación municipio-día."
    ))

    return pd.DataFrame(rows)


# =========================================================
# 6) PIPELINE PRINCIPAL
# =========================================================

def main() -> None:
    print("\nIntegration 03 | FIRMS contexto municipal y municipio-día")

    validate_input_exists()

    catalogo_municipios = load_catalogo_municipios()
    municipios_geom = load_municipios_geometry()

    print(f"Dataset FIRMS: {PATH_FIRMS}")
    print(f"Municipios geometría: {len(municipios_geom):,}")
    print(f"Catálogo municipal: {len(catalogo_municipios):,}")
    print(f"Chunk size: {CHUNK_SIZE:,}")

    partial_aggs: list[pd.DataFrame] = []

    stats = {
        "total_leidos": 0,
        "fecha_nula": 0,
        "coords_invalidas": 0,
        "cvegeo_nula": 0,
        "sin_catalogo": 0,
        "fuera_periodo": 0,
        "fecha_min": None,
        "fecha_max": None,
    }

    first_write = True
    original_cols: list[str] | None = None

    reader = pd.read_csv(
        PATH_FIRMS,
        encoding="utf-8-sig",
        low_memory=False,
        chunksize=CHUNK_SIZE
    )

    for i, chunk in enumerate(reader, start=1):
        print(f"\nProcesando chunk {i}... registros: {len(chunk):,}")

        if original_cols is None:
            original_cols = list(chunk.columns)

        stats["total_leidos"] += len(chunk)

        chunk = prepare_firms_chunk(chunk)
        chunk = spatial_join_firms_chunk(chunk, municipios_geom)
        chunk = attach_catalogo_municipal(chunk, catalogo_municipios)
        chunk = add_numeric_fields(chunk)

        stats["fecha_nula"] += int(chunk["fecha"].isna().sum())
        stats["coords_invalidas"] += int((~chunk["coordenada_valida"]).sum())
        stats["cvegeo_nula"] += int(chunk["cvegeo"].isna().sum())
        stats["sin_catalogo"] += int(chunk["cvegeo"].notna().sum() - chunk["nom_mun"].notna().sum())

        fecha_series = pd.to_datetime(chunk["fecha"], errors="coerce")

        if fecha_series.notna().any():
            chunk_min = fecha_series.min().date()
            chunk_max = fecha_series.max().date()

            if stats["fecha_min"] is None or chunk_min < stats["fecha_min"]:
                stats["fecha_min"] = chunk_min

            if stats["fecha_max"] is None or chunk_max > stats["fecha_max"]:
                stats["fecha_max"] = chunk_max

        stats["fuera_periodo"] += int(
            (
                (fecha_series < pd.to_datetime(PROJECT_START))
                | (fecha_series > pd.to_datetime(PROJECT_END))
            ).sum()
        )

        chunk_agg = build_chunk_aggregation(chunk)
        if not chunk_agg.empty:
            partial_aggs.append(chunk_agg)

        context_out = select_context_output_columns(chunk, original_cols)
        context_out.to_csv(
            OUT_PUNTOS_CONTEXTO,
            index=False,
            encoding="utf-8-sig",
            mode="w" if first_write else "a",
            header=first_write
        )

        first_write = False

        print(f"  Acumulado leído: {stats['total_leidos']:,}")
        print(f"  Sin municipio asignado acumulado: {stats['cvegeo_nula']:,}")

    print("\nConsolidando agregación municipio-día...")
    municipio_dia = finalize_municipio_dia(partial_aggs)

    validacion = build_validation_report(stats, municipio_dia)

    municipio_dia.to_csv(OUT_MUNICIPIO_DIA, index=False, encoding="utf-8-sig")
    validacion.to_csv(OUT_VALIDACION, index=False, encoding="utf-8-sig")

    errores = validacion[validacion["estatus"] == "error"]
    if not errores.empty:
        print("\nErrores de validación:")
        print(errores.to_string(index=False))
        raise ValueError("La integración FIRMS terminó con errores. Revisa el reporte.")

    print("\nArchivos generados:")
    print(f"- {OUT_PUNTOS_CONTEXTO}")
    print(f"- {OUT_MUNICIPIO_DIA}")
    print(f"- {OUT_VALIDACION}")

    print("\nResumen:")
    print(f"- Registros FIRMS leídos: {stats['total_leidos']:,}")
    print(f"- Registros FIRMS municipio-día: {len(municipio_dia):,}")
    print(f"- Sin municipio asignado: {stats['cvegeo_nula']:,}")
    print(f"- Warnings: {(validacion['estatus'] == 'warning').sum()}")
    print(f"- Errores: {(validacion['estatus'] == 'error').sum()}")

    print("\nProceso terminado.")


if __name__ == "__main__":
    main()