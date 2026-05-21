# -*- coding: utf-8 -*-
"""
INEGI | Data Preparation (DP) - Capas geoespaciales limpias

Objetivo
--------
Preparar físicamente las capas INEGI seleccionadas en DU.

DP:
- lectura de capas crudas;
- validación de existencia;
- validación/asignación controlada de CRS;
- reparación de geometrías inválidas;
- eliminación controlada de geometrías nulas, vacías o inválidas remanentes;
- reproyección a CRS común;
- normalización mínima de nombres de columnas;
- escritura de capas limpias en GeoPackage;
- reportes técnicos de calidad y pendientes.
"""

from __future__ import annotations

import re
import unicodedata
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import geopandas as gpd
import pandas as pd


# =========================================================
# 1) CONFIGURACIÓN
# =========================================================

BASE_DIR = Path(r"C:\Users\Hp\OneDrive\Documentos\PT_Analisis")

RAW_DIR = BASE_DIR / "01_raw-data" / "inegi"

DP_DIR = BASE_DIR / "03_data-preparation" / "inegi"
DATASETS_DIR = DP_DIR / "datasets"
REPORTS_DIR = DP_DIR / "reports"

DATASETS_DIR.mkdir(parents=True, exist_ok=True)
REPORTS_DIR.mkdir(parents=True, exist_ok=True)

OUT_GPKG = DATASETS_DIR / "inegi_capas_limpias.gpkg"
OUT_LAYER_INDEX = REPORTS_DIR / "dp_inegi_indice_capas_limpias.csv"
OUT_QUALITY_REPORT = REPORTS_DIR / "dp_inegi_reporte_calidad.csv"
OUT_PENDING_REPORT = REPORTS_DIR / "dp_inegi_pendientes.csv"

# CRS común final para todas las capas vectoriales limpias.
# EPSG:6365 corresponde al CRS proyectado México ITRF2008 LCC usado por capas INEGI actuales.
TARGET_CRS = "EPSG:6365"

# CRS manual para edafología.
# La capa llegó sin .prj, pero el metadato INEGI indica:
# Proyección: Cónica Conforme de Lambert
# Datum: ITRF92 época 1988.0
# Paralelos estándar: 17.5 y 29.5
# Latitud de origen: 12
# Meridiano central: -102
# Falso este: 2500000
# Falso norte: 0
#
# Se asigna este CRS original aproximado y después se reproyecta a TARGET_CRS.
EDAFOLOGIA_CRS_MANUAL: Optional[str] = (
    "+proj=lcc "
    "+lat_0=12 "
    "+lon_0=-102 "
    "+lat_1=17.5 "
    "+lat_2=29.5 "
    "+x_0=2500000 "
    "+y_0=0 "
    "+ellps=GRS80 "
    "+units=m "
    "+no_defs"
)


VECTOR_LAYERS = [
    {
        "id": "entidades",
        "filename": "00ent.shp",
        "layer_name": "entidades_limpio",
        "categoria": "administrativo",
        "uso_dp": "base territorial estatal para joins, filtros y visualizacion",
        "required": True,
        "manual_crs": None,
    },
    {
        "id": "municipios",
        "filename": "00mun.shp",
        "layer_name": "municipios_limpio",
        "categoria": "administrativo",
        "uso_dp": "base territorial municipal para joins, filtros y visualizacion",
        "required": True,
        "manual_crs": None,
    },
    {
        "id": "uso_suelo_vegetacion",
        "filename": "cdv_usuev250sVII_cnal.shp",
        "layer_name": "uso_suelo_vegetacion_limpio",
        "categoria": "ambiental",
        "uso_dp": "capa ambiental limpia para integracion o feature engineering posterior",
        "required": True,
        "manual_crs": None,
    },
    {
        "id": "fisiografia",
        "filename": "provincias_fisiograficas.shp",
        "layer_name": "fisiografia_limpio",
        "categoria": "ambiental",
        "uso_dp": "capa regional fisica limpia para integracion o visualizacion posterior",
        "required": True,
        "manual_crs": None,
    },
    {
        "id": "hidrografia",
        "filename": "red_hidrografica_250k.shp",
        "layer_name": "hidrografia_limpio",
        "categoria": "ambiental",
        "uso_dp": "capa hidrografica limpia; distancia/proximidad queda para feature engineering",
        "required": True,
        "manual_crs": None,
    },
    {
        "id": "edafologia",
        "filename": "cdv_edaf_esc_250k_serie II_cont_nac.shp",
        "layer_name": "edafologia_limpio",
        "categoria": "ambiental",
        "uso_dp": "capa de suelo limpia para integracion o feature engineering posterior",
        "required": True,
        "manual_crs": EDAFOLOGIA_CRS_MANUAL,
    },
]


