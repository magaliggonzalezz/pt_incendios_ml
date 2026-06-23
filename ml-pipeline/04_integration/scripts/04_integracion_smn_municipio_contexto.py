# -*- coding: utf-8 -*-
"""
Integración 04 | SMN contexto municipal y agregación municipio-día

Este script integra el dataset limpio diario de SMN/CONAGUA con el catálogo
municipal de INEGI para construir una versión contextualizada de estaciones
meteorológicas y una agregación diaria municipal.

Salidas
-------
1) 04_integration/datasets/integracion_smn_estaciones_contexto.csv
2) 04_integration/datasets/integracion_smn_municipio_dia.csv
3) 04_integration/reports/integracion_04_validacion_smn_contexto.csv

Objetivo
--------
- Construir un catálogo único de estaciones SMN.
- Asignar cvegeo municipal a cada estación mediante join espacial.
- Procesar observaciones diarias por chunks.
- Agregar variables meteorológicas por cvegeo + fecha.
- Mantener trazabilidad de estaciones y cobertura municipal.
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

PATH_SMN = (
    BASE_DIR
    / "03_data-preparation"
    / "smn"
    / "datasets"
    / "smn_dp01_diario_limpio_2001_2025.csv"
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

OUT_ESTACIONES_CONTEXTO = OUT_DATASETS_DIR / "integracion_smn_estaciones_contexto.csv"
OUT_MUNICIPIO_DIA = OUT_DATASETS_DIR / "integracion_smn_municipio_dia.csv"
OUT_VALIDACION = OUT_REPORTS_DIR / "integracion_04_validacion_smn_contexto.csv"

LAYER_MUNICIPIOS = "municipios_limpio"

PROJECT_START = "2001-01-01"
PROJECT_END = "2025-12-31"

CHUNK_SIZE = 500_000

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


def detect_column(
    df: pd.DataFrame,
    candidates: list[str],
    label: str,
    required: bool = True
) -> str | None:
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


def build_report_row(indicador: str, valor, estatus: str, observacion: str) -> dict:
    return {
        "indicador": indicador,
        "valor": valor,
        "estatus": estatus,
        "observacion": observacion,
    }


# =========================================================
# 3) CARGA DE INSUMOS
# =========================================================

def validate_input_exists() -> None:
    if not PATH_SMN.exists():
        raise FileNotFoundError(f"No existe el dataset SMN limpio: {PATH_SMN}")

    if not PATH_INEGI_GPKG.exists():
        raise FileNotFoundError(f"No existe GeoPackage INEGI limpio: {PATH_INEGI_GPKG}")

    if not PATH_CATALOGO_MUNICIPIOS.exists():
        raise FileNotFoundError(
            f"No existe catálogo municipal. Ejecuta primero el script 01: "
            f"{PATH_CATALOGO_MUNICIPIOS}"
        )


def load_catalogo_municipios() -> pd.DataFrame:
    cat = pd.read_csv(PATH_CATALOGO_MUNICIPIOS, encoding="utf-8-sig", dtype=str)

    required = {"cve_ent", "nom_ent", "cve_mun", "nom_mun", "cvegeo"}
    missing = required - set(cat.columns)

    if missing:
        raise ValueError(
            f"El catálogo municipal no contiene columnas requeridas. Faltan: {missing}"
        )

    cat["cve_ent"] = normalize_cve_ent(cat["cve_ent"])
    cat["cve_mun"] = normalize_cve_mun(cat["cve_mun"])
    cat["cvegeo"] = normalize_cvegeo(cat["cvegeo"])
    cat["nom_ent"] = cat["nom_ent"].map(normalize_text)
    cat["nom_mun"] = cat["nom_mun"].map(normalize_text)

    if cat["cvegeo"].duplicated().any():
        raise ValueError("El catálogo municipal contiene cvegeo duplicadas.")

    return cat


def load_municipios_geometry() -> gpd.GeoDataFrame:
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


def get_smn_columns() -> dict:
    header = pd.read_csv(PATH_SMN, encoding="utf-8-sig", nrows=0)
    dummy = pd.DataFrame(columns=header.columns)

    col_map = {
        "id_estacion": detect_column(
            dummy,
            ["id_estacion", "idestacion", "estacion_id", "clave_estacion"],
            "id_estacion"
        ),
        "nombre_estacion": detect_column(
            dummy,
            ["nombre_estacion", "estacion", "nombre"],
            "nombre_estacion",
            required=False
        ),
        "situacion_operativa": detect_column(
            dummy,
            ["situacion_operativa", "situacion", "estatus"],
            "situacion_operativa",
            required=False
        ),
        "estado": detect_column(
            dummy,
            ["estado", "entidad", "nom_ent"],
            "estado",
            required=False
        ),
        "municipio": detect_column(
            dummy,
            ["municipio", "nom_mun"],
            "municipio",
            required=False
        ),
        "latitud": detect_column(
            dummy,
            ["latitud", "latitude", "lat"],
            "latitud"
        ),
        "longitud": detect_column(
            dummy,
            ["longitud", "longitude", "lon", "lng"],
            "longitud"
        ),
        "fecha": detect_column(
            dummy,
            ["fecha", "date"],
            "fecha"
        ),
        "precip": detect_column(
            dummy,
            ["precip_mm", "precipitacion_mm", "precipitación_mm"],
            "precipitación",
            required=False
        ),
        "evap": detect_column(
            dummy,
            ["evap_mm", "evaporacion_mm", "evaporación_mm"],
            "evaporación",
            required=False
        ),
        "tmin": detect_column(
            dummy,
            ["tmin_c", "temperatura_minima_c", "temp_min_c"],
            "temperatura mínima",
            required=False
        ),
        "tmax": detect_column(
            dummy,
            ["tmax_c", "temperatura_maxima_c", "temp_max_c"],
            "temperatura máxima",
            required=False
        ),
    }

    return col_map


# =========================================================
# 4) CATÁLOGO DE ESTACIONES
# =========================================================

def build_estaciones_base(col_map: dict) -> pd.DataFrame:
    usecols = [
        col for col in [
            col_map["id_estacion"],
            col_map["nombre_estacion"],
            col_map["situacion_operativa"],
            col_map["estado"],
            col_map["municipio"],
            col_map["latitud"],
            col_map["longitud"],
        ]
        if col is not None
    ]

    estaciones_parts = []

    reader = pd.read_csv(
        PATH_SMN,
        encoding="utf-8-sig",
        low_memory=False,
        usecols=usecols,
        chunksize=CHUNK_SIZE
    )

    for i, chunk in enumerate(reader, start=1):
        print(f"Construyendo catálogo de estaciones | chunk {i}: {len(chunk):,} registros")

        tmp = pd.DataFrame()
        tmp["id_estacion"] = chunk[col_map["id_estacion"]].astype(str).str.strip()
        tmp["latitud_int"] = clean_numeric(chunk[col_map["latitud"]])
        tmp["longitud_int"] = clean_numeric(chunk[col_map["longitud"]])

        if col_map["nombre_estacion"] is not None:
            tmp["nombre_estacion"] = chunk[col_map["nombre_estacion"]].map(normalize_text)
        else:
            tmp["nombre_estacion"] = ""

        if col_map["situacion_operativa"] is not None:
            tmp["situacion_operativa"] = chunk[col_map["situacion_operativa"]].map(normalize_text)
        else:
            tmp["situacion_operativa"] = ""

        if col_map["estado"] is not None:
            tmp["estado_original"] = chunk[col_map["estado"]].map(normalize_text)
        else:
            tmp["estado_original"] = ""

        if col_map["municipio"] is not None:
            tmp["municipio_original"] = chunk[col_map["municipio"]].map(normalize_text)
        else:
            tmp["municipio_original"] = ""

        estaciones_parts.append(tmp.drop_duplicates())

    estaciones = pd.concat(estaciones_parts, ignore_index=True).drop_duplicates()

    # Si una estación aparece con configuraciones distintas, se conserva la
    # combinación más frecuente.
    freq = (
        estaciones
        .groupby(
            [
                "id_estacion",
                "nombre_estacion",
                "situacion_operativa",
                "estado_original",
                "municipio_original",
                "latitud_int",
                "longitud_int",
            ],
            dropna=False,
            as_index=False
        )
        .size()
        .rename(columns={"size": "frecuencia_configuracion"})
    )

    freq = freq.sort_values(
        ["id_estacion", "frecuencia_configuracion"],
        ascending=[True, False]
    )

    estaciones_final = freq.drop_duplicates(subset=["id_estacion"], keep="first").copy()

    estaciones_final["coordenada_valida"] = coordenada_en_bbox_mexico(
        estaciones_final["latitud_int"],
        estaciones_final["longitud_int"]
    )

    return estaciones_final


def spatial_join_estaciones(
    estaciones: pd.DataFrame,
    municipios_geom: gpd.GeoDataFrame,
    catalogo: pd.DataFrame
) -> pd.DataFrame:
    valid_coords = estaciones[estaciones["coordenada_valida"]].copy()
    invalid_coords = estaciones[~estaciones["coordenada_valida"]].copy()

    if valid_coords.empty:
        estaciones["cvegeo_spatial"] = pd.NA
        estaciones["asignacion_municipio_metodo"] = "sin_asignacion"
        return estaciones

    gdf = gpd.GeoDataFrame(
        valid_coords,
        geometry=gpd.points_from_xy(
            valid_coords["longitud_int"],
            valid_coords["latitud_int"]
        ),
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
    joined.loc[
        joined["cvegeo_spatial"].isna(),
        "asignacion_municipio_metodo"
    ] = "sin_asignacion"

    if not invalid_coords.empty:
        invalid_coords["cvegeo_spatial"] = pd.NA
        invalid_coords["asignacion_municipio_metodo"] = "coordenada_invalida"

        estaciones_joined = pd.concat(
            [joined, invalid_coords],
            ignore_index=True
        )
    else:
        estaciones_joined = joined.copy()

    estaciones_joined["cvegeo"] = normalize_cvegeo(estaciones_joined["cvegeo_spatial"])

    estaciones_joined = estaciones_joined.merge(
        catalogo[["cvegeo", "cve_ent", "nom_ent", "cve_mun", "nom_mun"]],
        on="cvegeo",
        how="left"
    )

    return estaciones_joined


# =========================================================
# 5) AGREGACIÓN SMN MUNICIPIO-DÍA
# =========================================================

def build_chunk_observaciones(
    chunk: pd.DataFrame,
    col_map: dict,
    estaciones_contexto: pd.DataFrame
) -> pd.DataFrame:
    obs = pd.DataFrame()

    obs["id_estacion"] = chunk[col_map["id_estacion"]].astype(str).str.strip()
    obs["fecha"] = pd.to_datetime(chunk[col_map["fecha"]], errors="coerce").dt.date

    if col_map["precip"] is not None:
        obs["precip_mm"] = clean_numeric(chunk[col_map["precip"]])
    else:
        obs["precip_mm"] = pd.NA

    if col_map["evap"] is not None:
        obs["evap_mm"] = clean_numeric(chunk[col_map["evap"]])
    else:
        obs["evap_mm"] = pd.NA

    if col_map["tmin"] is not None:
        obs["tmin_c"] = clean_numeric(chunk[col_map["tmin"]])
    else:
        obs["tmin_c"] = pd.NA

    if col_map["tmax"] is not None:
        obs["tmax_c"] = clean_numeric(chunk[col_map["tmax"]])
    else:
        obs["tmax_c"] = pd.NA

    obs = obs.merge(
        estaciones_contexto[
            ["id_estacion", "cve_ent", "nom_ent", "cve_mun", "nom_mun", "cvegeo"]
        ],
        on="id_estacion",
        how="left"
    )

    return obs


def build_chunk_aggregation(obs: pd.DataFrame) -> pd.DataFrame:
    base = obs.dropna(subset=["cvegeo", "fecha"]).copy()

    if base.empty:
        return pd.DataFrame()

    grouped = (
        base.groupby(
            ["cve_ent", "nom_ent", "cve_mun", "nom_mun", "cvegeo", "fecha"],
            as_index=False
        )
        .agg(
            smn_n_estaciones=("id_estacion", "nunique"),

            smn_precip_mm_sum_values=("precip_mm", "sum"),
            smn_precip_mm_valid_count=("precip_mm", "count"),

            smn_evap_mm_sum_values=("evap_mm", "sum"),
            smn_evap_mm_valid_count=("evap_mm", "count"),

            smn_tmin_c_sum_values=("tmin_c", "sum"),
            smn_tmin_c_valid_count=("tmin_c", "count"),

            smn_tmax_c_sum_values=("tmax_c", "sum"),
            smn_tmax_c_valid_count=("tmax_c", "count"),
        )
    )

    return grouped


def finalize_municipio_dia(partials: list[pd.DataFrame]) -> pd.DataFrame:
    if not partials:
        return pd.DataFrame()

    combined = pd.concat(partials, ignore_index=True)

    grouped = (
        combined.groupby(
            ["cve_ent", "nom_ent", "cve_mun", "nom_mun", "cvegeo", "fecha"],
            as_index=False
        )
        .agg(
            smn_n_estaciones=("smn_n_estaciones", "max"),

            smn_precip_mm_sum_values=("smn_precip_mm_sum_values", "sum"),
            smn_precip_mm_valid_count=("smn_precip_mm_valid_count", "sum"),

            smn_evap_mm_sum_values=("smn_evap_mm_sum_values", "sum"),
            smn_evap_mm_valid_count=("smn_evap_mm_valid_count", "sum"),

            smn_tmin_c_sum_values=("smn_tmin_c_sum_values", "sum"),
            smn_tmin_c_valid_count=("smn_tmin_c_valid_count", "sum"),

            smn_tmax_c_sum_values=("smn_tmax_c_sum_values", "sum"),
            smn_tmax_c_valid_count=("smn_tmax_c_valid_count", "sum"),
        )
    )

    grouped["smn_precip_mm_mean"] = (
        grouped["smn_precip_mm_sum_values"]
        / grouped["smn_precip_mm_valid_count"].replace(0, pd.NA)
    )

    grouped["smn_evap_mm_mean"] = (
        grouped["smn_evap_mm_sum_values"]
        / grouped["smn_evap_mm_valid_count"].replace(0, pd.NA)
    )

    grouped["smn_tmin_c_mean"] = (
        grouped["smn_tmin_c_sum_values"]
        / grouped["smn_tmin_c_valid_count"].replace(0, pd.NA)
    )

    grouped["smn_tmax_c_mean"] = (
        grouped["smn_tmax_c_sum_values"]
        / grouped["smn_tmax_c_valid_count"].replace(0, pd.NA)
    )

    grouped["has_smn"] = 1

    ordered_cols = [
        "cve_ent",
        "nom_ent",
        "cve_mun",
        "nom_mun",
        "cvegeo",
        "fecha",
        "smn_n_estaciones",
        "smn_precip_mm_mean",
        "smn_evap_mm_mean",
        "smn_tmin_c_mean",
        "smn_tmax_c_mean",
        "has_smn",
        "smn_precip_mm_valid_count",
        "smn_evap_mm_valid_count",
        "smn_tmin_c_valid_count",
        "smn_tmax_c_valid_count",
    ]

    grouped = grouped[ordered_cols].copy()
    grouped = grouped.sort_values(["fecha", "cvegeo"]).reset_index(drop=True)

    return grouped


# =========================================================
# 6) VALIDACIÓN
# =========================================================

def build_validation_report(
    stats: dict,
    estaciones_contexto: pd.DataFrame,
    municipio_dia: pd.DataFrame
) -> pd.DataFrame:
    rows = []

    estaciones_total = len(estaciones_contexto)
    estaciones_sin_cvegeo = int(estaciones_contexto["cvegeo"].isna().sum())
    estaciones_coord_invalida = int((~estaciones_contexto["coordenada_valida"]).sum())

    estaciones_sin_catalogo = int(
        estaciones_contexto["cvegeo"].notna().sum()
        - estaciones_contexto["nom_mun"].notna().sum()
    )

    dup_estaciones = int(estaciones_contexto["id_estacion"].duplicated().sum())

    dup_mun_dia = 0
    if not municipio_dia.empty:
        dup_mun_dia = int(municipio_dia.duplicated(subset=["cvegeo", "fecha"]).sum())

    rows.append(build_report_row(
        "smn_registros_diarios_leidos",
        stats["total_leidos"],
        "ok" if stats["total_leidos"] > 0 else "error",
        "Total de observaciones diarias SMN leídas desde DP."
    ))

    rows.append(build_report_row(
        "fecha_min",
        stats["fecha_min"],
        "ok",
        "Fecha mínima detectada en SMN."
    ))

    rows.append(build_report_row(
        "fecha_max",
        stats["fecha_max"],
        "ok",
        "Fecha máxima detectada en SMN."
    ))

    rows.append(build_report_row(
        "smn_fecha_nula",
        stats["fecha_nula"],
        "ok" if stats["fecha_nula"] == 0 else "warning",
        "Observaciones SMN sin fecha válida."
    ))

    rows.append(build_report_row(
        "smn_fuera_periodo_proyecto_2001_2025",
        stats["fuera_periodo"],
        "ok" if stats["fuera_periodo"] == 0 else "warning",
        "Observaciones SMN fuera del periodo general del proyecto."
    ))

    rows.append(build_report_row(
        "smn_estaciones_contexto",
        estaciones_total,
        "ok" if estaciones_total > 0 else "error",
        "Estaciones únicas SMN contextualizadas."
    ))

    rows.append(build_report_row(
        "smn_estaciones_duplicadas_id",
        dup_estaciones,
        "ok" if dup_estaciones == 0 else "error",
        "Duplicados por id_estacion en catálogo de estaciones contextualizadas."
    ))

    rows.append(build_report_row(
        "smn_estaciones_coordenada_invalida",
        estaciones_coord_invalida,
        "ok" if estaciones_coord_invalida == 0 else "warning",
        "Estaciones sin coordenadas válidas según BBOX INEGI 2025."
    ))

    rows.append(build_report_row(
        "smn_estaciones_cvegeo_nula",
        estaciones_sin_cvegeo,
        "ok" if estaciones_sin_cvegeo == 0 else "warning",
        "Estaciones sin municipio asignado por join espacial."
    ))

    rows.append(build_report_row(
        "smn_estaciones_sin_catalogo_municipal",
        estaciones_sin_catalogo,
        "ok" if estaciones_sin_catalogo == 0 else "warning",
        "Estaciones cuyo cvegeo no encontró correspondencia en catálogo municipal."
    ))

    rows.append(build_report_row(
        "smn_observaciones_sin_municipio",
        stats["observaciones_sin_municipio"],
        "ok" if stats["observaciones_sin_municipio"] == 0 else "warning",
        "Observaciones diarias asociadas a estaciones sin municipio asignado."
    ))

    rows.append(build_report_row(
        "municipio_dia_registros",
        len(municipio_dia),
        "ok" if len(municipio_dia) > 0 else "error",
        "Registros generados en integracion_smn_municipio_dia.csv."
    ))

    rows.append(build_report_row(
        "municipio_dia_duplicados_cvegeo_fecha",
        dup_mun_dia,
        "ok" if dup_mun_dia == 0 else "error",
        "Duplicados por clave cvegeo + fecha en agregación municipio-día."
    ))

    return pd.DataFrame(rows)


# =========================================================
# 7) PIPELINE PRINCIPAL
# =========================================================

def main() -> None:
    print("\nIntegración 04 | SMN contexto municipal y municipio-día")

    validate_input_exists()

    col_map = get_smn_columns()
    catalogo_municipios = load_catalogo_municipios()
    municipios_geom = load_municipios_geometry()

    print(f"Dataset SMN: {PATH_SMN}")
    print(f"Municipios geometría: {len(municipios_geom):,}")
    print(f"Catálogo municipal: {len(catalogo_municipios):,}")
    print(f"Chunk size: {CHUNK_SIZE:,}")

    print("\nColumnas detectadas:")
    for key, value in col_map.items():
        print(f"- {key}: {value}")

    print("\nConstruyendo catálogo de estaciones SMN...")
    estaciones_base = build_estaciones_base(col_map)

    print(f"Estaciones únicas detectadas: {len(estaciones_base):,}")

    estaciones_contexto = spatial_join_estaciones(
        estaciones_base,
        municipios_geom,
        catalogo_municipios
    )

    estaciones_contexto = estaciones_contexto.sort_values("id_estacion").reset_index(drop=True)

    estaciones_contexto.to_csv(
        OUT_ESTACIONES_CONTEXTO,
        index=False,
        encoding="utf-8-sig"
    )

    print(f"Estaciones contextualizadas guardadas en: {OUT_ESTACIONES_CONTEXTO}")

    partial_aggs: list[pd.DataFrame] = []

    stats = {
        "total_leidos": 0,
        "fecha_nula": 0,
        "fuera_periodo": 0,
        "observaciones_sin_municipio": 0,
        "fecha_min": None,
        "fecha_max": None,
    }

    usecols = [
        col for col in [
            col_map["id_estacion"],
            col_map["fecha"],
            col_map["precip"],
            col_map["evap"],
            col_map["tmin"],
            col_map["tmax"],
        ]
        if col is not None
    ]

    reader = pd.read_csv(
        PATH_SMN,
        encoding="utf-8-sig",
        low_memory=False,
        usecols=usecols,
        chunksize=CHUNK_SIZE
    )

    print("\nProcesando observaciones diarias SMN...")

    for i, chunk in enumerate(reader, start=1):
        print(f"Procesando chunk {i}... registros: {len(chunk):,}")

        stats["total_leidos"] += len(chunk)

        obs = build_chunk_observaciones(chunk, col_map, estaciones_contexto)

        stats["fecha_nula"] += int(obs["fecha"].isna().sum())
        stats["observaciones_sin_municipio"] += int(obs["cvegeo"].isna().sum())

        fecha_series = pd.to_datetime(obs["fecha"], errors="coerce")

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

        chunk_agg = build_chunk_aggregation(obs)

        if not chunk_agg.empty:
            partial_aggs.append(chunk_agg)

        print(f"  Acumulado leído: {stats['total_leidos']:,}")
        print(f"  Observaciones sin municipio acumuladas: {stats['observaciones_sin_municipio']:,}")

    print("\nConsolidando agregación municipio-día...")
    municipio_dia = finalize_municipio_dia(partial_aggs)

    validacion = build_validation_report(stats, estaciones_contexto, municipio_dia)

    municipio_dia.to_csv(OUT_MUNICIPIO_DIA, index=False, encoding="utf-8-sig")
    validacion.to_csv(OUT_VALIDACION, index=False, encoding="utf-8-sig")

    errores = validacion[validacion["estatus"] == "error"]

    if not errores.empty:
        print("\nErrores de validación:")
        print(errores.to_string(index=False))
        raise ValueError("La integración SMN terminó con errores. Revisa el reporte.")

    print("\nArchivos generados:")
    print(f"- {OUT_ESTACIONES_CONTEXTO}")
    print(f"- {OUT_MUNICIPIO_DIA}")
    print(f"- {OUT_VALIDACION}")

    print("\nResumen:")
    print(f"- Registros SMN leídos: {stats['total_leidos']:,}")
    print(f"- Estaciones SMN contextualizadas: {len(estaciones_contexto):,}")
    print(f"- Registros SMN municipio-día: {len(municipio_dia):,}")
    print(f"- Observaciones sin municipio: {stats['observaciones_sin_municipio']:,}")
    print(f"- Warnings: {(validacion['estatus'] == 'warning').sum()}")
    print(f"- Errores: {(validacion['estatus'] == 'error').sum()}")

    print("\nProceso terminado.")


if __name__ == "__main__":
    main()