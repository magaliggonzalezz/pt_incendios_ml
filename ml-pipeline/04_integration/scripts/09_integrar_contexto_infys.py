# -*- coding: utf-8 -*-
"""
Integración 09 | Contexto estructural INFyS

Este script integra datasets limpios de INFyS como contexto estructural
municipal y estatal, a partir del diagnóstico generado en Integration 08.

Salidas
-------
1) 04_integration/datasets/integracion_infys_municipio_contexto.csv
2) 04_integration/datasets/integracion_infys_entidad_contexto.csv
3) 04_integration/reports/integracion_09_validacion_contexto_infys.csv

Objetivo
--------
- Integrar INFyS sin duplicarlo en bases diarias.
- Generar contexto municipal cuando existan claves municipales, nombres
  administrativos o coordenadas geográficas.
- Generar contexto estatal cuando existan claves estatales o se derive desde
  contexto municipal.
- Omitir datasets nacionales de los flujos diarios.
- No generar matriz de modelado.
- No hacer Feature Engineering avanzado.
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

PATH_INFYS_DATASETS = (
    BASE_DIR
    / "03_data-preparation"
    / "infys"
    / "datasets"
)

PATH_DIAGNOSTICO_INFYS = (
    BASE_DIR
    / "04_integration"
    / "reports"
    / "integracion_08_diagnostico_contexto_infys.csv"
)

PATH_CATALOGO_MUNICIPIOS = (
    BASE_DIR
    / "04_integration"
    / "datasets"
    / "integracion_catalogo_municipios.csv"
)

PATH_CATALOGO_ENTIDADES = (
    BASE_DIR
    / "04_integration"
    / "datasets"
    / "integracion_catalogo_entidades.csv"
)

PATH_INEGI_GPKG = (
    BASE_DIR
    / "03_data-preparation"
    / "inegi"
    / "datasets"
    / "inegi_capas_limpias.gpkg"
)

OUT_DATASETS_DIR = BASE_DIR / "04_integration" / "datasets"
OUT_REPORTS_DIR = BASE_DIR / "04_integration" / "reports"

OUT_MUNICIPIO_CONTEXTO = OUT_DATASETS_DIR / "integracion_infys_municipio_contexto.csv"
OUT_ENTIDAD_CONTEXTO = OUT_DATASETS_DIR / "integracion_infys_entidad_contexto.csv"
OUT_VALIDACION = OUT_REPORTS_DIR / "integracion_09_validacion_contexto_infys.csv"

OUT_DATASETS_DIR.mkdir(parents=True, exist_ok=True)
OUT_REPORTS_DIR.mkdir(parents=True, exist_ok=True)

LAYER_MUNICIPIOS = "municipios_limpio"

# Fuente: INEGI, Marco Geoestadístico Nacional 2025.
# Calculado con get_mexico_bbox.py a partir de 00ent.shp.
# CRS: WGS84 / EPSG:4326.
MEXICO_BBOX = {
    "lat_min": 14.532098,
    "lat_max": 32.718649,
    "lon_min": -118.365251,
    "lon_max": -86.710401,
}

# Datasets que el diagnóstico recomienda no integrar a flujos diarios.
RECOMENDACIONES_OMITIR = {
    "no_integrar_a_flujos_diarios",
}

# Datasets que requieren revisión manual por no tener clave espacial suficiente.
RECOMENDACIONES_REVISION_MANUAL = {
    "revisar_manual",
}

# Datasets georreferenciados que sí pueden agregarse espacialmente.
RECOMENDACIONES_PUNTO = {
    "agregar_espacialmente_antes_de_integrar",
}

# Datasets que pueden integrarse directamente a entidad.
RECOMENDACIONES_ENTIDAD = {
    "entidad_contexto",
}

# Datasets que pueden integrarse a municipio y derivar a entidad.
RECOMENDACIONES_MUNICIPIO = {
    "municipio_contexto_y_entidad_contexto_derivado",
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


def normalize_text(value) -> str:
    if pd.isna(value):
        return ""

    s = str(value).strip().upper()
    s = unicodedata.normalize("NFKD", s)
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    s = " ".join(s.split())
    return s


def normalize_code(series: pd.Series, width: int) -> pd.Series:
    s = series.astype(str).str.strip()
    s = s.str.replace(r"\.0$", "", regex=True)
    extracted = s.str.extract(r"(\d+)", expand=False)
    return extracted.where(extracted.notna(), pd.NA).str.zfill(width)


def normalize_cve_ent(series: pd.Series) -> pd.Series:
    return normalize_code(series, 2)


def normalize_cve_mun(series: pd.Series) -> pd.Series:
    return normalize_code(series, 3)


def normalize_cvegeo(series: pd.Series) -> pd.Series:
    return normalize_code(series, 5)


def detect_column(
    df: pd.DataFrame,
    candidates: list[str],
    label: str,
    required: bool = False
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
            f"No se pudo detectar columna requerida para '{label}'. "
            f"Columnas disponibles: {list(df.columns)}"
        )

    return None


def clean_numeric(series: pd.Series) -> pd.Series:
    s = series.astype(str).str.strip()
    s = s.str.replace(",", ".", regex=False)
    s = s.str.replace(r"[^\d\.\-]", "", regex=True)
    return pd.to_numeric(s, errors="coerce")


def build_report_row(archivo: str, indicador: str, valor, estatus: str, observacion: str) -> dict:
    return {
        "archivo": archivo,
        "indicador": indicador,
        "valor": valor,
        "estatus": estatus,
        "observacion": observacion,
    }


def infer_cycle_from_filename(filename: str) -> str:
    name = filename.lower()

    if "2004_2009" in name or "2004-2009" in name:
        return "2004-2009"
    if "2009_2014" in name or "2009-2014" in name:
        return "2009-2014"
    if "2015_2020" in name or "2015-2020" in name:
        return "2015-2020"
    if "2024" in name:
        return "2024"

    return ""


def get_dataset_prefix(filename: str) -> str:
    name = filename.lower()
    name = name.replace(".csv", "")
    name = name.replace("_limpio", "")
    name = name.replace("infys_", "")
    name = name.replace("2015_2020", "c2015_2020")
    name = name.replace("2004_2009", "c2004_2009")
    name = name.replace("2009_2014", "c2009_2014")
    name = name.replace("-", "_")

    # Evitar nombres demasiado largos.
    replacements = {
        "secciones_conglomerados": "secc_cong",
        "secciones_sitios": "secc_sitios",
        "indicadores_": "ind_",
        "incremento_medio_anual": "ima",
        "distribucion_at_dn": "dist_at_dn",
        "tipo_propiedad": "tipo_prop",
        "superficie_": "sup_",
    }

    for old, new in replacements.items():
        name = name.replace(old, new)

    return f"infys_{name}"


def coordenada_en_bbox_mexico(lat: pd.Series, lon: pd.Series) -> pd.Series:
    return (
        lat.between(MEXICO_BBOX["lat_min"], MEXICO_BBOX["lat_max"])
        & lon.between(MEXICO_BBOX["lon_min"], MEXICO_BBOX["lon_max"])
    )


# =========================================================
# 3) CARGAS BASE
# =========================================================

def validate_input_exists() -> None:
    missing = []

    for path, label in [
        (PATH_INFYS_DATASETS, "directorio datasets INFyS"),
        (PATH_DIAGNOSTICO_INFYS, "diagnóstico INFyS 08"),
        (PATH_CATALOGO_MUNICIPIOS, "catálogo municipios"),
        (PATH_CATALOGO_ENTIDADES, "catálogo entidades"),
        (PATH_INEGI_GPKG, "GeoPackage INEGI"),
    ]:
        if not path.exists():
            missing.append(f"- {label}: {path}")

    if missing:
        raise FileNotFoundError(
            "Faltan insumos para integrar contexto INFyS:\n"
            + "\n".join(missing)
        )


def load_diagnostico() -> pd.DataFrame:
    df = pd.read_csv(PATH_DIAGNOSTICO_INFYS, encoding="utf-8-sig", dtype=str)
    required = {"archivo", "existe", "integracion_recomendada", "granularidad_probable"}

    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"El diagnóstico INFyS no contiene columnas requeridas: {missing}")

    return df


def load_catalogo_municipios() -> pd.DataFrame:
    cat = pd.read_csv(PATH_CATALOGO_MUNICIPIOS, encoding="utf-8-sig", dtype=str)

    required = {"cve_ent", "nom_ent", "cve_mun", "nom_mun", "cvegeo"}
    missing = required - set(cat.columns)
    if missing:
        raise ValueError(f"Faltan columnas en catálogo municipal: {missing}")

    cat["cve_ent"] = normalize_cve_ent(cat["cve_ent"])
    cat["cve_mun"] = normalize_cve_mun(cat["cve_mun"])
    cat["cvegeo"] = normalize_cvegeo(cat["cvegeo"])
    cat["nom_ent_norm"] = cat["nom_ent"].map(normalize_text)
    cat["nom_mun_norm"] = cat["nom_mun"].map(normalize_text)

    cat = cat[
        ["cve_ent", "nom_ent", "cve_mun", "nom_mun", "cvegeo", "nom_ent_norm", "nom_mun_norm"]
    ].copy()

    if cat["cvegeo"].duplicated().any():
        raise ValueError("El catálogo municipal contiene cvegeo duplicadas.")

    return cat


def load_catalogo_entidades() -> pd.DataFrame:
    cat = pd.read_csv(PATH_CATALOGO_ENTIDADES, encoding="utf-8-sig", dtype=str)

    required = {"cve_ent", "nom_ent"}
    missing = required - set(cat.columns)
    if missing:
        raise ValueError(f"Faltan columnas en catálogo de entidades: {missing}")

    cat["cve_ent"] = normalize_cve_ent(cat["cve_ent"])
    cat["nom_ent_norm"] = cat["nom_ent"].map(normalize_text)

    cat = cat[["cve_ent", "nom_ent", "nom_ent_norm"]].drop_duplicates().copy()

    if cat["cve_ent"].duplicated().any():
        raise ValueError("El catálogo de entidades contiene cve_ent duplicadas.")

    return cat


def load_municipios_geometry(catalogo_municipios: pd.DataFrame) -> gpd.GeoDataFrame:
    municipios = gpd.read_file(PATH_INEGI_GPKG, layer=LAYER_MUNICIPIOS)

    if municipios.crs is None:
        raise ValueError("La capa municipios_limpio no tiene CRS definido.")

    cvegeo_col = detect_column(
        municipios,
        ["cvegeo", "clavegeo", "clave_geografica"],
        "cvegeo",
        required=True
    )

    municipios["cvegeo"] = normalize_cvegeo(municipios[cvegeo_col])

    municipios = municipios[["cvegeo", "geometry"]].copy()
    municipios = municipios.merge(
        catalogo_municipios[["cve_ent", "nom_ent", "cve_mun", "nom_mun", "cvegeo"]],
        on="cvegeo",
        how="left"
    )

    municipios = municipios[municipios.geometry.notna()].copy()
    municipios = municipios[~municipios.geometry.is_empty].copy()

    if municipios["cvegeo"].duplicated().any():
        raise ValueError("La geometría municipal tiene cvegeo duplicadas.")

    return municipios


def read_infys_csv(path: Path) -> pd.DataFrame:
    try:
        return pd.read_csv(path, encoding="utf-8-sig", low_memory=False)
    except UnicodeDecodeError:
        return pd.read_csv(path, encoding="latin-1", low_memory=False)


# =========================================================
# 4) ESTANDARIZACIÓN DE CLAVES
# =========================================================

def attach_entity_keys(df: pd.DataFrame, catalogo_entidades: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()

    cve_ent_col = detect_column(
        out,
        ["cve_ent", "clave_entidad", "clave_estado"],
        "cve_ent"
    )

    estado_col = detect_column(
        out,
        ["nom_ent", "estado", "entidad", "nombre_entidad", "nombre_estado"],
        "nombre entidad"
    )

    if cve_ent_col is not None:
        out["cve_ent"] = normalize_cve_ent(out[cve_ent_col])
    else:
        out["cve_ent"] = pd.NA

    if estado_col is not None:
        out["nom_ent_norm"] = out[estado_col].map(normalize_text)
    else:
        out["nom_ent_norm"] = ""

    # Si falta cve_ent, se intenta resolver por nombre normalizado.
    missing_mask = out["cve_ent"].isna()

    if missing_mask.any() and estado_col is not None:
        out = out.merge(
            catalogo_entidades[["cve_ent", "nom_ent_norm"]].rename(columns={"cve_ent": "cve_ent_from_name"}),
            on="nom_ent_norm",
            how="left"
        )

        out.loc[missing_mask, "cve_ent"] = out.loc[missing_mask, "cve_ent_from_name"]
        out = out.drop(columns=["cve_ent_from_name"], errors="ignore")

    out = out.merge(
        catalogo_entidades[["cve_ent", "nom_ent"]],
        on="cve_ent",
        how="left"
    )

    return out


def attach_municipal_keys(df: pd.DataFrame, catalogo_municipios: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()

    cvegeo_col = detect_column(
        out,
        ["cvegeo", "cve_geo", "clavegeo", "clave_geoestadistica"],
        "cvegeo"
    )

    cve_ent_col = detect_column(
        out,
        ["cve_ent", "clave_entidad", "clave_estado"],
        "cve_ent"
    )

    cve_mun_col = detect_column(
        out,
        ["cve_mun", "clave_municipio"],
        "cve_mun"
    )

    estado_col = detect_column(
        out,
        ["nom_ent", "estado", "entidad", "nombre_entidad", "nombre_estado"],
        "nombre entidad"
    )

    municipio_col = detect_column(
        out,
        ["nom_mun", "municipio", "nombre_municipio"],
        "nombre municipio"
    )

    # Guardar claves detectadas en columnas temporales para evitar conflictos
    # con las columnas canónicas del catálogo.
    if cvegeo_col is not None:
        out["cvegeo_tmp"] = normalize_cvegeo(out[cvegeo_col])
    else:
        out["cvegeo_tmp"] = pd.NA

    if cve_ent_col is not None:
        out["cve_ent_tmp"] = normalize_cve_ent(out[cve_ent_col])
    else:
        out["cve_ent_tmp"] = pd.NA

    if cve_mun_col is not None:
        out["cve_mun_tmp"] = normalize_cve_mun(out[cve_mun_col])
    else:
        out["cve_mun_tmp"] = pd.NA

    # Resolver cvegeo desde cve_ent + cve_mun cuando no exista cvegeo directo.
    mask_no_cvegeo = out["cvegeo_tmp"].isna()
    mask_codes = out["cve_ent_tmp"].notna() & out["cve_mun_tmp"].notna()

    out.loc[mask_no_cvegeo & mask_codes, "cvegeo_tmp"] = (
        out.loc[mask_no_cvegeo & mask_codes, "cve_ent_tmp"]
        + out.loc[mask_no_cvegeo & mask_codes, "cve_mun_tmp"]
    )

    # Resolver por nombres normalizados si sigue sin cvegeo.
    if estado_col is not None:
        out["nom_ent_norm_tmp"] = out[estado_col].map(normalize_text)
    else:
        out["nom_ent_norm_tmp"] = ""

    if municipio_col is not None:
        out["nom_mun_norm_tmp"] = out[municipio_col].map(normalize_text)
    else:
        out["nom_mun_norm_tmp"] = ""

    unresolved = out["cvegeo_tmp"].isna()

    if unresolved.any() and estado_col is not None and municipio_col is not None:
        cat_names = catalogo_municipios[
            ["cvegeo", "nom_ent_norm", "nom_mun_norm"]
        ].copy()

        cat_names = cat_names.rename(columns={
            "cvegeo": "cvegeo_from_name",
            "nom_ent_norm": "nom_ent_norm_tmp",
            "nom_mun_norm": "nom_mun_norm_tmp",
        })

        out = out.merge(
            cat_names,
            on=["nom_ent_norm_tmp", "nom_mun_norm_tmp"],
            how="left"
        )

        unresolved_after_merge = out["cvegeo_tmp"].isna()
        out.loc[unresolved_after_merge, "cvegeo_tmp"] = out.loc[
            unresolved_after_merge,
            "cvegeo_from_name"
        ]

        out = out.drop(columns=["cvegeo_from_name"], errors="ignore")

    out["cvegeo"] = normalize_cvegeo(out["cvegeo_tmp"])

    # Eliminar columnas canónicas previas para que el catálogo imponga las definitivas.
    out = out.drop(
        columns=[
            "cve_ent",
            "nom_ent",
            "cve_mun",
            "nom_mun",
        ],
        errors="ignore"
    )

    out = out.merge(
        catalogo_municipios[["cve_ent", "nom_ent", "cve_mun", "nom_mun", "cvegeo"]],
        on="cvegeo",
        how="left"
    )

    out = out.drop(
        columns=[
            "cvegeo_tmp",
            "cve_ent_tmp",
            "cve_mun_tmp",
            "nom_ent_norm_tmp",
            "nom_mun_norm_tmp",
        ],
        errors="ignore"
    )

    return out


def attach_municipal_keys_by_coordinates(
    df: pd.DataFrame,
    municipios_geom: gpd.GeoDataFrame
) -> pd.DataFrame:
    out = df.copy()

    lat_col = detect_column(
        out,
        ["latitud", "latitude", "lat"],
        "latitud"
    )

    lon_col = detect_column(
        out,
        ["longitud", "longitude", "lon", "lng"],
        "longitud"
    )

    if lat_col is None or lon_col is None:
        out["cvegeo"] = pd.NA
        out["cve_ent"] = pd.NA
        out["nom_ent"] = pd.NA
        out["cve_mun"] = pd.NA
        out["nom_mun"] = pd.NA
        return out

    out["latitud_int"] = clean_numeric(out[lat_col])
    out["longitud_int"] = clean_numeric(out[lon_col])

    out["coordenada_valida"] = coordenada_en_bbox_mexico(
        out["latitud_int"],
        out["longitud_int"]
    )

    valid = out[out["coordenada_valida"]].copy()
    invalid = out[~out["coordenada_valida"]].copy()

    if valid.empty:
        out["cvegeo"] = pd.NA
        out["cve_ent"] = pd.NA
        out["nom_ent"] = pd.NA
        out["cve_mun"] = pd.NA
        out["nom_mun"] = pd.NA
        return out

    # Evitar conflictos por columnas administrativas vacías ya presentes
    # en algunos datasets INFyS.
    valid = valid.drop(
        columns=["cvegeo", "cve_ent", "nom_ent", "cve_mun", "nom_mun"],
        errors="ignore"
    )

    invalid = invalid.drop(
        columns=["cvegeo", "cve_ent", "nom_ent", "cve_mun", "nom_mun"],
        errors="ignore"
    )

    points = gpd.GeoDataFrame(
        valid,
        geometry=gpd.points_from_xy(valid["longitud_int"], valid["latitud_int"]),
        crs="EPSG:4326"
    )

    if points.crs != municipios_geom.crs:
        points = points.to_crs(municipios_geom.crs)

    joined = gpd.sjoin(
        points,
        municipios_geom[["cvegeo", "cve_ent", "nom_ent", "cve_mun", "nom_mun", "geometry"]],
        how="left",
        predicate="within"
    )

    joined = joined.drop(columns=["index_right", "geometry"], errors="ignore")

    if not invalid.empty:
        invalid["cvegeo"] = pd.NA
        invalid["cve_ent"] = pd.NA
        invalid["nom_ent"] = pd.NA
        invalid["cve_mun"] = pd.NA
        invalid["nom_mun"] = pd.NA

        out_final = pd.concat([joined, invalid], ignore_index=True)
    else:
        out_final = joined.copy()

    out_final["cvegeo"] = normalize_cvegeo(out_final["cvegeo"])
    out_final["cve_ent"] = normalize_cve_ent(out_final["cve_ent"])
    out_final["cve_mun"] = normalize_cve_mun(out_final["cve_mun"])

    return out_final


# =========================================================
# 5) RESÚMENES CONSERVADORES
# =========================================================

def choose_numeric_columns(df: pd.DataFrame) -> list[str]:
    exclude_tokens = {
        "cveent", "cvemun", "cvegeo", "clave", "id", "latitud", "longitud",
        "latitude", "longitude", "lat", "lon", "lng", "anio", "ano", "año",
    }

    numeric_cols = []

    for col in df.columns:
        norm = normalize_for_detection(col)

        if any(token in norm for token in exclude_tokens):
            continue

        converted = clean_numeric(df[col])
        valid_ratio = converted.notna().mean()

        if valid_ratio >= 0.5:
            numeric_cols.append(col)

    return numeric_cols


def add_cycle_column(df: pd.DataFrame, filename: str) -> pd.DataFrame:
    out = df.copy()

    ciclo_col = detect_column(
        out,
        ["ciclo_infys", "ciclo", "periodo", "levantamiento"],
        "ciclo"
    )

    if ciclo_col is not None:
        out["ciclo_infys_int"] = out[ciclo_col].astype(str).str.strip()
    else:
        out["ciclo_infys_int"] = infer_cycle_from_filename(filename)

    out["ciclo_infys_int"] = out["ciclo_infys_int"].replace({"": pd.NA, "nan": pd.NA, "None": pd.NA})

    return out


def summarize_by_key(
    df: pd.DataFrame,
    key_cols: list[str],
    filename: str,
    prefix: str
) -> pd.DataFrame:
    out = df.copy()
    out = add_cycle_column(out, filename)

    group_cols = key_cols + ["ciclo_infys_int"]

    # Evitar que ciclo vacío elimine grupos.
    out["ciclo_infys_int"] = out["ciclo_infys_int"].fillna("sin_ciclo_detectado")

    numeric_cols = choose_numeric_columns(out)

    agg_spec = {
        f"{prefix}_n_registros": (key_cols[0], "size"),
    }

    for col in numeric_cols:
        clean_col = f"__num_{col}"
        out[clean_col] = clean_numeric(out[col])
        safe_name = normalize_for_detection(col)
        agg_spec[f"{prefix}_{safe_name}_mean"] = (clean_col, "mean")
        agg_spec[f"{prefix}_{safe_name}_valid_count"] = (clean_col, "count")

    resumen = (
        out.dropna(subset=[key_cols[0]])
        .groupby(group_cols, as_index=False)
        .agg(**agg_spec)
    )

    resumen = resumen.rename(columns={"ciclo_infys_int": "ciclo_infys"})

    return resumen


def merge_context_tables(base: pd.DataFrame, tables: list[pd.DataFrame], key_cols: list[str]) -> pd.DataFrame:
    contexto = base.copy()

    for table in tables:
        if table.empty:
            continue

        # Para evitar duplicar filas por ciclo, se deja una fila por clave y ciclo.
        # Si una tabla tiene ciclos, se expande el contexto por ciclo solo cuando
        # sea necesario. Para mantener una tabla única, se usa pivot por ciclo.
        if "ciclo_infys" in table.columns:
            value_cols = [col for col in table.columns if col not in key_cols + ["ciclo_infys"]]

            table_pivot_parts = []

            for ciclo, group in table.groupby("ciclo_infys", dropna=False):
                ciclo_safe = normalize_for_detection(str(ciclo))
                renamed = group[key_cols + value_cols].copy()
                renamed = renamed.rename(columns={
                    col: f"{col}_{ciclo_safe}"
                    for col in value_cols
                })
                table_pivot_parts.append(renamed)

            table_wide = table_pivot_parts[0]
            for part in table_pivot_parts[1:]:
                table_wide = table_wide.merge(part, on=key_cols, how="outer")
        else:
            table_wide = table.copy()

        contexto = contexto.merge(table_wide, on=key_cols, how="left")

    return contexto


# =========================================================
# 6) INTEGRACIÓN POR TIPO
# =========================================================

def process_entity_dataset(
    path: Path,
    filename: str,
    catalogo_entidades: pd.DataFrame
) -> tuple[pd.DataFrame, list[dict]]:
    report = []

    df = read_infys_csv(path)
    df_keys = attach_entity_keys(df, catalogo_entidades)

    sin_entidad = int(df_keys["cve_ent"].isna().sum())

    prefix = get_dataset_prefix(filename)

    resumen = summarize_by_key(
        df=df_keys,
        key_cols=["cve_ent"],
        filename=filename,
        prefix=prefix
    )

    report.append(build_report_row(
        filename,
        "registros_leidos",
        len(df),
        "ok" if len(df) > 0 else "warning",
        "Registros leídos desde dataset INFyS limpio."
    ))

    report.append(build_report_row(
        filename,
        "registros_sin_cve_ent",
        sin_entidad,
        "ok" if sin_entidad == 0 else "warning",
        "Registros sin entidad asignada en integración INFyS."
    ))

    report.append(build_report_row(
        filename,
        "entidades_con_contexto",
        resumen["cve_ent"].nunique() if not resumen.empty else 0,
        "ok" if not resumen.empty else "warning",
        "Entidades con resumen estructural INFyS."
    ))

    return resumen, report


def process_municipal_dataset(
    path: Path,
    filename: str,
    catalogo_municipios: pd.DataFrame
) -> tuple[pd.DataFrame, pd.DataFrame, list[dict]]:
    report = []

    df = read_infys_csv(path)
    df_keys = attach_municipal_keys(df, catalogo_municipios)

    sin_municipio = int(df_keys["cvegeo"].isna().sum())

    prefix = get_dataset_prefix(filename)

    resumen_mun = summarize_by_key(
        df=df_keys,
        key_cols=["cvegeo"],
        filename=filename,
        prefix=prefix
    )

    df_ent = df_keys.dropna(subset=["cve_ent"]).copy()

    resumen_ent = summarize_by_key(
        df=df_ent,
        key_cols=["cve_ent"],
        filename=filename,
        prefix=f"{prefix}_derivado_mun"
    )

    report.append(build_report_row(
        filename,
        "registros_leidos",
        len(df),
        "ok" if len(df) > 0 else "warning",
        "Registros leídos desde dataset INFyS limpio."
    ))

    report.append(build_report_row(
        filename,
        "registros_sin_cvegeo",
        sin_municipio,
        "ok" if sin_municipio == 0 else "warning",
        "Registros sin municipio asignado por clave o nombre."
    ))

    report.append(build_report_row(
        filename,
        "municipios_con_contexto",
        resumen_mun["cvegeo"].nunique() if not resumen_mun.empty else 0,
        "ok" if not resumen_mun.empty else "warning",
        "Municipios con resumen estructural INFyS."
    ))

    report.append(build_report_row(
        filename,
        "entidades_derivadas_con_contexto",
        resumen_ent["cve_ent"].nunique() if not resumen_ent.empty else 0,
        "ok" if not resumen_ent.empty else "warning",
        "Entidades con resumen derivado desde registros municipales."
    ))

    return resumen_mun, resumen_ent, report


def process_point_dataset(
    path: Path,
    filename: str,
    municipios_geom: gpd.GeoDataFrame
) -> tuple[pd.DataFrame, pd.DataFrame, list[dict]]:
    report = []

    df = read_infys_csv(path)
    df_keys = attach_municipal_keys_by_coordinates(df, municipios_geom)

    sin_municipio = int(df_keys["cvegeo"].isna().sum())

    prefix = get_dataset_prefix(filename)

    resumen_mun = summarize_by_key(
        df=df_keys,
        key_cols=["cvegeo"],
        filename=filename,
        prefix=prefix
    )

    df_ent = df_keys.dropna(subset=["cve_ent"]).copy()

    resumen_ent = summarize_by_key(
        df=df_ent,
        key_cols=["cve_ent"],
        filename=filename,
        prefix=f"{prefix}_derivado_punto"
    )

    report.append(build_report_row(
        filename,
        "registros_leidos",
        len(df),
        "ok" if len(df) > 0 else "warning",
        "Registros leídos desde dataset INFyS limpio."
    ))

    report.append(build_report_row(
        filename,
        "registros_sin_cvegeo_spatial",
        sin_municipio,
        "ok" if sin_municipio == 0 else "warning",
        "Registros georreferenciados sin municipio asignado por spatial join."
    ))

    report.append(build_report_row(
        filename,
        "municipios_con_contexto_spatial",
        resumen_mun["cvegeo"].nunique() if not resumen_mun.empty else 0,
        "ok" if not resumen_mun.empty else "warning",
        "Municipios con resumen estructural INFyS derivado de puntos."
    ))

    report.append(build_report_row(
        filename,
        "entidades_derivadas_con_contexto_spatial",
        resumen_ent["cve_ent"].nunique() if not resumen_ent.empty else 0,
        "ok" if not resumen_ent.empty else "warning",
        "Entidades con resumen derivado desde puntos INFyS."
    ))

    return resumen_mun, resumen_ent, report


# =========================================================
# 7) VALIDACIÓN GLOBAL
# =========================================================

def build_global_validation(
    municipio_contexto: pd.DataFrame,
    entidad_contexto: pd.DataFrame,
    catalogo_municipios: pd.DataFrame,
    catalogo_entidades: pd.DataFrame,
    report_rows: list[dict]
) -> pd.DataFrame:
    rows = []

    rows.append(build_report_row(
        "GLOBAL",
        "municipio_contexto_registros",
        len(municipio_contexto),
        "ok" if len(municipio_contexto) == len(catalogo_municipios) else "error",
        "Registros generados en integracion_infys_municipio_contexto.csv."
    ))

    rows.append(build_report_row(
        "GLOBAL",
        "municipio_contexto_cvegeo_duplicado",
        int(municipio_contexto["cvegeo"].duplicated().sum()),
        "ok" if int(municipio_contexto["cvegeo"].duplicated().sum()) == 0 else "error",
        "Duplicados por cvegeo en contexto municipal INFyS."
    ))

    rows.append(build_report_row(
        "GLOBAL",
        "entidad_contexto_registros",
        len(entidad_contexto),
        "ok" if len(entidad_contexto) == len(catalogo_entidades) else "error",
        "Registros generados en integracion_infys_entidad_contexto.csv."
    ))

    rows.append(build_report_row(
        "GLOBAL",
        "entidad_contexto_cve_ent_duplicado",
        int(entidad_contexto["cve_ent"].duplicated().sum()),
        "ok" if int(entidad_contexto["cve_ent"].duplicated().sum()) == 0 else "error",
        "Duplicados por cve_ent en contexto estatal INFyS."
    ))

    rows.extend(report_rows)

    return pd.DataFrame(rows)


# =========================================================
# 8) PIPELINE PRINCIPAL
# =========================================================

def main() -> None:
    print("\nIntegración 09 | Contexto estructural INFyS")

    validate_input_exists()

    diagnostico = load_diagnostico()
    catalogo_municipios = load_catalogo_municipios()
    catalogo_entidades = load_catalogo_entidades()
    municipios_geom = load_municipios_geometry(catalogo_municipios)

    print(f"Catálogo municipios: {len(catalogo_municipios):,}")
    print(f"Catálogo entidades: {len(catalogo_entidades):,}")
    print(f"Municipios geometría: {len(municipios_geom):,}")

    municipio_tables = []
    entidad_tables = []
    report_rows = []

    for _, row in diagnostico.iterrows():
        filename = row["archivo"]
        existe = row["existe"]
        recomendacion = row["integracion_recomendada"]

        # Corrección metodológica puntual:
        # Este archivo no tiene cve_ent/cve_mun/municipio útiles, pero sí latitud/longitud.
        # Por lo tanto, debe integrarse por spatial join y no como municipal_textual.
        if filename == "infys_secciones_sitios_2015_2020_limpio.csv":
            recomendacion_original = recomendacion
            recomendacion = "agregar_espacialmente_antes_de_integrar"
        else:
            recomendacion_original = recomendacion

        path = PATH_INFYS_DATASETS / filename

        print(f"\nProcesando INFyS: {filename}")
        print(f"- Recomendación diagnóstico: {recomendacion_original}")

        if recomendacion != recomendacion_original:
            print(f"- Recomendación corregida para integración: {recomendacion}")
            report_rows.append(build_report_row(
                filename,
                "recomendacion_corregida_integracion",
                f"{recomendacion_original} -> {recomendacion}",
                "ok",
                "Corrección metodológica: el dataset no tiene municipio útil, pero sí coordenadas; se integra por spatial join."
            ))

        if existe != "si" or not path.exists():
            report_rows.append(build_report_row(
                filename,
                "archivo_disponible",
                "no",
                "warning",
                "Archivo no disponible; se omite."
            ))
            print("- Omitido: archivo no disponible")
            continue

        if recomendacion in RECOMENDACIONES_OMITIR:
            report_rows.append(build_report_row(
                filename,
                "integracion",
                "omitido",
                "ok",
                "Dataset nacional o no compatible con flujos diarios; no se integra."
            ))
            print("- Omitido metodológicamente")
            continue

        if recomendacion in RECOMENDACIONES_REVISION_MANUAL:
            report_rows.append(build_report_row(
                filename,
                "integracion",
                "revision_manual",
                "warning",
                "Dataset requiere revisión manual; no se integra automáticamente."
            ))
            print("- Enviado a revisión manual")
            continue

        try:
            if recomendacion in RECOMENDACIONES_ENTIDAD:
                resumen_ent, rep = process_entity_dataset(
                    path=path,
                    filename=filename,
                    catalogo_entidades=catalogo_entidades
                )
                entidad_tables.append(resumen_ent)
                report_rows.extend(rep)
                print(f"- Entidad contexto generado: {len(resumen_ent):,} filas intermedias")

            elif recomendacion in RECOMENDACIONES_MUNICIPIO:
                resumen_mun, resumen_ent, rep = process_municipal_dataset(
                    path=path,
                    filename=filename,
                    catalogo_municipios=catalogo_municipios
                )
                municipio_tables.append(resumen_mun)
                entidad_tables.append(resumen_ent)
                report_rows.extend(rep)
                print(f"- Municipio contexto generado: {len(resumen_mun):,} filas intermedias")
                print(f"- Entidad derivada generada: {len(resumen_ent):,} filas intermedias")

            elif recomendacion in RECOMENDACIONES_PUNTO:
                resumen_mun, resumen_ent, rep = process_point_dataset(
                    path=path,
                    filename=filename,
                    municipios_geom=municipios_geom
                )
                municipio_tables.append(resumen_mun)
                entidad_tables.append(resumen_ent)
                report_rows.extend(rep)
                print(f"- Municipio contexto espacial generado: {len(resumen_mun):,} filas intermedias")
                print(f"- Entidad derivada espacial generada: {len(resumen_ent):,} filas intermedias")

            else:
                report_rows.append(build_report_row(
                    filename,
                    "integracion",
                    "recomendacion_no_reconocida",
                    "warning",
                    f"No se reconoce la recomendación '{recomendacion}'; se omite."
                ))
                print("- Omitido: recomendación no reconocida")

        except Exception as exc:
            report_rows.append(build_report_row(
                filename,
                "integracion_error",
                "error",
                "warning",
                f"Error no bloqueante durante integración de dataset: {exc}"
            ))
            print(f"- Error no bloqueante: {exc}")

    print("\nConsolidando contexto municipal INFyS...")
    municipio_base = catalogo_municipios[["cve_ent", "nom_ent", "cve_mun", "nom_mun", "cvegeo"]].copy()
    municipio_contexto = merge_context_tables(
        base=municipio_base,
        tables=municipio_tables,
        key_cols=["cvegeo"]
    )

    print("Consolidando contexto estatal INFyS...")
    entidad_base = catalogo_entidades[["cve_ent", "nom_ent"]].copy()
    entidad_contexto = merge_context_tables(
        base=entidad_base,
        tables=entidad_tables,
        key_cols=["cve_ent"]
    )

    validacion = build_global_validation(
        municipio_contexto=municipio_contexto,
        entidad_contexto=entidad_contexto,
        catalogo_municipios=catalogo_municipios,
        catalogo_entidades=catalogo_entidades,
        report_rows=report_rows
    )

    municipio_contexto.to_csv(
        OUT_MUNICIPIO_CONTEXTO,
        index=False,
        encoding="utf-8-sig"
    )

    entidad_contexto.to_csv(
        OUT_ENTIDAD_CONTEXTO,
        index=False,
        encoding="utf-8-sig"
    )

    validacion.to_csv(
        OUT_VALIDACION,
        index=False,
        encoding="utf-8-sig"
    )

    errores_globales = validacion[
        (validacion["archivo"] == "GLOBAL")
        & (validacion["estatus"] == "error")
    ]

    if not errores_globales.empty:
        print("\nErrores globales de validación:")
        print(errores_globales.to_string(index=False))
        raise ValueError("La integración INFyS terminó con errores globales.")

    print("\nArchivos generados:")
    print(f"- {OUT_MUNICIPIO_CONTEXTO}")
    print(f"- {OUT_ENTIDAD_CONTEXTO}")
    print(f"- {OUT_VALIDACION}")

    print("\nResumen:")
    print(f"- Contexto municipal INFyS: {len(municipio_contexto):,} registros")
    print(f"- Contexto estatal INFyS: {len(entidad_contexto):,} registros")
    print(f"- Columnas contexto municipal: {len(municipio_contexto.columns):,}")
    print(f"- Columnas contexto estatal: {len(entidad_contexto.columns):,}")
    print(f"- Warnings: {(validacion['estatus'] == 'warning').sum()}")
    print(f"- Errores globales: {len(errores_globales):,}")

    print("\nProceso terminado.")


if __name__ == "__main__":
    main()