# =========================================================
# 2) UTILIDADES
# =========================================================

def find_file(root: Path, filename: str) -> Optional[Path]:
    matches = list(root.rglob(filename))

    if not matches:
        return None

    if len(matches) > 1:
        print(f"Advertencia: se encontraron múltiples archivos para {filename}. Se usará: {matches[0]}")

    return matches[0]


def strip_accents(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", text)
    return "".join(c for c in normalized if not unicodedata.combining(c))


def normalize_column_name(col: str) -> str:
    col = strip_accents(str(col)).lower().strip()
    col = re.sub(r"[^a-z0-9]+", "_", col)
    col = re.sub(r"_+", "_", col).strip("_")

    if not col:
        col = "campo"

    if col[0].isdigit():
        col = f"c_{col}"

    return col


def make_unique_columns(columns: List[str]) -> List[str]:
    seen = {}
    out = []

    for c in columns:
        base = normalize_column_name(c)

        if base not in seen:
            seen[base] = 0
            out.append(base)
        else:
            seen[base] += 1
            out.append(f"{base}_{seen[base]}")

    return out


def normalize_text_value(value):
    if pd.isna(value):
        return None

    s = str(value).strip()
    s = re.sub(r"\s+", " ", s)

    return s if s else None


def get_geom_quality(gdf: gpd.GeoDataFrame) -> Dict[str, int]:
    total = int(len(gdf))

    if "geometry" not in gdf.columns:
        return {
            "total_registros": total,
            "geom_nulas": 0,
            "geom_vacias": 0,
            "geom_invalidas": 0,
        }

    geom_nulas = int(gdf.geometry.isna().sum())

    try:
        geom_vacias = int(gdf.geometry.is_empty.sum())
    except Exception:
        geom_vacias = 0

    try:
        geom_invalidas = int((~gdf.geometry.is_valid).sum())
    except Exception:
        geom_invalidas = 0

    return {
        "total_registros": total,
        "geom_nulas": geom_nulas,
        "geom_vacias": geom_vacias,
        "geom_invalidas": geom_invalidas,
    }


def repair_geometries(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """
    Repara geometrías inválidas con estrategia doble:
    1) shapely.make_valid si está disponible.
    2) buffer(0) para geometrías que sigan inválidas.
    """
    gdf = gdf.copy()

    if "geometry" not in gdf.columns:
        return gdf

    mask_notna = gdf.geometry.notna()

    try:
        from shapely import make_valid
        gdf.loc[mask_notna, "geometry"] = gdf.loc[mask_notna, "geometry"].apply(make_valid)
    except Exception:
        pass

    try:
        invalid_mask = gdf.geometry.notna() & (~gdf.geometry.is_valid)
        if invalid_mask.any():
            gdf.loc[invalid_mask, "geometry"] = gdf.loc[invalid_mask, "geometry"].buffer(0)
    except Exception:
        pass

    return gdf


def clean_geometries(gdf: gpd.GeoDataFrame) -> Tuple[gpd.GeoDataFrame, Dict[str, int]]:
    """
    Elimina geometrías nulas, vacías e inválidas remanentes después de reparación.
    Se registra cuántas fueron removidas.
    """
    before = len(gdf)

    gdf = gdf[gdf.geometry.notna()].copy()
    after_null = len(gdf)

    gdf = gdf[~gdf.geometry.is_empty].copy()
    after_empty = len(gdf)

    try:
        gdf = gdf[gdf.geometry.is_valid].copy()
    except Exception:
        pass

    after_invalid = len(gdf)

    removed = {
        "removidas_geom_nula": before - after_null,
        "removidas_geom_vacia": after_null - after_empty,
        "removidas_geom_invalida_remanente": after_empty - after_invalid,
        "removidas_total": before - after_invalid,
    }

    return gdf, removed


def assign_or_validate_crs(
    gdf: gpd.GeoDataFrame,
    layer_id: str,
    manual_crs: Optional[str],
) -> Tuple[gpd.GeoDataFrame, str]:
    """
    Si la capa no tiene CRS:
    - usa manual_crs si fue definido;
    - si no, la manda a pendientes.
    """
    gdf = gdf.copy()

    if gdf.crs is None:
        if manual_crs:
            gdf = gdf.set_crs(manual_crs, allow_override=True)
            return gdf, f"crs_asignado_manual={manual_crs}"

        raise ValueError(
            f"La capa {layer_id} no tiene CRS. "
            f"No se asigna CRS automáticamente para evitar reproyección incorrecta."
        )

    return gdf, "crs_original_conservado"


def normalize_attributes(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """
    Normalización mínima:
    - nombres de columnas a snake_case sin acentos;
    - cadenas con espacios normalizados.
    """
    gdf = gdf.copy()

    old_cols = list(gdf.columns)
    new_cols = make_unique_columns(old_cols)
    rename_map = dict(zip(old_cols, new_cols))

    if "geometry" in old_cols:
        rename_map["geometry"] = "geometry"

    gdf = gdf.rename(columns=rename_map)

    for col in gdf.columns:
        if col == "geometry":
            continue

        if pd.api.types.is_object_dtype(gdf[col]):
            gdf[col] = gdf[col].map(normalize_text_value)

    return gdf


def normalize_admin_keys(gdf: gpd.GeoDataFrame, layer_id: str) -> gpd.GeoDataFrame:
    gdf = gdf.copy()

    if "cve_ent" in gdf.columns:
        gdf["cve_ent"] = gdf["cve_ent"].astype(str).str.strip().str.zfill(2)

    if layer_id == "municipios":
        if "cve_mun" in gdf.columns:
            gdf["cve_mun"] = gdf["cve_mun"].astype(str).str.strip().str.zfill(3)

        if "cvegeo" in gdf.columns:
            gdf["cvegeo"] = gdf["cvegeo"].astype(str).str.strip().str.zfill(5)

    return gdf


def add_dp_metadata(
    gdf: gpd.GeoDataFrame,
    layer_id: str,
    categoria: str,
    uso_dp: str,
) -> gpd.GeoDataFrame:
    gdf = gdf.copy()

    gdf["dp_fuente"] = "inegi"
    gdf["dp_capa"] = layer_id
    gdf["dp_categoria"] = categoria
    gdf["dp_uso"] = uso_dp

    return gdf


def delete_existing_gpkg(path: Path) -> None:
    if path.exists():
        path.unlink()


# =========================================================
# 3) PREPARACIÓN DE CAPAS
# =========================================================

def prepare_vector_layer(
    layer_cfg: Dict[str, object]
) -> Tuple[Optional[Dict[str, object]], Optional[Dict[str, object]]]:

    layer_id = str(layer_cfg["id"])
    filename = str(layer_cfg["filename"])
    layer_name = str(layer_cfg["layer_name"])
    categoria = str(layer_cfg["categoria"])
    uso_dp = str(layer_cfg["uso_dp"])
    required = bool(layer_cfg.get("required", False))
    manual_crs = layer_cfg.get("manual_crs")

    path = find_file(RAW_DIR, filename)

    if path is None:
        pending = {
            "capa": layer_id,
            "archivo": filename,
            "problema": "archivo_no_encontrado",
            "detalle": f"No se encontró {filename} dentro de {RAW_DIR}",
            "accion_requerida": "verificar descarga o ruta",
            "bloqueante": required,
        }

        return None, pending

    print(f"\nPreparando capa: {layer_id}")
    print(f"Archivo: {path}")

    try:
        gdf = gpd.read_file(path)
    except Exception as e:
        pending = {
            "capa": layer_id,
            "archivo": filename,
            "problema": "error_lectura",
            "detalle": str(e),
            "accion_requerida": "revisar integridad del archivo fuente",
            "bloqueante": required,
        }

        return None, pending

    original_crs = str(gdf.crs) if gdf.crs else None
    original_quality = get_geom_quality(gdf)
    original_rows = len(gdf)

    try:
        gdf, crs_action = assign_or_validate_crs(gdf, layer_id, manual_crs)
    except Exception as e:
        pending = {
            "capa": layer_id,
            "archivo": filename,
            "problema": "crs_pendiente",
            "detalle": str(e),
            "accion_requerida": (
                "confirmar CRS con metadatos oficiales y configurar CRS manual si corresponde"
            ),
            "bloqueante": required,
        }

        return None, pending

    gdf = repair_geometries(gdf)
    quality_after_repair = get_geom_quality(gdf)

    gdf, removed_geom = clean_geometries(gdf)

    if gdf.empty:
        pending = {
            "capa": layer_id,
            "archivo": filename,
            "problema": "capa_vacia_post_limpieza",
            "detalle": "La capa quedó vacía después de limpiar geometrías.",
            "accion_requerida": "revisar fuente",
            "bloqueante": required,
        }

        return None, pending

    if str(gdf.crs) != str(TARGET_CRS):
        gdf = gdf.to_crs(TARGET_CRS)

    # Segunda reparación después de reproyección.
    # Algunas geometrías pueden volverse inválidas al transformar CRS.
    gdf = repair_geometries(gdf)
    gdf, removed_geom_post_crs = clean_geometries(gdf)

    # Sumar removidos post-CRS al conteo previo
    removed_geom["removidas_geom_nula"] += removed_geom_post_crs["removidas_geom_nula"]
    removed_geom["removidas_geom_vacia"] += removed_geom_post_crs["removidas_geom_vacia"]
    removed_geom["removidas_geom_invalida_remanente"] += removed_geom_post_crs["removidas_geom_invalida_remanente"]
    removed_geom["removidas_total"] += removed_geom_post_crs["removidas_total"]

    gdf = normalize_attributes(gdf)
    gdf = normalize_admin_keys(gdf, layer_id)
    gdf = add_dp_metadata(gdf, layer_id, categoria, uso_dp)

    final_quality = get_geom_quality(gdf)

    gdf.to_file(OUT_GPKG, layer=layer_name, driver="GPKG")

    estado_dp = "preparado"
    if final_quality["geom_invalidas"] > 0:
        estado_dp = "preparado_con_observaciones"

    report = {
        "capa": layer_id,
        "archivo": filename,
        "layer_gpkg": layer_name,
        "categoria": categoria,
        "uso_dp": uso_dp,
        "ruta_origen": str(path),
        "ruta_salida": str(OUT_GPKG),
        "crs_original": original_crs,
        "crs_accion": crs_action,
        "crs_final": str(gdf.crs),
        "registros_originales": original_rows,
        "registros_finales": len(gdf),
        "registros_removidos_total": removed_geom["removidas_total"],
        "removidas_geom_nula": removed_geom["removidas_geom_nula"],
        "removidas_geom_vacia": removed_geom["removidas_geom_vacia"],
        "removidas_geom_invalida_remanente": removed_geom["removidas_geom_invalida_remanente"],
        "geom_invalidas_antes": original_quality["geom_invalidas"],
        "geom_invalidas_despues_reparacion": quality_after_repair["geom_invalidas"],
        "geom_invalidas_final": final_quality["geom_invalidas"],
        "geom_nulas_originales": original_quality["geom_nulas"],
        "geom_vacias_originales": original_quality["geom_vacias"],
        "num_columnas_final": len(gdf.columns),
        "estado_dp": estado_dp,
    }

    print(f"Registros originales: {original_rows}")
    print(f"Registros finales: {len(gdf)}")
    print(f"Removidos por geometría: {removed_geom['removidas_total']}")
    print(f"Geometrías inválidas antes: {original_quality['geom_invalidas']}")
    print(f"Geometrías inválidas después reparación: {quality_after_repair['geom_invalidas']}")
    print(f"Geometrías inválidas final: {final_quality['geom_invalidas']}")
    print(f"CRS final: {gdf.crs}")
    print(f"Layer guardada: {layer_name}")

    return report, None


# =========================================================
# 4) PIPELINE PRINCIPAL
# =========================================================

def main():
    print("\nINEGI | Data Preparation - Capas limpias")
    print(f"RAW_DIR: {RAW_DIR}")
    print(f"DATASETS_DIR: {DATASETS_DIR}")
    print(f"REPORTS_DIR: {REPORTS_DIR}")
    print(f"TARGET_CRS: {TARGET_CRS}")

    if not RAW_DIR.exists():
        raise FileNotFoundError(f"No existe RAW_DIR: {RAW_DIR}")

    delete_existing_gpkg(OUT_GPKG)

    layer_reports = []
    pending_reports = []

    for cfg in VECTOR_LAYERS:
        report, pending = prepare_vector_layer(cfg)

        if report is not None:
            layer_reports.append(report)

        if pending is not None:
            pending_reports.append(pending)

    layer_index = pd.DataFrame(layer_reports)

    if not layer_index.empty:
        layer_index = layer_index.sort_values(by=["categoria", "capa"]).reset_index(drop=True)

    layer_index.to_csv(OUT_LAYER_INDEX, index=False, encoding="utf-8-sig")

    quality_cols = [
        "capa",
        "archivo",
        "categoria",
        "crs_original",
        "crs_accion",
        "crs_final",
        "registros_originales",
        "registros_finales",
        "registros_removidos_total",
        "removidas_geom_nula",
        "removidas_geom_vacia",
        "removidas_geom_invalida_remanente",
        "geom_invalidas_antes",
        "geom_invalidas_despues_reparacion",
        "geom_invalidas_final",
        "estado_dp",
    ]

    if not layer_index.empty:
        quality_report = layer_index[quality_cols].copy()
    else:
        quality_report = pd.DataFrame(columns=quality_cols)

    quality_report.to_csv(OUT_QUALITY_REPORT, index=False, encoding="utf-8-sig")

    pending_cols = [
        "capa",
        "archivo",
        "problema",
        "detalle",
        "accion_requerida",
        "bloqueante",
    ]

    pending_df = pd.DataFrame(pending_reports)

    if pending_df.empty:
        if OUT_PENDING_REPORT.exists():
            OUT_PENDING_REPORT.unlink()
        print("No hay pendientes. No se generó archivo de pendientes.")
    else:
        pending_df = pending_df[pending_cols]
        pending_df.to_csv(OUT_PENDING_REPORT, index=False, encoding="utf-8-sig")
        print(f"Reporte de pendientes: {OUT_PENDING_REPORT}")

    print("\n=== RESUMEN DP INEGI ===")
    print(f"Capas preparadas: {len(layer_reports)}")
    print(f"Pendientes: {len(pending_reports)}")
    print(f"GeoPackage generado: {OUT_GPKG}")
    print(f"Índice de capas: {OUT_LAYER_INDEX}")
    print(f"Reporte de calidad: {OUT_QUALITY_REPORT}")

    if pending_reports:
        print("\n=== PENDIENTES ===")
        for p in pending_reports:
            print(f"- {p['capa']} | {p['problema']} | {p['accion_requerida']}")

    print("\nProceso terminado.")


if __name__ == "__main__":
    main()