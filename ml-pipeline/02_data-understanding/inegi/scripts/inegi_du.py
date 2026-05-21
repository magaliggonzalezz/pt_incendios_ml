# -*- coding: utf-8 -*-
"""
INEGI | Data Understanding (DU) técnico + catálogo metodológico

Salidas
-------
1) inegi_du_report.csv
   Reporte técnico detallado:
   - archivo
   - campo
   - raster_band
   - resumen_global
   - hallazgos_globales

2) inegi_du_catalogo_metodologico.csv
   Catálogo compacto por archivo/capa:
   - producto inferido
   - categoría metodológica
   - utilidad para ML
   - utilidad para visualización
   - fase CRISP-DM donde debe usarse
   - prioridad
   - decisión DU
   - temporalidad
   - problemas detectados

3) inegi_du_resumen_ejecutivo.csv
   Resumen agregado por categoría, decisión y fase.

Qué evalúa
----------
- Inventario de archivos geoespaciales
- Formato observado
- Tipo de dato: vector / raster
- Geometría
- CRS / EPSG
- Registros
- Campos
- Geometrías vacías e inválidas
- Cobertura espacial básica
- Perfil atributivo por campo
- Estadísticos básicos por banda raster
- Sidecars de shapefile (.shp, .dbf, .shx, .prj, .cpg)
- Clasificación metodológica de utilidad para el proyecto
"""

from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import geopandas as gpd
import numpy as np
import pandas as pd
import rasterio


# =========================================================
# 1) CONFIGURACIÓN
# =========================================================

BASE_DIR = Path(r"C:\Users\Hp\OneDrive\Documentos\PT_Analisis")

# Ajusta solo si tu carpeta real se llama distinto.
ROOT_CANDIDATES = [
    BASE_DIR / "01_raw-data" / "inegi",
    BASE_DIR / "raw-data" / "inegi",
    BASE_DIR / "01_raw_data" / "inegi",
]

OUT_CANDIDATES = [
    BASE_DIR / "02_data-understanding" / "inegi" / "reports",
    BASE_DIR / "du" / "inegi",
    BASE_DIR / "02_data_understanding" / "inegi" / "reports",
]

VECTOR_EXTENSIONS = {".shp", ".gpkg", ".geojson"}
RASTER_EXTENSIONS = {".tif", ".tiff"}

TOP_N = 10
MAX_UNIQUES_FOR_FULL_TOP = 1000

OUT_REPORT_NAME = "inegi_du_report.csv"
OUT_CATALOG_NAME = "inegi_du_catalogo_metodologico.csv"
OUT_SUMMARY_NAME = "inegi_du_resumen_ejecutivo.csv"


def first_existing_path(candidates: List[Path], default: Path, create: bool = False) -> Path:
    for p in candidates:
        if p.exists():
            return p
    if create:
        default.mkdir(parents=True, exist_ok=True)
    return default


ROOT_DIR = first_existing_path(ROOT_CANDIDATES, ROOT_CANDIDATES[0], create=False)
OUT_DIR = first_existing_path(OUT_CANDIDATES, OUT_CANDIDATES[0], create=True)

OUT_REPORT = OUT_DIR / OUT_REPORT_NAME
OUT_CATALOG = OUT_DIR / OUT_CATALOG_NAME
OUT_SUMMARY = OUT_DIR / OUT_SUMMARY_NAME


# =========================================================
# 2) UTILIDADES GENERALES
# =========================================================

def safe_json(value) -> str:
    if value is None:
        return ""
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def safe_pct(num: int, den: int) -> float:
    return round((num / den) * 100.0, 4) if den else 0.0


def normalize_value(v):
    if pd.isna(v):
        return None
    if isinstance(v, str):
        s = v.strip()
        return s if s != "" else None
    return v


def value_to_key(v):
    if v is None:
        return None
    if isinstance(v, (list, dict, tuple, set)):
        return str(v)
    return v


def safe_bounds(bounds) -> Dict[str, Optional[float]]:
    if bounds is None:
        return {"minx": None, "miny": None, "maxx": None, "maxy": None}

    try:
        return {
            "minx": round(float(bounds[0]), 6),
            "miny": round(float(bounds[1]), 6),
            "maxx": round(float(bounds[2]), 6),
            "maxy": round(float(bounds[3]), 6),
        }
    except Exception:
        return {"minx": None, "miny": None, "maxx": None, "maxy": None}


def geometry_type_summary(gdf: gpd.GeoDataFrame) -> Dict[str, int]:
    counter = Counter()

    if "geometry" not in gdf.columns:
        return {}

    for geom in gdf.geometry:
        if geom is None:
            counter["None"] += 1
        else:
            try:
                counter[geom.geom_type] += 1
            except Exception:
                counter["Unknown"] += 1

    return dict(counter)


def infer_observed_dtype(series: pd.Series) -> str:
    non_null = series.dropna()
    if non_null.empty:
        return "all_null"

    sample = non_null.iloc[:200]
    py_types = Counter(type(x).__name__ for x in sample)

    if len(py_types) == 1:
        return next(iter(py_types.keys()))

    return "mixed:" + ",".join(f"{k}={v}" for k, v in py_types.items())


def thematic_candidate_fields(columns: List[str]) -> List[str]:
    hints = [
        "clase", "tipo", "uso", "veg", "veget", "cobertura", "region", "región",
        "prov", "fisio", "suelo", "edaf", "nombre", "nom", "desc", "serie",
        "clave", "clima", "hidro", "corriente", "cuenca", "subcuenca", "altitud"
    ]

    out = []
    for c in columns:
        low = c.lower()
        if any(h in low for h in hints):
            out.append(c)

    return sorted(set(out))


def identifier_candidate_fields(columns: List[str]) -> List[str]:
    hints = ["id", "cve", "cv_", "clave", "folio", "gid", "objectid", "oid", "nomgeo"]

    out = []
    for c in columns:
        low = c.lower()
        if any(h in low for h in hints):
            out.append(c)

    return sorted(set(out))


