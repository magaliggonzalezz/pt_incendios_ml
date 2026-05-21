# -*- coding: utf-8 -*-
"""
Integración 07 | Contexto geográfico INEGI

Este script integra capas geográficas limpias de INEGI como contexto estructural
municipal y estatal.

Salidas
-------
1) 04_integration/datasets/integracion_inegi_municipio_contexto.csv
2) 04_integration/datasets/integracion_inegi_entidad_contexto.csv
3) 04_integration/reports/integracion_07_validacion_contexto_geografico_inegi.csv

Objetivo
--------
- Construir contexto geográfico municipal a partir de capas INEGI limpias.
- Construir contexto geográfico estatal derivado del contexto municipal.
- Integrar capas estáticas/semiestáticas sin duplicarlas en bases diarias.
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

PATH_CATALOGO_ENTIDADES = (
    BASE_DIR
    / "04_integration"
    / "datasets"
    / "integracion_catalogo_entidades.csv"
)

OUT_DATASETS_DIR = BASE_DIR / "04_integration" / "datasets"
OUT_REPORTS_DIR = BASE_DIR / "04_integration" / "reports"

OUT_MUNICIPIO_CONTEXTO = OUT_DATASETS_DIR / "integracion_inegi_municipio_contexto.csv"
OUT_ENTIDAD_CONTEXTO = OUT_DATASETS_DIR / "integracion_inegi_entidad_contexto.csv"
OUT_VALIDACION = OUT_REPORTS_DIR / "integracion_07_validacion_contexto_geografico_inegi.csv"

OUT_DATASETS_DIR.mkdir(parents=True, exist_ok=True)
OUT_REPORTS_DIR.mkdir(parents=True, exist_ok=True)

LAYER_ENTIDADES = "entidades_limpio"
LAYER_MUNICIPIOS = "municipios_limpio"

CAPAS_CONTEXTO = {
    "edafologia": "edafologia_limpio",
    "fisiografia": "fisiografia_limpio",
    "uso_suelo_vegetacion": "uso_suelo_vegetacion_limpio",
    "hidrografia": "hidrografia_limpio",
}

# CRS métrico nacional para cálculos de área y longitud.
# Se usa solo para medir geometrías, no para cambiar la estructura espacial final.
# EPSG:6372 corresponde a una proyección Lambert Conformal Conic para México.
METRIC_CRS = "EPSG:6372"


# =========================================================
# 2) UTILIDADES
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

    s = str(value).strip()
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


def build_report_row(indicador: str, valor, estatus: str, observacion: str) -> dict:
    return {
        "indicador": indicador,
        "valor": valor,
        "estatus": estatus,
        "observacion": observacion,
    }


def validate_input_exists() -> None:
    missing = []

    if not PATH_INEGI_GPKG.exists():
        missing.append(f"- GeoPackage INEGI: {PATH_INEGI_GPKG}")

    if not PATH_CATALOGO_MUNICIPIOS.exists():
        missing.append(f"- catálogo municipios: {PATH_CATALOGO_MUNICIPIOS}")

    if not PATH_CATALOGO_ENTIDADES.exists():
        missing.append(f"- catálogo entidades: {PATH_CATALOGO_ENTIDADES}")

    if missing:
        raise FileNotFoundError(
            "Faltan insumos para integrar contexto geográfico INEGI:\n"
            + "\n".join(missing)
        )


def get_geometry_family(gdf: gpd.GeoDataFrame) -> str:
    geom_types = set(gdf.geometry.geom_type.dropna().unique())

    polygon_types = {"Polygon", "MultiPolygon"}
    line_types = {"LineString", "MultiLineString", "LinearRing"}
    point_types = {"Point", "MultiPoint"}

    if geom_types and geom_types.issubset(polygon_types):
        return "polygon"

    if geom_types and geom_types.issubset(line_types):
        return "line"

    if geom_types and geom_types.issubset(point_types):
        return "point"

    return "mixed"


def choose_category_column(gdf: gpd.GeoDataFrame, layer_key: str) -> str | None:
    """
    Elige una columna categórica representativa.

    Se excluyen claves, geometría y columnas técnicas dp_*.
    Si existe una columna típica por capa, se prioriza.
    """
    priority_by_layer = {
        "edafologia": [
            "tipo_suelo",
            "grupo_suelo",
            "clave_suelo",
            "suelo",
            "descripcion",
            "nombre",
            "clase",
        ],
        "fisiografia": [
            "provincia",
            "subprovincia",
            "sistema_topoformas",
            "topoforma",
            "descripcion",
            "nombre",
            "clase",
        ],
        "uso_suelo_vegetacion": [
            "uso_suelo",
            "vegetacion",
            "tipo_vegetacion",
            "uso_vegetacion",
            "descripcion",
            "nombre",
            "clase",
        ],
        "hidrografia": [
            "tipo",
            "nombre",
            "condicion",
            "descripcion",
            "clase",
        ],
    }

    exclude_norm = {
        "geometry",
        "geom",
        "cvegeo",
        "cveent",
        "cvemun",
        "nomgeo",
        "noment",
        "nommun",
        "dpfuente",
        "dpcapa",
        "dpcategoria",
        "dpuso",
    }

    normalized_cols = {
        normalize_for_detection(col): col
        for col in gdf.columns
    }

    for candidate in priority_by_layer.get(layer_key, []):
        key = normalize_for_detection(candidate)
        if key in normalized_cols:
            return normalized_cols[key]

    candidate_cols = []

    for col in gdf.columns:
        norm = normalize_for_detection(col)

        if norm in exclude_norm:
            continue

        if norm.startswith("dp"):
            continue

        if col == gdf.geometry.name:
            continue

        if pd.api.types.is_numeric_dtype(gdf[col]):
            continue

        nunique = gdf[col].nunique(dropna=True)

        if 1 <= nunique <= 500:
            candidate_cols.append((col, nunique))

    if candidate_cols:
        candidate_cols = sorted(candidate_cols, key=lambda x: x[1], reverse=True)
        return candidate_cols[0][0]

    return None


def to_metric_crs(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """
    Reproyecta temporalmente a un CRS métrico para calcular áreas y longitudes.
    No modifica el GeoDataFrame original.
    """
    if gdf.crs is None:
        raise ValueError("No se puede calcular área/longitud porque la geometría no tiene CRS.")

    return gdf.to_crs(METRIC_CRS)


def safe_area_km2(gdf: gpd.GeoDataFrame) -> pd.Series:
    gdf_metric = to_metric_crs(gdf)
    return gdf_metric.geometry.area / 1_000_000


def safe_length_km(gdf: gpd.GeoDataFrame) -> pd.Series:
    gdf_metric = to_metric_crs(gdf)
    return gdf_metric.geometry.length / 1_000


# =========================================================
# 3) CARGA DE CATÁLOGOS Y GEOMETRÍAS BASE
# =========================================================

def load_catalogo_municipios() -> pd.DataFrame:
    cat = pd.read_csv(PATH_CATALOGO_MUNICIPIOS, encoding="utf-8-sig", dtype=str)

    required = {"cve_ent", "nom_ent", "cve_mun", "nom_mun", "cvegeo"}
    missing = required - set(cat.columns)

    if missing:
        raise ValueError(f"Faltan columnas en catálogo municipal: {missing}")

    cat["cve_ent"] = normalize_cve_ent(cat["cve_ent"])
    cat["cve_mun"] = normalize_cve_mun(cat["cve_mun"])
    cat["cvegeo"] = normalize_cvegeo(cat["cvegeo"])

    cat = cat[["cve_ent", "nom_ent", "cve_mun", "nom_mun", "cvegeo"]].copy()

    if cat["cvegeo"].duplicated().any():
        raise ValueError("El catálogo municipal tiene cvegeo duplicadas.")

    return cat


def load_catalogo_entidades() -> pd.DataFrame:
    cat = pd.read_csv(PATH_CATALOGO_ENTIDADES, encoding="utf-8-sig", dtype=str)

    required = {"cve_ent", "nom_ent"}
    missing = required - set(cat.columns)

    if missing:
        raise ValueError(f"Faltan columnas en catálogo de entidades: {missing}")

    cat["cve_ent"] = normalize_cve_ent(cat["cve_ent"])
    cat = cat[["cve_ent", "nom_ent"]].drop_duplicates().copy()

    if cat["cve_ent"].duplicated().any():
        raise ValueError("El catálogo de entidades tiene cve_ent duplicadas.")

    return cat


def load_municipios_geometry(catalogo_municipios: pd.DataFrame) -> gpd.GeoDataFrame:
    municipios = gpd.read_file(PATH_INEGI_GPKG, layer=LAYER_MUNICIPIOS)

    if municipios.crs is None:
        raise ValueError("La capa municipios_limpio no tiene CRS definido.")

    cvegeo_col = detect_column(
        municipios,
        ["cvegeo", "clavegeo", "clave_geografica"],
        "cvegeo municipal"
    )

    municipios["cvegeo"] = normalize_cvegeo(municipios[cvegeo_col])

    municipios = municipios[["cvegeo", "geometry"]].copy()
    municipios = municipios.merge(
        catalogo_municipios,
        on="cvegeo",
        how="left"
    )

    municipios = municipios[municipios.geometry.notna()].copy()
    municipios = municipios[~municipios.geometry.is_empty].copy()

    if municipios["cvegeo"].duplicated().any():
        raise ValueError("La geometría municipal tiene cvegeo duplicadas.")

    municipios["municipio_area_km2"] = safe_area_km2(municipios)

    return municipios


# =========================================================
# 4) INTEGRACIÓN POR CAPA
# =========================================================

def integrate_polygon_layer(
    municipios: gpd.GeoDataFrame,
    layer_gdf: gpd.GeoDataFrame,
    layer_key: str
) -> tuple[pd.DataFrame, dict]:
    category_col = choose_category_column(layer_gdf, layer_key)

    if category_col is None:
        return pd.DataFrame({"cvegeo": municipios["cvegeo"]}), {
            "categoria_columna": None,
            "observacion": "No se detectó columna categórica útil; solo se conserva estructura base.",
            "estatus": "warning",
        }

    capa = layer_gdf[[category_col, "geometry"]].copy()
    capa = capa[capa.geometry.notna()].copy()
    capa = capa[~capa.geometry.is_empty].copy()
    capa["categoria_contexto"] = capa[category_col].map(normalize_text)

    if capa.crs != municipios.crs:
        capa = capa.to_crs(municipios.crs)

    inter = gpd.overlay(
        municipios[["cvegeo", "geometry", "municipio_area_km2"]],
        capa[["categoria_contexto", "geometry"]],
        how="intersection",
        keep_geom_type=False
    )

    if inter.empty:
        return pd.DataFrame({"cvegeo": municipios["cvegeo"]}), {
            "categoria_columna": category_col,
            "observacion": "La intersección espacial quedó vacía.",
            "estatus": "warning",
        }

    inter["area_interseccion_km2"] = safe_area_km2(inter)

    resumen_cat = (
        inter.groupby(["cvegeo", "categoria_contexto"], as_index=False)
        .agg(area_km2=("area_interseccion_km2", "sum"))
    )

    resumen_total = (
        resumen_cat.groupby("cvegeo", as_index=False)
        .agg(
            **{
                f"inegi_{layer_key}_area_total_km2": ("area_km2", "sum"),
                f"inegi_{layer_key}_n_clases": ("categoria_contexto", "nunique"),
            }
        )
    )

    dominante = resumen_cat.sort_values(
        ["cvegeo", "area_km2"],
        ascending=[True, False]
    ).drop_duplicates(subset=["cvegeo"], keep="first")

    dominante = dominante.rename(columns={
        "categoria_contexto": f"inegi_{layer_key}_dominante",
        "area_km2": f"inegi_{layer_key}_dominante_area_km2",
    })

    out = resumen_total.merge(
        dominante[[
            "cvegeo",
            f"inegi_{layer_key}_dominante",
            f"inegi_{layer_key}_dominante_area_km2",
        ]],
        on="cvegeo",
        how="left"
    )

    out = out.merge(
        municipios[["cvegeo", "municipio_area_km2"]],
        on="cvegeo",
        how="left"
    )

    out[f"inegi_{layer_key}_dominante_prop_area"] = (
        out[f"inegi_{layer_key}_dominante_area_km2"]
        / out["municipio_area_km2"].replace(0, pd.NA)
    )

    out = out.drop(columns=["municipio_area_km2"], errors="ignore")

    return out, {
        "categoria_columna": category_col,
        "observacion": f"Capa poligonal integrada por área. Columna categórica usada: {category_col}.",
        "estatus": "ok",
    }


def integrate_line_layer(
    municipios: gpd.GeoDataFrame,
    layer_gdf: gpd.GeoDataFrame,
    layer_key: str
) -> tuple[pd.DataFrame, dict]:
    category_col = choose_category_column(layer_gdf, layer_key)

    cols = ["geometry"]
    if category_col is not None:
        cols.append(category_col)

    capa = layer_gdf[cols].copy()
    capa = capa[capa.geometry.notna()].copy()
    capa = capa[~capa.geometry.is_empty].copy()

    if capa.crs != municipios.crs:
        capa = capa.to_crs(municipios.crs)

    inter = gpd.overlay(
        municipios[["cvegeo", "geometry", "municipio_area_km2"]],
        capa,
        how="intersection",
        keep_geom_type=False
    )

    if inter.empty:
        return pd.DataFrame({"cvegeo": municipios["cvegeo"]}), {
            "categoria_columna": category_col,
            "observacion": "La intersección lineal quedó vacía.",
            "estatus": "warning",
        }

    inter["longitud_km"] = safe_length_km(inter)

    agg_dict = {
        f"inegi_{layer_key}_longitud_total_km": ("longitud_km", "sum"),
        f"inegi_{layer_key}_n_segmentos_intersectados": ("longitud_km", "size"),
    }

    resumen = inter.groupby("cvegeo", as_index=False).agg(**agg_dict)

    resumen = resumen.merge(
        municipios[["cvegeo", "municipio_area_km2"]],
        on="cvegeo",
        how="left"
    )

    resumen[f"inegi_{layer_key}_longitud_km_por_km2"] = (
        resumen[f"inegi_{layer_key}_longitud_total_km"]
        / resumen["municipio_area_km2"].replace(0, pd.NA)
    )

    resumen = resumen.drop(columns=["municipio_area_km2"], errors="ignore")

    if category_col is not None:
        inter["categoria_contexto"] = inter[category_col].map(normalize_text)

        resumen_cat = (
            inter.groupby(["cvegeo", "categoria_contexto"], as_index=False)
            .agg(longitud_km=("longitud_km", "sum"))
        )

        dominante = resumen_cat.sort_values(
            ["cvegeo", "longitud_km"],
            ascending=[True, False]
        ).drop_duplicates(subset=["cvegeo"], keep="first")

        dominante = dominante.rename(columns={
            "categoria_contexto": f"inegi_{layer_key}_tipo_dominante",
            "longitud_km": f"inegi_{layer_key}_tipo_dominante_longitud_km",
        })

        resumen = resumen.merge(
            dominante[[
                "cvegeo",
                f"inegi_{layer_key}_tipo_dominante",
                f"inegi_{layer_key}_tipo_dominante_longitud_km",
            ]],
            on="cvegeo",
            how="left"
        )

    return resumen, {
        "categoria_columna": category_col,
        "observacion": (
            f"Capa lineal integrada por longitud. "
            f"Columna categórica usada: {category_col}."
        ),
        "estatus": "ok",
    }


def integrate_point_layer(
    municipios: gpd.GeoDataFrame,
    layer_gdf: gpd.GeoDataFrame,
    layer_key: str
) -> tuple[pd.DataFrame, dict]:
    capa = layer_gdf.copy()
    capa = capa[capa.geometry.notna()].copy()
    capa = capa[~capa.geometry.is_empty].copy()

    if capa.crs != municipios.crs:
        capa = capa.to_crs(municipios.crs)

    joined = gpd.sjoin(
        capa,
        municipios[["cvegeo", "geometry"]],
        how="left",
        predicate="within"
    )

    resumen = (
        joined.dropna(subset=["cvegeo"])
        .groupby("cvegeo", as_index=False)
        .size()
        .rename(columns={"size": f"inegi_{layer_key}_n_puntos"})
    )

    return resumen, {
        "categoria_columna": None,
        "observacion": "Capa puntual integrada por conteo de puntos dentro del municipio.",
        "estatus": "ok",
    }


def integrate_context_layers(municipios: gpd.GeoDataFrame) -> tuple[pd.DataFrame, list[dict]]:
    contexto = municipios[
        ["cve_ent", "nom_ent", "cve_mun", "nom_mun", "cvegeo", "municipio_area_km2"]
    ].copy()

    report_rows = []

    for layer_key, layer_name in CAPAS_CONTEXTO.items():
        print(f"\nIntegrando capa INEGI: {layer_name}")

        try:
            layer_gdf = gpd.read_file(PATH_INEGI_GPKG, layer=layer_name)
        except Exception as exc:
            report_rows.append(build_report_row(
                f"capa_{layer_key}",
                "no_leida",
                "warning",
                f"No se pudo leer la capa {layer_name}: {exc}"
            ))
            continue

        if layer_gdf.empty:
            report_rows.append(build_report_row(
                f"capa_{layer_key}",
                0,
                "warning",
                f"La capa {layer_name} está vacía."
            ))
            continue

        if layer_gdf.crs is None:
            report_rows.append(build_report_row(
                f"capa_{layer_key}",
                len(layer_gdf),
                "warning",
                f"La capa {layer_name} no tiene CRS definido; se omite."
            ))
            continue

        geom_family = get_geometry_family(layer_gdf)

        print(f"- Registros capa: {len(layer_gdf):,}")
        print(f"- Tipo geometría detectado: {geom_family}")

        if geom_family == "polygon":
            capa_contexto, meta = integrate_polygon_layer(municipios, layer_gdf, layer_key)
        elif geom_family == "line":
            capa_contexto, meta = integrate_line_layer(municipios, layer_gdf, layer_key)
        elif geom_family == "point":
            capa_contexto, meta = integrate_point_layer(municipios, layer_gdf, layer_key)
        else:
            report_rows.append(build_report_row(
                f"capa_{layer_key}",
                len(layer_gdf),
                "warning",
                f"La capa {layer_name} tiene geometrías mixtas; no se integró automáticamente."
            ))
            continue

        contexto = contexto.merge(
            capa_contexto,
            on="cvegeo",
            how="left"
        )

        report_rows.append(build_report_row(
            f"capa_{layer_key}",
            len(layer_gdf),
            meta["estatus"],
            f"{meta['observacion']} Geometría: {geom_family}."
        ))

        municipios_con_valor = int(capa_contexto["cvegeo"].nunique()) if "cvegeo" in capa_contexto.columns else 0

        report_rows.append(build_report_row(
            f"municipios_con_contexto_{layer_key}",
            municipios_con_valor,
            "ok" if municipios_con_valor > 0 else "warning",
            f"Municipios con al menos un valor integrado para {layer_key}."
        ))

    return contexto, report_rows


# =========================================================
# 5) CONTEXTO ENTIDAD
# =========================================================

def build_entidad_contexto(
    municipio_contexto: pd.DataFrame,
    catalogo_entidades: pd.DataFrame
) -> pd.DataFrame:
    df = municipio_contexto.copy()

    rows = []

    for cve_ent, group in df.groupby("cve_ent", dropna=False):
        row = {
            "cve_ent": cve_ent,
            "n_municipios_contexto": group["cvegeo"].nunique(),
            "entidad_area_km2_sum": pd.to_numeric(
                group["municipio_area_km2"],
                errors="coerce"
            ).sum(min_count=1),
        }

        # Para columnas dominantes municipales, calculamos dominante estatal
        # como la categoría con mayor área dominante municipal acumulada.
        for col in df.columns:
            if col.endswith("_dominante") and col.startswith("inegi_"):
                prefix = col.replace("_dominante", "")
                area_col = f"{prefix}_dominante_area_km2"

                if area_col in df.columns:
                    temp = group[[col, area_col]].dropna(subset=[col]).copy()
                    temp[area_col] = pd.to_numeric(temp[area_col], errors="coerce")

                    if not temp.empty:
                        agg = (
                            temp.groupby(col, as_index=False)
                            .agg(area_km2=(area_col, "sum"))
                            .sort_values("area_km2", ascending=False)
                        )

                        row[f"{prefix}_dominante_entidad"] = agg.iloc[0][col]
                        row[f"{prefix}_dominante_entidad_area_km2"] = agg.iloc[0]["area_km2"]
                    else:
                        row[f"{prefix}_dominante_entidad"] = pd.NA
                        row[f"{prefix}_dominante_entidad_area_km2"] = pd.NA

            if col.endswith("_tipo_dominante") and col.startswith("inegi_"):
                prefix = col.replace("_tipo_dominante", "")
                length_col = f"{prefix}_tipo_dominante_longitud_km"

                if length_col in df.columns:
                    temp = group[[col, length_col]].dropna(subset=[col]).copy()
                    temp[length_col] = pd.to_numeric(temp[length_col], errors="coerce")

                    if not temp.empty:
                        agg = (
                            temp.groupby(col, as_index=False)
                            .agg(longitud_km=(length_col, "sum"))
                            .sort_values("longitud_km", ascending=False)
                        )

                        row[f"{prefix}_tipo_dominante_entidad"] = agg.iloc[0][col]
                        row[f"{prefix}_tipo_dominante_entidad_longitud_km"] = agg.iloc[0]["longitud_km"]
                    else:
                        row[f"{prefix}_tipo_dominante_entidad"] = pd.NA
                        row[f"{prefix}_tipo_dominante_entidad_longitud_km"] = pd.NA

        # Sumar métricas numéricas estructurales.
        numeric_sum_suffixes = [
            "_area_total_km2",
            "_longitud_total_km",
            "_n_segmentos_intersectados",
            "_n_puntos",
        ]

        for col in df.columns:
            if col.startswith("inegi_") and any(col.endswith(suffix) for suffix in numeric_sum_suffixes):
                row[col] = pd.to_numeric(group[col], errors="coerce").sum(min_count=1)

        rows.append(row)

    entidad_contexto = pd.DataFrame(rows)

    entidad_contexto = entidad_contexto.merge(
        catalogo_entidades,
        on="cve_ent",
        how="left"
    )

    priority = [
        "cve_ent",
        "nom_ent",
        "n_municipios_contexto",
        "entidad_area_km2_sum",
    ]

    ordered = [col for col in priority if col in entidad_contexto.columns]
    rest = [col for col in entidad_contexto.columns if col not in ordered]

    entidad_contexto = entidad_contexto[ordered + rest].copy()
    entidad_contexto = entidad_contexto.sort_values("cve_ent").reset_index(drop=True)

    return entidad_contexto


# =========================================================
# 6) VALIDACIÓN
# =========================================================

def build_validation_report(
    catalogo_municipios: pd.DataFrame,
    catalogo_entidades: pd.DataFrame,
    municipios_geom: gpd.GeoDataFrame,
    municipio_contexto: pd.DataFrame,
    entidad_contexto: pd.DataFrame,
    layer_rows: list[dict]
) -> pd.DataFrame:
    rows = []

    rows.append(build_report_row(
        "catalogo_municipios_registros",
        len(catalogo_municipios),
        "ok" if len(catalogo_municipios) == 2478 else "warning",
        "Municipios en catálogo de integración."
    ))

    rows.append(build_report_row(
        "catalogo_entidades_registros",
        len(catalogo_entidades),
        "ok" if len(catalogo_entidades) == 32 else "warning",
        "Entidades en catálogo de integración."
    ))

    rows.append(build_report_row(
        "municipios_geometria_registros",
        len(municipios_geom),
        "ok" if len(municipios_geom) == len(catalogo_municipios) else "warning",
        "Municipios con geometría cargada desde INEGI."
    ))

    rows.append(build_report_row(
        "crs_metric_calculos_area_longitud",
        METRIC_CRS,
        "ok",
        "CRS métrico usado para calcular áreas y longitudes en contexto INEGI."
    ))

    rows.append(build_report_row(
        "municipio_contexto_registros",
        len(municipio_contexto),
        "ok" if len(municipio_contexto) == len(catalogo_municipios) else "error",
        "Registros generados en integracion_inegi_municipio_contexto.csv."
    ))

    rows.append(build_report_row(
        "municipio_contexto_cvegeo_duplicado",
        int(municipio_contexto["cvegeo"].duplicated().sum()),
        "ok" if int(municipio_contexto["cvegeo"].duplicated().sum()) == 0 else "error",
        "Duplicados por cvegeo en contexto municipal."
    ))

    rows.append(build_report_row(
        "municipio_contexto_cvegeo_sin_catalogo",
        int(municipio_contexto["nom_mun"].isna().sum()),
        "ok" if int(municipio_contexto["nom_mun"].isna().sum()) == 0 else "error",
        "Municipios de contexto sin correspondencia de catálogo."
    ))

    rows.append(build_report_row(
        "entidad_contexto_registros",
        len(entidad_contexto),
        "ok" if len(entidad_contexto) == len(catalogo_entidades) else "error",
        "Registros generados en integracion_inegi_entidad_contexto.csv."
    ))

    rows.append(build_report_row(
        "entidad_contexto_cve_ent_duplicado",
        int(entidad_contexto["cve_ent"].duplicated().sum()),
        "ok" if int(entidad_contexto["cve_ent"].duplicated().sum()) == 0 else "error",
        "Duplicados por cve_ent en contexto estatal."
    ))

    rows.extend(layer_rows)

    return pd.DataFrame(rows)


# =========================================================
# 7) PIPELINE PRINCIPAL
# =========================================================

def main() -> None:
    print("\nIntegración 07 | Contexto geográfico INEGI")

    validate_input_exists()

    print("Cargando catálogos...")
    catalogo_municipios = load_catalogo_municipios()
    catalogo_entidades = load_catalogo_entidades()

    print(f"Catálogo municipios: {len(catalogo_municipios):,}")
    print(f"Catálogo entidades: {len(catalogo_entidades):,}")

    print("\nCargando geometría municipal...")
    municipios_geom = load_municipios_geometry(catalogo_municipios)
    print(f"Municipios con geometría: {len(municipios_geom):,}")
    print(f"CRS municipal: {municipios_geom.crs}")

    municipio_contexto, layer_rows = integrate_context_layers(municipios_geom)

    print("\nConstruyendo contexto estatal derivado...")
    entidad_contexto = build_entidad_contexto(
        municipio_contexto=municipio_contexto,
        catalogo_entidades=catalogo_entidades
    )

    validacion = build_validation_report(
        catalogo_municipios=catalogo_municipios,
        catalogo_entidades=catalogo_entidades,
        municipios_geom=municipios_geom,
        municipio_contexto=municipio_contexto,
        entidad_contexto=entidad_contexto,
        layer_rows=layer_rows
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

    errores = validacion[validacion["estatus"] == "error"]

    if not errores.empty:
        print("\nErrores de validación:")
        print(errores.to_string(index=False))
        raise ValueError("La integración de contexto geográfico INEGI terminó con errores.")

    print("\nArchivos generados:")
    print(f"- {OUT_MUNICIPIO_CONTEXTO}")
    print(f"- {OUT_ENTIDAD_CONTEXTO}")
    print(f"- {OUT_VALIDACION}")

    print("\nResumen:")
    print(f"- Contexto municipal INEGI: {len(municipio_contexto):,} registros")
    print(f"- Contexto estatal INEGI: {len(entidad_contexto):,} registros")
    print(f"- Warnings: {(validacion['estatus'] == 'warning').sum()}")
    print(f"- Errores: {(validacion['estatus'] == 'error').sum()}")

    print("\nProceso terminado.")


if __name__ == "__main__":
    main()