# -*- coding: utf-8 -*-
"""
Integration 02 | CONAFOR contexto municipal y agregación municipio-día

Este script integra el dataset limpio de CONAFOR con el catálogo municipal de INEGI
para construir una versión contextualizada de eventos confirmados de incendios
forestales y una agregación diaria municipal.

Salidas
-------
1) 04_integration/datasets/integracion_conafor_eventos_contexto.csv
2) 04_integration/datasets/integracion_conafor_municipio_dia.csv
3) 04_integration/reports/integracion_02_validacion_conafor_context.csv

Objetivo
--------
- Validar/asignar cvegeo municipal a eventos CONAFOR.
- Comparar cvegeo original contra cvegeo derivado por join espacial.
- Construir agregación municipio-día usando fecha_inicio.
- Mantener trazabilidad de la asignación municipal.
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

PATH_CONAFOR = (
    BASE_DIR
    / "03_data-preparation"
    / "conafor"
    / "datasets"
    / "conafor_eventos_2005_2025_limpio.csv"
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

OUT_EVENTOS_CONTEXTO = OUT_DATASETS_DIR / "integracion_conafor_eventos_contexto.csv"
OUT_MUNICIPIO_DIA = OUT_DATASETS_DIR / "integracion_conafor_municipio_dia.csv"
OUT_VALIDACION = OUT_REPORTS_DIR / "integracion_02_validacion_conafor_contexto.csv"

LAYER_MUNICIPIOS = "municipios_limpio"

PROJECT_START = "2001-01-01"
PROJECT_END = "2025-12-31"

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
# 2) UTILIDADES GENERALES
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


def normalize_cve_ent(series: pd.Series) -> pd.Series:
    s = series.astype(str).str.strip()
    s = s.str.replace(r"\.0$", "", regex=True)
    s = s.str.extract(r"(\d+)", expand=False)
    return s.str.zfill(2)


def normalize_cve_mun(series: pd.Series) -> pd.Series:
    s = series.astype(str).str.strip()
    s = s.str.replace(r"\.0$", "", regex=True)
    s = s.str.extract(r"(\d+)", expand=False)
    return s.str.zfill(3)


def normalize_cvegeo(series: pd.Series) -> pd.Series:
    s = series.astype(str).str.strip()
    s = s.str.replace(r"\.0$", "", regex=True)
    s = s.str.extract(r"(\d+)", expand=False)
    return s.str.zfill(5)


def clean_numeric(series: pd.Series) -> pd.Series:
    if series is None:
        return pd.Series(dtype="float64")

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

def load_conafor() -> pd.DataFrame:
    if not PATH_CONAFOR.exists():
        raise FileNotFoundError(f"No existe el dataset CONAFOR limpio: {PATH_CONAFOR}")

    df = pd.read_csv(PATH_CONAFOR, encoding="utf-8-sig", low_memory=False)
    print(f"CONAFOR registros leídos: {len(df):,}")

    return df


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

    return municipios


# =========================================================
# 4) CONTEXTUALIZACIÓN CONAFOR
# =========================================================

def prepare_conafor_fields(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    lat_col = detect_column(df, ["latitud", "latitude", "lat"], "latitud")
    lon_col = detect_column(df, ["longitud", "longitude", "lon", "lng"], "longitud")
    fecha_col = detect_column(df, ["fecha_inicio", "f_inicio", "fecha_de_inicio"], "fecha de inicio")
    sup_col = detect_column(
        df,
        ["total_hectáreas", "total_hectareas", "sup_ha", "superficie_ha", "superficie_afectada"],
        "superficie/hectáreas",
        required=False
    )

    cvegeo_col = detect_column(df, ["cvegeo", "cve_geo", "clavegeo"], "cvegeo", required=False)
    cve_ent_col = detect_column(df, ["cve_ent", "clave_entidad"], "cve_ent", required=False)
    cve_mun_col = detect_column(df, ["cve_mun", "clave_municipio"], "cve_mun", required=False)

    df["latitud_int"] = clean_numeric(df[lat_col])
    df["longitud_int"] = clean_numeric(df[lon_col])
    df["fecha"] = pd.to_datetime(df[fecha_col], errors="coerce").dt.date

    if sup_col is not None:
        df["conafor_total_hectareas"] = clean_numeric(df[sup_col])
    else:
        df["conafor_total_hectareas"] = pd.NA

    if cvegeo_col is not None:
        df["cvegeo_original"] = normalize_cvegeo(df[cvegeo_col])
    elif cve_ent_col is not None and cve_mun_col is not None:
        df["cvegeo_original"] = normalize_cve_ent(df[cve_ent_col]) + normalize_cve_mun(df[cve_mun_col])
    else:
        df["cvegeo_original"] = pd.NA

    df["coordenada_valida"] = coordenada_en_bbox_mexico(
        df["latitud_int"],
        df["longitud_int"]
    )

    return df


def spatial_join_conafor(df: pd.DataFrame, municipios_geom: gpd.GeoDataFrame) -> pd.DataFrame:
    df = df.copy()

    valid_coords = df[df["coordenada_valida"]].copy()
    invalid_coords = df[~df["coordenada_valida"]].copy()

    print(f"CONAFOR con coordenadas válidas para join espacial: {len(valid_coords):,}")
    print(f"CONAFOR sin coordenadas válidas para join espacial: {len(invalid_coords):,}")

    if valid_coords.empty:
        df["cvegeo_spatial"] = pd.NA
        return df

    gdf = gpd.GeoDataFrame(
        valid_coords,
        geometry=gpd.points_from_xy(valid_coords["longitud_int"], valid_coords["latitud_int"]),
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

    if not invalid_coords.empty:
        invalid_coords["cvegeo_spatial"] = pd.NA
        output = pd.concat([joined, invalid_coords], ignore_index=True)
    else:
        output = joined.copy()

    return pd.DataFrame(output)


def assign_integration_cvegeo(df: pd.DataFrame, catalogo: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    df["cvegeo_spatial"] = normalize_cvegeo(df["cvegeo_spatial"])
    df["cvegeo_original"] = normalize_cvegeo(df["cvegeo_original"])

    # Evitar que valores nulos se conviertan en claves falsas.
    invalid_keys = {"00nan", "0nan", "nan", "00000", "", "none", "None"}

    df.loc[
        df["cvegeo_spatial"].astype(str).str.lower().isin(invalid_keys),
        "cvegeo_spatial"
    ] = pd.NA

    df.loc[
        df["cvegeo_original"].astype(str).str.lower().isin(invalid_keys),
        "cvegeo_original"
    ] = pd.NA

    df["cvegeo_conflicto_original_vs_spatial"] = (
        df["cvegeo_original"].notna()
        & df["cvegeo_spatial"].notna()
        & (df["cvegeo_original"] != df["cvegeo_spatial"])
    )

    # Regla de integración:
    # 1) Si existe cvegeo_spatial, se usa porque deriva de coordenadas + geometría INEGI.
    # 2) Si no existe cvegeo_spatial, se usa cvegeo_original.
    # 3) Si no existe ninguno, queda nulo.
    df["cvegeo"] = df["cvegeo_spatial"].combine_first(df["cvegeo_original"])

    df["asignacion_municipio_metodo"] = "sin_asignacion"
    df.loc[
        df["cvegeo_original"].notna() & df["cvegeo_spatial"].isna(),
        "asignacion_municipio_metodo"
    ] = "cvegeo_original"

    df.loc[
        df["cvegeo_spatial"].notna(),
        "asignacion_municipio_metodo"
    ] = "spatial_join"

    df.loc[
        df["cvegeo_conflicto_original_vs_spatial"],
        "asignacion_municipio_metodo"
    ] = "spatial_join_con_conflicto"

    # Preservar campos administrativos originales de CONAFOR como trazabilidad,
    # si existen, antes de imponer los campos canónicos del catálogo.
    original_admin_map = {
        "cve_ent": "conafor_cve_ent_original",
        "nom_ent": "conafor_nom_ent_original",
        "cve_mun": "conafor_cve_mun_original",
        "nom_mun": "conafor_nom_mun_original",
        "estado": "conafor_estado_original",
        "municipio": "conafor_municipio_original",
    }

    for old_col, new_col in original_admin_map.items():
        if old_col in df.columns and new_col not in df.columns:
            df = df.rename(columns={old_col: new_col})

    # Eliminar cualquier columna administrativa canónica residual para evitar
    # conflictos con el catálogo municipal.
    for col in ["cve_ent", "nom_ent", "cve_mun", "nom_mun"]:
        if col in df.columns:
            df = df.drop(columns=[col])

    cat_merge = catalogo[["cvegeo", "cve_ent", "nom_ent", "cve_mun", "nom_mun"]].copy()

    df = df.merge(
        cat_merge,
        on="cvegeo",
        how="left"
    )

    return df


# =========================================================
# 5) AGREGACIÓN MUNICIPIO-DÍA
# =========================================================

def build_conafor_municipio_dia(df: pd.DataFrame) -> pd.DataFrame:
    base = df.dropna(subset=["cvegeo", "fecha"]).copy()

    grouped = (
        base.groupby(["cve_ent", "nom_ent", "cve_mun", "nom_mun", "cvegeo", "fecha"], as_index=False)
        .agg(
            conafor_event_count=("fecha", "size"),
            conafor_total_hectareas_sum=("conafor_total_hectareas", "sum"),
            conafor_total_hectareas_mean=("conafor_total_hectareas", "mean"),
        )
    )

    grouped["has_conafor"] = 1
    grouped["conafor_disponible"] = 1

    grouped = grouped.sort_values(["fecha", "cvegeo"]).reset_index(drop=True)

    return grouped


# =========================================================
# 6) VALIDACIÓN
# =========================================================

def build_validation_report(eventos: pd.DataFrame, municipio_dia: pd.DataFrame) -> pd.DataFrame:
    rows = []

    total_eventos = len(eventos)
    eventos_fecha_nula = int(eventos["fecha"].isna().sum())
    eventos_cvegeo_nula = int(eventos["cvegeo"].isna().sum())
    eventos_sin_catalogo = int(eventos["nom_mun"].isna().sum())
    conflictos = int(eventos["cvegeo_conflicto_original_vs_spatial"].sum())
    coords_invalidas = int((~eventos["coordenada_valida"]).sum())

    fecha_min = eventos["fecha"].min()
    fecha_max = eventos["fecha"].max()

    dup_mun_dia = int(municipio_dia.duplicated(subset=["cvegeo", "fecha"]).sum())

    rows.append(build_report_row(
        "eventos_conafor_leidos",
        total_eventos,
        "ok" if total_eventos > 0 else "error",
        "Total de eventos CONAFOR leídos desde DP."
    ))

    rows.append(build_report_row(
        "fecha_min",
        fecha_min,
        "ok",
        "Fecha mínima detectada en eventos CONAFOR."
    ))

    rows.append(build_report_row(
        "fecha_max",
        fecha_max,
        "ok",
        "Fecha máxima detectada en eventos CONAFOR."
    ))

    rows.append(build_report_row(
        "eventos_fecha_nula",
        eventos_fecha_nula,
        "ok" if eventos_fecha_nula == 0 else "warning",
        "Eventos sin fecha válida para agregación municipio-día."
    ))

    rows.append(build_report_row(
        "eventos_cvegeo_nula",
        eventos_cvegeo_nula,
        "ok" if eventos_cvegeo_nula == 0 else "warning",
        "Eventos sin cvegeo integrado."
    ))

    rows.append(build_report_row(
        "eventos_sin_catalogo_municipal",
        eventos_sin_catalogo,
        "ok" if eventos_sin_catalogo == 0 else "warning",
        "Eventos cuyo cvegeo integrado no encontró correspondencia en catálogo municipal."
    ))

    rows.append(build_report_row(
        "conflictos_cvegeo_original_vs_spatial",
        conflictos,
        "ok" if conflictos == 0 else "warning",
        "Eventos donde el cvegeo original difiere del cvegeo asignado por join espacial."
    ))

    rows.append(build_report_row(
        "eventos_con_coordenada_invalida",
        coords_invalidas,
        "ok" if coords_invalidas == 0 else "warning",
        "Eventos sin coordenadas válidas para join espacial."
    ))

    rows.append(build_report_row(
        "municipio_dia_registros",
        len(municipio_dia),
        "ok" if len(municipio_dia) > 0 else "error",
        "Registros generados en integration_conafor_municipio_dia.csv."
    ))

    rows.append(build_report_row(
        "municipio_dia_duplicados_cvegeo_fecha",
        dup_mun_dia,
        "ok" if dup_mun_dia == 0 else "error",
        "Duplicados por clave cvegeo + fecha en agregación municipio-día."
    ))

    periodo_fuera = int(
        (
            (pd.to_datetime(eventos["fecha"], errors="coerce") < pd.to_datetime(PROJECT_START))
            | (pd.to_datetime(eventos["fecha"], errors="coerce") > pd.to_datetime(PROJECT_END))
        ).sum()
    )

    rows.append(build_report_row(
        "eventos_fuera_periodo_proyecto_2001_2025",
        periodo_fuera,
        "ok" if periodo_fuera == 0 else "warning",
        "Eventos fuera del periodo general del proyecto."
    ))

    return pd.DataFrame(rows)


# =========================================================
# 7) PIPELINE PRINCIPAL
# =========================================================

def main() -> None:
    print("\nIntegration 02 | CONAFOR contexto municipal y municipio-día")

    conafor_raw = load_conafor()
    catalogo_municipios = load_catalogo_municipios()
    municipios_geom = load_municipios_geometry()

    conafor_prepared = prepare_conafor_fields(conafor_raw)
    conafor_joined = spatial_join_conafor(conafor_prepared, municipios_geom)
    conafor_contexto = assign_integration_cvegeo(conafor_joined, catalogo_municipios)

    conafor_municipio_dia = build_conafor_municipio_dia(conafor_contexto)

    validacion = build_validation_report(conafor_contexto, conafor_municipio_dia)

    # Guardar siempre las salidas para poder revisar resultados y depurar.
    conafor_contexto.to_csv(OUT_EVENTOS_CONTEXTO, index=False, encoding="utf-8-sig")
    conafor_municipio_dia.to_csv(OUT_MUNICIPIO_DIA, index=False, encoding="utf-8-sig")
    validacion.to_csv(OUT_VALIDACION, index=False, encoding="utf-8-sig")

    errores = validacion[validacion["estatus"] == "error"]
    if not errores.empty:
        print("\nErrores de validación:")
        print(errores.to_string(index=False))
        raise ValueError("La integración CONAFOR terminó con errores. Revisa el reporte.")

    print("\nArchivos generados:")
    print(f"- {OUT_EVENTOS_CONTEXTO}")
    print(f"- {OUT_MUNICIPIO_DIA}")
    print(f"- {OUT_VALIDACION}")

    print("\nResumen:")
    print(f"- Eventos CONAFOR contextualizados: {len(conafor_contexto):,}")
    print(f"- Registros CONAFOR municipio-día: {len(conafor_municipio_dia):,}")
    print(f"- Warnings: {(validacion['estatus'] == 'warning').sum()}")
    print(f"- Errores: {(validacion['estatus'] == 'error').sum()}")

    print("\nProceso terminado.")


if __name__ == "__main__":
    main()