def top_values(series: pd.Series, n: int = TOP_N):
    values = [value_to_key(normalize_value(v)) for v in series]
    values = [v for v in values if v is not None]
    counter = Counter(values)
    return counter.most_common(n)


def profile_series(series: pd.Series) -> Dict[str, object]:
    total = int(len(series))
    normalized = series.map(normalize_value)

    null_count = int(normalized.isna().sum())
    non_null = normalized.dropna()
    unique_count = int(non_null.nunique(dropna=True))

    observed_dtype = infer_observed_dtype(series)

    max_text_len = None
    min_text_len = None
    if not non_null.empty:
        text_lengths = [len(str(x)) for x in non_null if isinstance(x, str)]
        if text_lengths:
            max_text_len = int(max(text_lengths))
            min_text_len = int(min(text_lengths))

    numeric_min = None
    numeric_max = None
    numeric_mean = None

    try:
        numeric = pd.to_numeric(non_null, errors="coerce").dropna()
        if not numeric.empty:
            numeric_min = float(numeric.min())
            numeric_max = float(numeric.max())
            numeric_mean = float(numeric.mean())
    except Exception:
        pass

    tops = []
    if unique_count <= MAX_UNIQUES_FOR_FULL_TOP or observed_dtype in {
        "str", "int", "float", "int64", "float64", "object"
    }:
        tops = top_values(series, TOP_N)

    return {
        "observed_dtype": observed_dtype,
        "null_count": null_count,
        "null_pct": safe_pct(null_count, total),
        "unique_count": unique_count,
        "top_values": tops,
        "min_text_len": min_text_len,
        "max_text_len": max_text_len,
        "numeric_min": numeric_min,
        "numeric_max": numeric_max,
        "numeric_mean": numeric_mean,
    }


def inspect_shapefile_sidecars(path: Path) -> Dict[str, object]:
    """
    Revisa sidecars de shapefile.
    DU: solo diagnostica disponibilidad de archivos asociados.

    Criterio:
    - .dbf y .shx son críticos para integridad del shapefile.
    - .prj es crítico para conocer CRS.
    - .cpg ayuda a codificación, pero no es bloqueante.
    """
    if path.suffix.lower() != ".shp":
        return {
            "shp_tiene_dbf": None,
            "shp_tiene_shx": None,
            "shp_tiene_prj": None,
            "shp_tiene_cpg": None,
            "shp_sidecars_faltantes": "",
            "shp_sidecars_criticos_faltantes": "",
            "shp_sidecars_no_criticos_faltantes": "",
        }

    sidecars = {
        ".dbf": path.with_suffix(".dbf").exists(),
        ".shx": path.with_suffix(".shx").exists(),
        ".prj": path.with_suffix(".prj").exists(),
        ".cpg": path.with_suffix(".cpg").exists(),
    }

    faltantes = [ext for ext, exists in sidecars.items() if not exists]
    criticos_faltantes = [ext for ext in [".dbf", ".shx", ".prj"] if not sidecars[ext]]
    no_criticos_faltantes = [ext for ext in [".cpg"] if not sidecars[ext]]

    return {
        "shp_tiene_dbf": sidecars[".dbf"],
        "shp_tiene_shx": sidecars[".shx"],
        "shp_tiene_prj": sidecars[".prj"],
        "shp_tiene_cpg": sidecars[".cpg"],
        "shp_sidecars_faltantes": ";".join(faltantes),
        "shp_sidecars_criticos_faltantes": ";".join(criticos_faltantes),
        "shp_sidecars_no_criticos_faltantes": ";".join(no_criticos_faltantes),
    }


def base_file_row(path: Path, tipo_dato: str) -> Dict[str, object]:
    sidecars = inspect_shapefile_sidecars(path)

    return {
        "tipo_fila": "archivo",
        "archivo": path.name,
        "ruta": str(path),
        "carpeta_relativa": str(path.parent.relative_to(ROOT_DIR)) if ROOT_DIR in path.parents else str(path.parent),
        "formato": path.suffix.lower().replace(".", "").upper(),
        "tipo_dato": tipo_dato,
        "registros": 0 if tipo_dato == "vector" else None,
        "num_campos": 0,
        "campos_presentes": [],
        "campos_tematicos_candidatos": [],
        "campos_identificadores_candidatos": [],
        "crs": None,
        "epsg": None,
        "geom_tipos": {},
        "geom_vacias": None,
        "geom_invalidas": None,
        "bbox": {},
        "raster_width": None,
        "raster_height": None,
        "raster_res_x": None,
        "raster_res_y": None,
        "raster_nodata": None,
        "raster_dtype": None,
        "raster_count": None,
        "campo_nombre": None,
        "campo_dtype_observado": None,
        "campo_nulos": None,
        "campo_nulos_pct": None,
        "campo_unicos": None,
        "campo_top_valores": None,
        "campo_min_text_len": None,
        "campo_max_text_len": None,
        "campo_numeric_min": None,
        "campo_numeric_max": None,
        "campo_numeric_mean": None,
        "raster_band": None,
        "raster_valid_pixels": None,
        "raster_nodata_pixels": None,
        "raster_min": None,
        "raster_max": None,
        "raster_mean": None,
        "shp_tiene_dbf": sidecars["shp_tiene_dbf"],
        "shp_tiene_shx": sidecars["shp_tiene_shx"],
        "shp_tiene_prj": sidecars["shp_tiene_prj"],
        "shp_tiene_cpg": sidecars["shp_tiene_cpg"],
        "shp_sidecars_faltantes": sidecars["shp_sidecars_faltantes"],
        "shp_sidecars_criticos_faltantes": sidecars.get("shp_sidecars_criticos_faltantes", ""),
        "shp_sidecars_no_criticos_faltantes": sidecars.get("shp_sidecars_no_criticos_faltantes", ""),
        "observaciones": "",
    }


# =========================================================
# 3) ANÁLISIS VECTORIAL
# =========================================================

def analyze_vector_file(path: Path) -> Tuple[Dict[str, object], List[Dict[str, object]]]:
    file_row = base_file_row(path, "vector")
    field_rows = []

    try:
        gdf = gpd.read_file(path)
    except Exception as e:
        file_row["observaciones"] = f"Error de lectura: {e}"
        return file_row, field_rows

    file_row["registros"] = int(len(gdf))

    fields = [c for c in gdf.columns if c != "geometry"]
    file_row["campos_presentes"] = fields
    file_row["num_campos"] = len(fields)
    file_row["campos_tematicos_candidatos"] = thematic_candidate_fields(fields)
    file_row["campos_identificadores_candidatos"] = identifier_candidate_fields(fields)

    if gdf.crs is not None:
        file_row["crs"] = str(gdf.crs)
        try:
            file_row["epsg"] = gdf.crs.to_epsg()
        except Exception:
            file_row["epsg"] = None

    if "geometry" in gdf.columns:
        file_row["geom_tipos"] = geometry_type_summary(gdf)

        try:
            file_row["geom_vacias"] = int(gdf.geometry.is_empty.sum())
        except Exception:
            file_row["geom_vacias"] = None

        try:
            file_row["geom_invalidas"] = int((~gdf.geometry.is_valid).sum())
        except Exception:
            file_row["geom_invalidas"] = None

        try:
            file_row["bbox"] = safe_bounds(gdf.total_bounds)
        except Exception:
            file_row["bbox"] = {}

    for col in fields:
        prof = profile_series(gdf[col])
        sidecars = inspect_shapefile_sidecars(path)

        field_rows.append({
            "tipo_fila": "campo",
            "archivo": path.name,
            "ruta": str(path),
            "carpeta_relativa": file_row["carpeta_relativa"],
            "formato": path.suffix.lower().replace(".", "").upper(),
            "tipo_dato": "vector",
            "registros": int(len(gdf)),
            "num_campos": len(fields),
            "campos_presentes": None,
            "campos_tematicos_candidatos": None,
            "campos_identificadores_candidatos": None,
            "crs": file_row["crs"],
            "epsg": file_row["epsg"],
            "geom_tipos": None,
            "geom_vacias": None,
            "geom_invalidas": None,
            "bbox": None,
            "raster_width": None,
            "raster_height": None,
            "raster_res_x": None,
            "raster_res_y": None,
            "raster_nodata": None,
            "raster_dtype": None,
            "raster_count": None,
            "campo_nombre": col,
            "campo_dtype_observado": prof["observed_dtype"],
            "campo_nulos": prof["null_count"],
            "campo_nulos_pct": prof["null_pct"],
            "campo_unicos": prof["unique_count"],
            "campo_top_valores": prof["top_values"],
            "campo_min_text_len": prof["min_text_len"],
            "campo_max_text_len": prof["max_text_len"],
            "campo_numeric_min": prof["numeric_min"],
            "campo_numeric_max": prof["numeric_max"],
            "campo_numeric_mean": prof["numeric_mean"],
            "raster_band": None,
            "raster_valid_pixels": None,
            "raster_nodata_pixels": None,
            "raster_min": None,
            "raster_max": None,
            "raster_mean": None,
            "shp_tiene_dbf": sidecars["shp_tiene_dbf"],
            "shp_tiene_shx": sidecars["shp_tiene_shx"],
            "shp_tiene_prj": sidecars["shp_tiene_prj"],
            "shp_tiene_cpg": sidecars["shp_tiene_cpg"],
            "shp_sidecars_faltantes": sidecars["shp_sidecars_faltantes"],
            "observaciones": "",
        })

    notes = []

    if file_row["registros"] == 0:
        notes.append("sin_registros")

    if file_row["geom_vacias"] not in (None, 0):
        notes.append(f"geom_vacias={file_row['geom_vacias']}")

    if file_row["geom_invalidas"] not in (None, 0):
        notes.append(f"geom_invalidas={file_row['geom_invalidas']}")

    if file_row["crs"] is None:
        notes.append("sin_crs")

    if file_row["shp_sidecars_faltantes"]:
        notes.append(f"sidecars_faltantes={file_row['shp_sidecars_faltantes']}")

    if len(file_row["campos_tematicos_candidatos"]) == 0:
        notes.append("sin_campos_tematicos_candidatos")

    if len(file_row["campos_identificadores_candidatos"]) == 0:
        notes.append("sin_campos_identificadores_candidatos")

    file_row["observaciones"] = "; ".join(notes)
    return file_row, field_rows


# =========================================================
# 4) ANÁLISIS RASTER
# =========================================================

def analyze_raster_file(path: Path) -> Tuple[Dict[str, object], List[Dict[str, object]]]:
    file_row = base_file_row(path, "raster")
    band_rows = []

    try:
        with rasterio.open(path) as src:
            file_row["crs"] = str(src.crs) if src.crs else None
            try:
                file_row["epsg"] = src.crs.to_epsg() if src.crs else None
            except Exception:
                file_row["epsg"] = None

            file_row["raster_width"] = int(src.width)
            file_row["raster_height"] = int(src.height)
            file_row["raster_res_x"] = float(src.res[0])
            file_row["raster_res_y"] = float(src.res[1])
            file_row["raster_nodata"] = src.nodata
            file_row["raster_count"] = int(src.count)
            file_row["raster_dtype"] = safe_json(list(src.dtypes)) if src.dtypes else ""
            file_row["bbox"] = safe_bounds(src.bounds)

            for band in range(1, src.count + 1):
                valid_pixels = 0
                nodata_pixels = 0
                total_sum = 0.0
                band_min = None
                band_max = None

                for _, window in src.block_windows(band):
                    arr = src.read(band, window=window, masked=True)

                    current_valid = int(np.ma.count(arr))
                    current_total = int(arr.size)
                    current_nodata = current_total - current_valid

                    valid_pixels += current_valid
                    nodata_pixels += current_nodata

                    if current_valid > 0:
                        data = arr.compressed()

                        local_min = float(data.min())
                        local_max = float(data.max())
                        local_sum = float(data.sum())

                        band_min = local_min if band_min is None else min(band_min, local_min)
                        band_max = local_max if band_max is None else max(band_max, local_max)
                        total_sum += local_sum

                band_mean = (total_sum / valid_pixels) if valid_pixels > 0 else None

                band_rows.append({
                    "tipo_fila": "raster_band",
                    "archivo": path.name,
                    "ruta": str(path),
                    "carpeta_relativa": file_row["carpeta_relativa"],
                    "formato": path.suffix.lower().replace(".", "").upper(),
                    "tipo_dato": "raster",
                    "registros": None,
                    "num_campos": 0,
                    "campos_presentes": None,
                    "campos_tematicos_candidatos": None,
                    "campos_identificadores_candidatos": None,
                    "crs": file_row["crs"],
                    "epsg": file_row["epsg"],
                    "geom_tipos": None,
                    "geom_vacias": None,
                    "geom_invalidas": None,
                    "bbox": None,
                    "raster_width": file_row["raster_width"],
                    "raster_height": file_row["raster_height"],
                    "raster_res_x": file_row["raster_res_x"],
                    "raster_res_y": file_row["raster_res_y"],
                    "raster_nodata": file_row["raster_nodata"],
                    "raster_dtype": file_row["raster_dtype"],
                    "raster_count": file_row["raster_count"],
                    "campo_nombre": None,
                    "campo_dtype_observado": None,
                    "campo_nulos": None,
                    "campo_nulos_pct": None,
                    "campo_unicos": None,
                    "campo_top_valores": None,
                    "campo_min_text_len": None,
                    "campo_max_text_len": None,
                    "campo_numeric_min": None,
                    "campo_numeric_max": None,
                    "campo_numeric_mean": None,
                    "raster_band": band,
                    "raster_valid_pixels": valid_pixels,
                    "raster_nodata_pixels": nodata_pixels,
                    "raster_min": band_min,
                    "raster_max": band_max,
                    "raster_mean": band_mean,
                    "shp_tiene_dbf": None,
                    "shp_tiene_shx": None,
                    "shp_tiene_prj": None,
                    "shp_tiene_cpg": None,
                    "shp_sidecars_faltantes": "",
                    "observaciones": "",
                })

    except Exception as e:
        file_row["observaciones"] = f"Error de lectura: {e}"
        return file_row, band_rows

    notes = []

    if file_row["crs"] is None:
        notes.append("sin_crs")

    if file_row["raster_nodata"] is None:
        notes.append("nodata_no_declarado")

    if file_row["raster_width"] and file_row["raster_height"]:
        total_pixels = int(file_row["raster_width"]) * int(file_row["raster_height"])
        if total_pixels > 1_000_000_000:
            notes.append("raster_muy_grande_requiere_manejo_por_bloques")

    file_row["observaciones"] = "; ".join(notes)
    return file_row, band_rows


# =========================================================
# 5) RESUMEN GLOBAL TÉCNICO
# =========================================================

def build_global_rows(rows: List[Dict[str, object]]) -> List[Dict[str, object]]:
    if not rows:
        return []

    file_rows = [r for r in rows if r["tipo_fila"] == "archivo"]

    total_files = len(file_rows)
    vector_count = sum(1 for r in file_rows if r["tipo_dato"] == "vector")
    raster_count = sum(1 for r in file_rows if r["tipo_dato"] == "raster")

    format_counter = Counter(str(r["formato"]) for r in file_rows)

    total_invalid_geom = sum(
        int(r["geom_invalidas"] or 0)
        for r in file_rows
        if r["tipo_dato"] == "vector"
    )

    total_empty_geom = sum(
        int(r["geom_vacias"] or 0)
        for r in file_rows
        if r["tipo_dato"] == "vector"
    )

    no_crs_count = sum(1 for r in file_rows if not r["crs"])

    missing_sidecars_count = sum(
        1 for r in file_rows
        if r["formato"] == "SHP" and r.get("shp_sidecars_faltantes")
    )

    field_rows = [r for r in rows if r["tipo_fila"] == "campo"]
    raster_band_rows = [r for r in rows if r["tipo_fila"] == "raster_band"]

    all_fields = set()
    all_geom_types = Counter()

    for r in file_rows:
        campos = r.get("campos_presentes")
        if isinstance(campos, list):
            all_fields.update(campos)

        geom_summary = r.get("geom_tipos")
        if isinstance(geom_summary, dict):
            all_geom_types.update(geom_summary)

    high_null_fields = sum(
        1 for r in field_rows
        if r["campo_nulos_pct"] is not None and r["campo_nulos_pct"] >= 50
    )

    findings = []
    findings.append(f"Se analizaron {total_files} archivo(s): {vector_count} vectorial(es) y {raster_count} ráster(es).")
    findings.append(f"Formatos observados: {dict(format_counter)}.")

    if total_invalid_geom == 0:
        findings.append("No se detectaron geometrías inválidas en los archivos vectoriales.")
    else:
        findings.append(f"Se detectaron {total_invalid_geom:,} geometrías inválidas en total.")

    if total_empty_geom == 0:
        findings.append("No se detectaron geometrías vacías en los archivos vectoriales.")
    else:
        findings.append(f"Se detectaron {total_empty_geom:,} geometrías vacías en total.")

    if no_crs_count == 0:
        findings.append("Todos los archivos analizados reportaron CRS.")
    else:
        findings.append(f"Se detectaron {no_crs_count:,} archivo(s) sin CRS declarado.")

    if missing_sidecars_count == 0:
        findings.append("No se detectaron shapefiles con sidecars faltantes.")
    else:
        findings.append(f"Se detectaron {missing_sidecars_count:,} shapefile(s) con sidecars faltantes.")

    if high_null_fields == 0:
        findings.append("No se detectaron campos con 50% o más de nulos en el perfil atributivo.")
    else:
        findings.append(f"Se detectaron {high_null_fields:,} campo(s) con 50% o más de nulos.")

    summary_row = base_file_row(Path("__GLOBAL__"), "GLOBAL")
    summary_row.update({
        "tipo_fila": "resumen_global",
        "archivo": "__GLOBAL__",
        "ruta": str(ROOT_DIR),
        "carpeta_relativa": "",
        "formato": safe_json(dict(format_counter)),
        "registros": None,
        "num_campos": len(all_fields),
        "campos_presentes": safe_json(sorted(all_fields)),
        "geom_tipos": safe_json(dict(all_geom_types)),
        "geom_vacias": total_empty_geom,
        "geom_invalidas": total_invalid_geom,
        "raster_count": len(raster_band_rows),
        "observaciones": (
            f"archivos={total_files}; "
            f"sin_crs={no_crs_count}; "
            f"campos_perfilados={len(field_rows)}; "
            f"raster_bands={len(raster_band_rows)}; "
            f"shapefiles_sidecars_faltantes={missing_sidecars_count}"
        ),
    })

    findings_row = base_file_row(Path("__FINDINGS__"), "GLOBAL")
    findings_row.update({
        "tipo_fila": "hallazgos_globales",
        "archivo": "__FINDINGS__",
        "ruta": "",
        "carpeta_relativa": "",
        "formato": "",
        "registros": None,
        "num_campos": None,
        "observaciones": " | ".join(findings),
    })

    return [summary_row, findings_row]


# =========================================================
# 6) CLASIFICACIÓN METODOLÓGICA DU
# =========================================================

def normalize_text_for_rules(text: str) -> str:
    text = text.lower()
    text = text.replace("á", "a").replace("é", "e").replace("í", "i").replace("ó", "o").replace("ú", "u")
    text = text.replace("ñ", "n")
    text = re.sub(r"[^a-z0-9_ .\-]+", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def infer_inegi_product(row: Dict[str, object]) -> Dict[str, str]:
    """
    Clasifica por nombre/ruta/campos.
    No es limpieza ni transformación: solo DU metodológico.
    """
    archivo = normalize_text_for_rules(str(row.get("archivo", "")))
    ruta = normalize_text_for_rules(str(row.get("ruta", "")))
    carpeta = normalize_text_for_rules(str(row.get("carpeta_relativa", "")))
    campos = normalize_text_for_rules(str(row.get("campos_presentes", "")))

    blob = f"{archivo} {ruta} {carpeta} {campos}"

    # Defaults
    out = {
        "producto_inferido": "producto_no_clasificado",
        "categoria_du": "sin_clasificar",
        "subcategoria_du": "sin_clasificar",
        "temporalidad_tipo": "no_determinada",
        "periodo_referencia": "no_determinado",
        "uso_ml_posterior": "revisar",
        "uso_visualizacion": "revisar",
        "fase_uso": "du_revision",
        "prioridad_du": "media",
        "decision_du": "revisar",
        "comentario_metodologico": "Producto no clasificado automáticamente; revisar nombre, metadatos o documentación.",
    }

    if "usuev" in blob or "uso" in blob and "veget" in blob or "vegetacion" in blob:
        out.update({
            "producto_inferido": "uso_suelo_vegetacion",
            "categoria_du": "ambiental",
            "subcategoria_du": "cobertura_vegetal_uso_suelo",
            "temporalidad_tipo": "corte_cartografico_o_serie",
            "periodo_referencia": "serie_producto_inegi; confirmar en metadatos",
            "uso_ml_posterior": "candidato_fuerte_como_variable_categorica",
            "uso_visualizacion": "si",
            "fase_uso": "integration_feature_engineering",
            "prioridad_du": "alta",
            "decision_du": "conservar_revisar_calidad",
            "comentario_metodologico": (
                "Capa relevante para contexto ambiental y posible variable categórica "
                "posterior. No generar features en DU."
            ),
        })

    elif "edaf" in blob or "suelo" in blob:
        out.update({
            "producto_inferido": "edafologia",
            "categoria_du": "ambiental",
            "subcategoria_du": "suelo_edafologia",
            "temporalidad_tipo": "corte_cartografico",
            "periodo_referencia": "serie_producto_inegi; confirmar en metadatos",
            "uso_ml_posterior": "candidato_medio_como_variable_categorica",
            "uso_visualizacion": "si",
            "fase_uso": "integration_feature_engineering",
            "prioridad_du": "media",
            "decision_du": "conservar_revisar_crs_geometrias",
            "comentario_metodologico": (
                "Puede aportar contexto de suelo. Si carece de CRS, no asignar ni reproyectar "
                "hasta confirmar metadatos oficiales."
            ),
        })

    elif "fisiograf" in blob or "provincia" in blob:
        out.update({
            "producto_inferido": "fisiografia",
            "categoria_du": "ambiental",
            "subcategoria_du": "region_fisiografica",
            "temporalidad_tipo": "capa_estatica_contextual",
            "periodo_referencia": "no_aplica_como_serie_diaria",
            "uso_ml_posterior": "candidato_medio_como_variable_regional",
            "uso_visualizacion": "si",
            "fase_uso": "integration_feature_engineering",
            "prioridad_du": "media",
            "decision_du": "conservar",
            "comentario_metodologico": (
                "Útil para contextualizar regiones físicas. No tiene granularidad diaria."
            ),
        })

    elif "hidrograf" in blob or "red_hidro" in blob or "cuenca" in blob or "corriente" in blob:
        out.update({
            "producto_inferido": "hidrografia",
            "categoria_du": "ambiental",
            "subcategoria_du": "red_hidrografica",
            "temporalidad_tipo": "capa_estatica_contextual",
            "periodo_referencia": "no_aplica_como_serie_diaria",
            "uso_ml_posterior": "no_directo_derivable_distancia",
            "uso_visualizacion": "si",
            "fase_uso": "feature_engineering_visualizacion",
            "prioridad_du": "media",
            "decision_du": "conservar",
            "comentario_metodologico": (
                "No se usa directamente como variable tabular; puede servir después para "
                "distancia a red hídrica o visualización."
            ),
        })

    elif "continuonacional" in blob or "15m" in blob or "elev" in blob or row.get("tipo_dato") == "raster":
        out.update({
            "producto_inferido": "elevacion",
            "categoria_du": "elevacion",
            "subcategoria_du": "modelo_digital_elevacion",
            "temporalidad_tipo": "capa_estatica",
            "periodo_referencia": "no_aplica_como_serie_diaria",
            "uso_ml_posterior": "candidato_fuerte_como_variable_derivada",
            "uso_visualizacion": "si",
            "fase_uso": "feature_engineering",
            "prioridad_du": "alta",
            "decision_du": "conservar_revisar_tamano_raster",
            "comentario_metodologico": (
                "Útil para extraer elevación y posiblemente pendiente en Feature Engineering. "
                "No procesar completo en DU si es muy grande."
            ),
        })

    elif archivo in {"00ent.shp", "00mun.shp"} or "entidad" in blob or "municip" in blob or "nom_ent" in blob or "nom_mun" in blob:
        if archivo == "00ent.shp" or "nom_ent" in blob:
            producto = "division_estatal"
            subcategoria = "entidades_federativas"
        elif archivo == "00mun.shp" or "nom_mun" in blob:
            producto = "division_municipal"
            subcategoria = "municipios"
        else:
            producto = "division_administrativa"
            subcategoria = "marco_geoestadistico"

        out.update({
            "producto_inferido": producto,
            "categoria_du": "administrativo",
            "subcategoria_du": subcategoria,
            "temporalidad_tipo": "capa_administrativa_de_referencia",
            "periodo_referencia": "corte_geoestadistico; confirmar version",
            "uso_ml_posterior": "no_directo",
            "uso_visualizacion": "si",
            "fase_uso": "visualizacion_integration",
            "prioridad_du": "alta" if producto in {"division_estatal", "division_municipal"} else "media",
            "decision_du": "conservar",
            "comentario_metodologico": (
                "Capa útil para filtros, joins administrativos y mapas coropléticos. "
                "No debe tratarse como predictor ambiental directo."
            ),
        })

    elif archivo.startswith("00") and row.get("tipo_dato") == "vector":
        out.update({
            "producto_inferido": "marco_geoestadistico",
            "categoria_du": "administrativo",
            "subcategoria_du": "localidades_o_area_geoestadistica",
            "temporalidad_tipo": "capa_administrativa_de_referencia",
            "periodo_referencia": "corte_geoestadistico; confirmar version",
            "uso_ml_posterior": "no_directo",
            "uso_visualizacion": "si",
            "fase_uso": "visualizacion_contexto",
            "prioridad_du": "media",
            "decision_du": "conservar_si_aporta_a_consultas",
            "comentario_metodologico": (
                "Puede servir para contexto territorial o consultas. Validar si realmente "
                "se usará en la aplicación para no cargar capas innecesarias."
            ),
        })

    elif "ndvi" in blob:
        out.update({
            "producto_inferido": "ndvi",
            "categoria_du": "ambiental",
            "subcategoria_du": "indice_vegetacion",
            "temporalidad_tipo": "serie_temporal_anual_o_periodica",
            "periodo_referencia": "confirmar_anio_producto",
            "uso_ml_posterior": "candidato_fuerte_como_variable_temporal_o_contextual",
            "uso_visualizacion": "si",
            "fase_uso": "integration_feature_engineering",
            "prioridad_du": "alta",
            "decision_du": "conservar_revisar_temporalidad",
            "comentario_metodologico": (
                "NDVI sí puede aportar al análisis, pero debe cuidarse su temporalidad. "
                "No interpolar ni generar variables derivadas en DU."
            ),
        })

    return out


def build_quality_flags(row: Dict[str, object]) -> Dict[str, object]:
    flags = []

    geom_invalidas = row.get("geom_invalidas")
    geom_vacias = row.get("geom_vacias")
    crs = row.get("crs")
    observaciones = str(row.get("observaciones") or "")

    if not crs:
        flags.append("sin_crs")

    if geom_invalidas not in (None, "", 0):
        try:
            if int(geom_invalidas) > 0:
                flags.append("geometrias_invalidas")
        except Exception:
            pass

    if geom_vacias not in (None, "", 0):
        try:
            if int(geom_vacias) > 0:
                flags.append("geometrias_vacias")
        except Exception:
            pass

    if "Error de lectura" in observaciones:
        flags.append("error_lectura")

    if row.get("formato") == "SHP":
        criticos = str(row.get("shp_sidecars_criticos_faltantes") or "")
        no_criticos = str(row.get("shp_sidecars_no_criticos_faltantes") or "")

        if criticos:
            flags.append("sidecars_criticos_faltantes")

        if no_criticos:
            flags.append("sidecars_no_criticos_faltantes")

    if row.get("tipo_dato") == "raster":
        width = row.get("raster_width") or 0
        height = row.get("raster_height") or 0
        try:
            if int(width) * int(height) > 1_000_000_000:
                flags.append("raster_muy_grande")
        except Exception:
            pass

        if row.get("raster_nodata") is None:
            flags.append("nodata_no_declarado")

    nivel = "sin_hallazgos"
    if "error_lectura" in flags:
        nivel = "bloqueante"
    elif "sin_crs" in flags or "sidecars_criticos_faltantes" in flags:
        nivel = "alto"
    elif "geometrias_invalidas" in flags or "raster_muy_grande" in flags:
        nivel = "medio"
    elif "sidecars_no_criticos_faltantes" in flags:
        nivel = "bajo"
    elif flags:
        nivel = "bajo"

    return {
        "hallazgos_calidad": ";".join(flags),
        "nivel_revision": nivel,
    }


def adjust_decision_by_quality(method: Dict[str, str], quality: Dict[str, object]) -> Dict[str, str]:
    decision = method["decision_du"]
    comentario = method["comentario_metodologico"]
    nivel = quality["nivel_revision"]
    flags = quality["hallazgos_calidad"]

    if nivel == "bloqueante":
        decision = "revisar_error_lectura_antes_dp"
        comentario += " Presenta error de lectura; revisar archivo fuente antes de DP."

    elif "sin_crs" in flags:
        if "revisar_crs" not in decision:
            decision = decision + "_revisar_crs"
        comentario += " Presenta CRS ausente; en DP solo asignar CRS si se confirma con metadatos."

    if "geometrias_invalidas" in flags:
        if "revisar_geometrias" not in decision:
            decision = decision + "_revisar_geometrias"
        comentario += " Presenta geometrías inválidas; en DP puede requerir make_valid o estrategia equivalente."

    if "sidecars_criticos_faltantes" in flags:
        if "revisar_sidecars_criticos" not in decision:
            decision = decision + "_revisar_sidecars_criticos"
        comentario += " Presenta sidecars críticos faltantes; validar integridad del shapefile antes de DP."

    if "sidecars_no_criticos_faltantes" in flags:
        comentario += " Falta .cpg; revisar codificación si aparecen caracteres raros, pero no es bloqueante."
        if "raster_muy_grande" in flags:
            comentario += " Por tamaño, cualquier procesamiento posterior debe hacerse por bloques o recortes."

    method["decision_du"] = decision
    method["comentario_metodologico"] = comentario

    return method


def build_methodological_catalog(rows: List[Dict[str, object]]) -> pd.DataFrame:
    file_rows = [r for r in rows if r["tipo_fila"] == "archivo"]

    catalog = []

    for r in file_rows:
        method = infer_inegi_product(r)
        quality = build_quality_flags(r)
        method = adjust_decision_by_quality(method, quality)

        catalog.append({
            "archivo": r.get("archivo"),
            "ruta": r.get("ruta"),
            "carpeta_relativa": r.get("carpeta_relativa"),
            "formato": r.get("formato"),
            "tipo_dato": r.get("tipo_dato"),
            "registros": r.get("registros"),
            "num_campos": r.get("num_campos"),
            "epsg": r.get("epsg"),
            "crs": r.get("crs"),
            "geom_tipos": safe_json(r.get("geom_tipos")) if isinstance(r.get("geom_tipos"), dict) else r.get("geom_tipos"),
            "geom_vacias": r.get("geom_vacias"),
            "geom_invalidas": r.get("geom_invalidas"),
            "bbox": safe_json(r.get("bbox")) if isinstance(r.get("bbox"), dict) else r.get("bbox"),
            "raster_width": r.get("raster_width"),
            "raster_height": r.get("raster_height"),
            "raster_res_x": r.get("raster_res_x"),
            "raster_res_y": r.get("raster_res_y"),
            "raster_nodata": r.get("raster_nodata"),
            "raster_dtype": r.get("raster_dtype"),
            "raster_count": r.get("raster_count"),
            "shp_tiene_dbf": r.get("shp_tiene_dbf"),
            "shp_tiene_shx": r.get("shp_tiene_shx"),
            "shp_tiene_prj": r.get("shp_tiene_prj"),
            "shp_tiene_cpg": r.get("shp_tiene_cpg"),
            "shp_sidecars_faltantes": r.get("shp_sidecars_faltantes"),
            "producto_inferido": method["producto_inferido"],
            "categoria_du": method["categoria_du"],
            "subcategoria_du": method["subcategoria_du"],
            "temporalidad_tipo": method["temporalidad_tipo"],
            "periodo_referencia": method["periodo_referencia"],
            "uso_ml_posterior": method["uso_ml_posterior"],
            "uso_visualizacion": method["uso_visualizacion"],
            "fase_uso": method["fase_uso"],
            "prioridad_du": method["prioridad_du"],
            "decision_du": method["decision_du"],
            "hallazgos_calidad": quality["hallazgos_calidad"],
            "nivel_revision": quality["nivel_revision"],
            "observaciones_tecnicas": r.get("observaciones"),
            "comentario_metodologico": method["comentario_metodologico"],
        })

    df = pd.DataFrame(catalog)

    if not df.empty:
        priority_order = {"alta": 1, "media": 2, "baja": 3}
        review_order = {
            "bloqueante": 1,
            "alto": 2,
            "medio": 3,
            "bajo": 4,
            "sin_hallazgos": 5,
        }

        df["_prioridad_order"] = df["prioridad_du"].map(priority_order).fillna(99)
        df["_revision_order"] = df["nivel_revision"].map(review_order).fillna(99)

        df = df.sort_values(
            by=["_revision_order", "_prioridad_order", "categoria_du", "producto_inferido", "archivo"],
            ascending=True
        ).drop(columns=["_prioridad_order", "_revision_order"])

    return df


def build_du_summary(catalog_df: pd.DataFrame) -> pd.DataFrame:
    if catalog_df.empty:
        return pd.DataFrame()

    summaries = []

    def add_summary(group_cols: List[str], etiqueta: str):
        grouped = (
            catalog_df
            .groupby(group_cols, dropna=False)
            .size()
            .reset_index(name="num_archivos")
        )
        grouped.insert(0, "tipo_resumen", etiqueta)
        summaries.append(grouped)

    add_summary(["categoria_du"], "por_categoria")
    add_summary(["producto_inferido"], "por_producto")
    add_summary(["fase_uso"], "por_fase_uso")
    add_summary(["decision_du"], "por_decision_du")
    add_summary(["nivel_revision"], "por_nivel_revision")
    add_summary(["prioridad_du"], "por_prioridad")

    # Unifica columnas heterogéneas
    all_cols = sorted(set().union(*(set(df.columns) for df in summaries)))
    normalized = []

    for df in summaries:
        for col in all_cols:
            if col not in df.columns:
                df[col] = ""
        normalized.append(df[all_cols])

    return pd.concat(normalized, ignore_index=True)


# =========================================================
# 7) APLANADO PARA CSV TÉCNICO
# =========================================================

def flatten_rows(rows: List[Dict[str, object]]) -> List[Dict[str, object]]:
    out = []

    for r in rows:
        row = {
            "tipo_fila": r.get("tipo_fila"),
            "archivo": r.get("archivo"),
            "ruta": r.get("ruta"),
            "carpeta_relativa": r.get("carpeta_relativa"),
            "formato": r.get("formato"),
            "tipo_dato": r.get("tipo_dato"),
            "registros": r.get("registros"),
            "num_campos": r.get("num_campos"),
            "campos_presentes": safe_json(r.get("campos_presentes")) if isinstance(r.get("campos_presentes"), list) else r.get("campos_presentes"),
            "campos_tematicos_candidatos": safe_json(r.get("campos_tematicos_candidatos")) if isinstance(r.get("campos_tematicos_candidatos"), list) else r.get("campos_tematicos_candidatos"),
            "campos_identificadores_candidatos": safe_json(r.get("campos_identificadores_candidatos")) if isinstance(r.get("campos_identificadores_candidatos"), list) else r.get("campos_identificadores_candidatos"),
            "crs": r.get("crs"),
            "epsg": r.get("epsg"),
            "geom_tipos": safe_json(r.get("geom_tipos")) if isinstance(r.get("geom_tipos"), dict) else r.get("geom_tipos"),
            "geom_vacias": r.get("geom_vacias"),
            "geom_invalidas": r.get("geom_invalidas"),
            "bbox": safe_json(r.get("bbox")) if isinstance(r.get("bbox"), dict) else r.get("bbox"),
            "raster_width": r.get("raster_width"),
            "raster_height": r.get("raster_height"),
            "raster_res_x": r.get("raster_res_x"),
            "raster_res_y": r.get("raster_res_y"),
            "raster_nodata": r.get("raster_nodata"),
            "raster_dtype": r.get("raster_dtype"),
            "raster_count": r.get("raster_count"),
            "campo_nombre": r.get("campo_nombre"),
            "campo_dtype_observado": r.get("campo_dtype_observado"),
            "campo_nulos": r.get("campo_nulos"),
            "campo_nulos_pct": r.get("campo_nulos_pct"),
            "campo_unicos": r.get("campo_unicos"),
            "campo_top_valores": safe_json(r.get("campo_top_valores")) if isinstance(r.get("campo_top_valores"), list) else r.get("campo_top_valores"),
            "campo_min_text_len": r.get("campo_min_text_len"),
            "campo_max_text_len": r.get("campo_max_text_len"),
            "campo_numeric_min": r.get("campo_numeric_min"),
            "campo_numeric_max": r.get("campo_numeric_max"),
            "campo_numeric_mean": r.get("campo_numeric_mean"),
            "raster_band": r.get("raster_band"),
            "raster_valid_pixels": r.get("raster_valid_pixels"),
            "raster_nodata_pixels": r.get("raster_nodata_pixels"),
            "raster_min": r.get("raster_min"),
            "raster_max": r.get("raster_max"),
            "raster_mean": r.get("raster_mean"),
            "shp_tiene_dbf": r.get("shp_tiene_dbf"),
            "shp_tiene_shx": r.get("shp_tiene_shx"),
            "shp_tiene_prj": r.get("shp_tiene_prj"),
            "shp_tiene_cpg": r.get("shp_tiene_cpg"),
            "shp_sidecars_faltantes": r.get("shp_sidecars_faltantes"),
            "observaciones": r.get("observaciones"),
        }
        out.append(row)

    return out


# =========================================================
# 8) PIPELINE PRINCIPAL
# =========================================================

def main():
    print("\nINEGI | Data Understanding técnico + catálogo metodológico")
    print(f"Directorio raíz: {ROOT_DIR}")
    print(f"Directorio salida: {OUT_DIR}")

    if not ROOT_DIR.exists():
        raise FileNotFoundError(
            f"No existe ROOT_DIR: {ROOT_DIR}\n"
            f"Revisa la configuración ROOT_CANDIDATES al inicio del script."
        )

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    files = sorted(
        [
            p for p in ROOT_DIR.rglob("*")
            if p.is_file() and p.suffix.lower() in (VECTOR_EXTENSIONS | RASTER_EXTENSIONS)
        ]
    )

    if not files:
        print("No se encontraron archivos geoespaciales compatibles.")
        return

    print(f"Archivos geoespaciales detectados: {len(files)}")

    all_rows = []

    for idx, path in enumerate(files, start=1):
        print(f"\n[{idx}/{len(files)}] Analizando: {path.name}")

        ext = path.suffix.lower()

        if ext in VECTOR_EXTENSIONS:
            file_row, extra_rows = analyze_vector_file(path)
        elif ext in RASTER_EXTENSIONS:
            file_row, extra_rows = analyze_raster_file(path)
        else:
            continue

        all_rows.append(file_row)
        all_rows.extend(extra_rows)

        print(f"  Tipo: {file_row['tipo_dato']}")
        print(f"  CRS: {file_row['crs']}")
        print(f"  EPSG: {file_row['epsg']}")
        print(f"  Registros: {file_row['registros']}")
        print(f"  Campos: {file_row['num_campos']}")
        print(f"  Observaciones: {file_row['observaciones']}")

    # Reporte técnico DU01
    global_rows = build_global_rows(all_rows)
    final_rows = flatten_rows(all_rows + global_rows)
    technical_df = pd.DataFrame(final_rows)
    technical_df.to_csv(OUT_REPORT, index=False, encoding="utf-8-sig")

    # Catálogo metodológico DU02 integrado
    catalog_df = build_methodological_catalog(all_rows)
    catalog_df.to_csv(OUT_CATALOG, index=False, encoding="utf-8-sig")

    # Resumen ejecutivo compacto
    summary_df = build_du_summary(catalog_df)
    summary_df.to_csv(OUT_SUMMARY, index=False, encoding="utf-8-sig")

    print("\n=== RESUMEN GLOBAL ===")
    print(f"Archivos perfilados: {sum(1 for r in all_rows if r['tipo_fila'] == 'archivo')}")
    print(f"Filas totales en reporte técnico: {len(final_rows)}")
    print(f"Filas en catálogo metodológico: {len(catalog_df)}")
    print(f"Filas en resumen ejecutivo: {len(summary_df)}")

    print("\nArchivos generados:")
    print(f"  1) {OUT_REPORT}")
    print(f"  2) {OUT_CATALOG}")
    print(f"  3) {OUT_SUMMARY}")

    if not catalog_df.empty:
        print("\n=== DECISIONES DU POR ARCHIVO ===")
        cols = [
            "archivo",
            "producto_inferido",
            "categoria_du",
            "fase_uso",
            "prioridad_du",
            "decision_du",
            "nivel_revision",
        ]
        print(catalog_df[cols].to_string(index=False))


if __name__ == "__main__":
    main()