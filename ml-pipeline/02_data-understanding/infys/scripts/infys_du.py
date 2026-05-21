# -*- coding: utf-8 -*-
"""
INFyS | Data Understanding consolidado

Fase CRISP-DM:
- Data Understanding

Qué hace:
1) Inventario general multiformato de archivos INFyS.
2) Inventario de workbooks y hojas Excel.
3) Perfil detallado de workbooks prioritarios.
4) Clasificación preliminar de productos, ciclos, formatos y utilidad metodológica.

Salidas:
- 02_data-understanding/infys/reports/infys_du_file_inventory.csv
- 02_data-understanding/infys/reports/infys_du_excel_inventory.csv
- 02_data-understanding/infys/reports/infys_du_priority_profile.csv
- 02_data-understanding/infys/reports/infys_du_summary.csv
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd


# =========================================================
# 1) CONFIGURACIÓN
# =========================================================

BASE_DIR = Path(r"C:\Users\Hp\OneDrive\Documentos\PT_Analisis")

ROOT_DIR = BASE_DIR / "01_raw-data" / "infys"
OUT_DIR = BASE_DIR / "02_data-understanding" / "infys" / "reports"
OUT_DIR.mkdir(parents=True, exist_ok=True)

OUT_FILE_INVENTORY = OUT_DIR / "infys_du_archivo_inventario.csv"
OUT_EXCEL_INVENTORY = OUT_DIR / "infys_du_excel_inventario.csv"
OUT_PRIORITY_PROFILE = OUT_DIR / "infys_du_perfil_prioridad.csv"
OUT_SUMMARY = OUT_DIR / "infys_du_resumen.csv"

EXCEL_EXTENSIONS = {".xlsx", ".xls"}
VECTOR_EXTENSIONS = {".shp", ".geojson", ".gpkg", ".kml"}
RASTER_EXTENSIONS = {".tif", ".tiff"}
TABULAR_EXTENSIONS = {".csv", ".xlsx", ".xls", ".dbf"}
METADATA_EXTENSIONS = {".xml", ".txt", ".pdf", ".doc", ".docx"}
SHAPEFILE_SIDE_EXTENSIONS = {".shp", ".shx", ".dbf", ".prj", ".cpg", ".sbn", ".sbx", ".qpj"}

TARGET_WORKBOOKS = {
    "INFyS_Secciones_2004_2009.xlsx",
    "INFyS_Secciones_2009_2014.xlsx",
    "INFyS_Secciones_2015-2020.xlsx",
    "1_Superficie.xlsx",
    "Superficie_forestal_INFyS-2015-2020_Tablas_v4_27042023.xlsx",
    "DeforestacionNacional_2024.xlsx",
}

SAMPLE_ROWS = 10
PROFILE_ROWS = 500
TOP_N = 10


# =========================================================
# 2) UTILIDADES GENERALES
# =========================================================

def safe_json(value) -> str:
    if value is None:
        return ""
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def normalize_text(value: object) -> str:
    if value is None:
        return ""

    s = str(value).strip().lower()
    replacements = {
        "á": "a",
        "é": "e",
        "í": "i",
        "ó": "o",
        "ú": "u",
        "ñ": "n",
    }

    for old, new in replacements.items():
        s = s.replace(old, new)

    s = re.sub(r"\s+", "_", s)
    return s


def normalize_column_name(value: object) -> str:
    s = normalize_text(value)
    s = re.sub(r"[^a-z0-9_]+", "_", s)
    s = re.sub(r"_+", "_", s)
    return s.strip("_")


def file_size_mb(path: Path) -> float:
    try:
        return round(path.stat().st_size / (1024 * 1024), 4)
    except Exception:
        return 0.0


def detect_cycle(path_or_name: object) -> str:
    s_raw = str(path_or_name)
    s = normalize_text(s_raw)

    if re.search(r"2004\s*[-_]\s*2009|2004\s*[–-]\s*2009", s_raw, flags=re.I):
        return "2004-2009"

    if re.search(r"2009\s*[-_]\s*2014|2009\s*[–-]\s*2014", s_raw, flags=re.I):
        return "2009-2014"

    if re.search(r"2015\s*[-_]\s*2020|2015\s*[–-]\s*2020", s_raw, flags=re.I):
        return "2015-2020"

    if "deforestacionnacional_2024" in s or "deforestacion" in s:
        return "2001-2024"

    years = re.findall(r"20\d{2}", s_raw)

    if years:
        years = sorted(set(years))
        if len(years) == 1:
            return years[0]
        return f"{years[0]}-{years[-1]}"

    return "desconocido"


def detect_product(path_or_name: object) -> str:
    s = normalize_text(path_or_name)

    if "secciones" in s:
        return "secciones"

    if "superficie" in s:
        return "superficie_forestal"

    if "dasometric" in s or "dasometrico" in s:
        return "dasometricos"

    if "composicion" in s or "estructura" in s or "ivi" in s or "ivf" in s:
        return "composicion_estructura"

    if "salud" in s or "sanidad" in s or "saludftal" in s:
        return "sanidad_forestal"

    if "suelo" in s or "suelos" in s:
        return "suelos"

    if "deforest" in s:
        return "deforestacion"

    if "arbolado" in s:
        return "arbolado"

    if "distribucion" in s or "at_dn" in s or "at-dn" in s:
        return "distribucion_arbolado"

    if "existencias" in s:
        return "existencias"

    if "incremento_medio_anual" in s or "ima" in s:
        return "incremento_medio_anual"

    if "tipo_propiedad" in s or "tipo-propiedad" in s or "propiedad" in s:
        return "tipo_propiedad"

    if "diccionario" in s or "catalogo" in s or "catálogo" in s:
        return "catalogo_diccionario"

    if "ecuacion" in s or "volumen" in s:
        return "ecuaciones_volumen"

    if "geoespacial" in s or "geo" in s:
        return "informacion_geoespacial"

    if "conglomerado" in s:
        return "conglomerados"

    if "sitio" in s:
        return "sitios"

    if "parcela" in s:
        return "parcelas"

    if "biomasa" in s:
        return "biomasa"

    if "carbono" in s:
        return "carbono"

    if "cobertura" in s:
        return "cobertura_forestal"

    return "desconocido"


def detect_format_group(path: Path) -> str:
    ext = path.suffix.lower()

    if ext in EXCEL_EXTENSIONS or ext == ".csv" or ext == ".dbf":
        return "tabular"

    if ext in VECTOR_EXTENSIONS:
        return "vectorial"

    if ext in RASTER_EXTENSIONS:
        return "raster"

    if ext in METADATA_EXTENSIONS:
        return "metadato_documentacion"

    if ext in SHAPEFILE_SIDE_EXTENSIONS:
        return "archivo_auxiliar_shapefile"

    return "otro"


def candidate_columns(columns: List[str], keywords: List[str]) -> List[str]:
    out = []

    for c in columns:
        low = normalize_column_name(c)
        if any(k in low for k in keywords):
            out.append(str(c))

    return sorted(set(out))


def classify_sheet(sheet_name: str, columns: List[str]) -> str:
    s = normalize_column_name(sheet_name)
    cols = " ".join(normalize_column_name(c) for c in columns)
    text = f"{s} {cols}"

    if any(k in text for k in ["diccionario", "catalogo", "catálogo", "glosario"]):
        return "catalogo_o_diccionario"

    if any(k in text for k in ["estatus", "conglomerado", "sitio", "muestreado", "upmid", "idconglomerado"]):
        return "detalle_muestreo"

    if any(k in text for k in ["arbol", "arbolado", "diametro", "altura", "dap", "densidad"]):
        return "detalle_dasometrico"

    if any(k in text for k in ["municipio", "parcela", "x_", "y_", "coordenada", "lat", "lon"]):
        return "detalle_geografico"

    if any(k in text for k in ["superficie", "ecosistema", "formacion", "ha", "desveg", "fase_vs"]):
        return "indicador_agregado"

    if any(k in text for k in ["estado", "cve_estado", "cve_ent", "nom_ent", "forestal", "deforestacion"]):
        return "posible_indicador_agregado"

    return "desconocido"


def detect_aggregation_level(columns: List[str], sheet_name: str) -> str:
    cols = [normalize_column_name(c) for c in columns]
    s = normalize_column_name(sheet_name)
    text = " ".join(cols) + " " + s

    has_estado = any(k in text for k in ["cve_estado", "estado", "cve_ent", "nom_ent", "entidad"])
    has_municipio = any(k in text for k in ["cve_municipio", "municipio", "cve_mun", "nom_mun"])
    has_coords = any(k in text for k in ["x_", "y_", "lat", "lon", "coord", "utm"])
    has_conglomerado = any(k in text for k in ["conglomerado", "upmid", "sitio", "muestreado"])
    has_anio = any(k in text for k in ["anio", "ano", "año", "year", "periodo", "ciclo"])
    has_ecosistema = any(k in text for k in ["ecosistema", "formacion", "descrip_s6", "desveg_s6", "fase_vs_s6", "ha"])

    if has_estado and has_municipio and not has_coords:
        return "estado_municipio"

    if has_estado and has_ecosistema and not has_coords:
        return "estado_ecosistema_formacion"

    if has_estado and not has_coords and not has_conglomerado:
        return "estado"

    if has_coords and has_conglomerado:
        return "sitio_conglomerado"

    if has_coords and has_estado:
        return "detalle_geografico"

    if has_anio and not has_estado and not has_coords:
        return "serie_anual"

    return "desconocido"


def infer_methodological_use(product: str, format_group: str, aggregation_level: Optional[str] = None) -> str:
    aggregation_level = aggregation_level or ""

    if product in {
        "secciones",
        "superficie_forestal",
        "deforestacion",
        "suelos",
        "composicion_estructura",
        "dasometricos",
        "sanidad_forestal",
        "biomasa",
        "carbono",
        "cobertura_forestal",
        "existencias",
        "incremento_medio_anual",
        "tipo_propiedad",
        "distribucion_arbolado",
    }:
        if aggregation_level in {"sitio_conglomerado", "detalle_geografico"}:
            return "candidato_ml_posterior_o_contexto_geoespacial"

        if aggregation_level in {"estado", "estado_municipio", "estado_ecosistema_formacion", "serie_anual"}:
            return "contexto_visualizacion_apoyo_descriptivo"

        return "revisar_utilidad"

    if product in {"catalogo_diccionario", "ecuaciones_volumen"}:
        return "metadato_catalogo_apoyo"

    if format_group == "raster":
        return "revisar_raster"

    if format_group == "vectorial":
        return "revisar_vectorial"

    return "revisar_utilidad"


def infer_preliminary_decision(product: str, format_group: str, observations: str = "") -> str:
    obs = normalize_text(observations)

    if "error" in obs or "incompleto" in obs or "corrupt" in obs:
        return "revisar"

    if product in {"catalogo_diccionario", "ecuaciones_volumen"}:
        return "conservar_como_apoyo"

    if product == "desconocido":
        return "revisar"

    if format_group in {"tabular", "vectorial", "raster"}:
        return "conservar_para_du"

    return "revisar"


# =========================================================
# 3) DU-00 INVENTARIO GENERAL MULTIFORMATO
# =========================================================

def shapefile_component_status(shp_path: Path) -> Dict[str, object]:
    stem = shp_path.with_suffix("")
    existing = []
    missing_required = []

    required = [".shp", ".shx", ".dbf", ".prj"]

    for ext in SHAPEFILE_SIDE_EXTENSIONS:
        candidate = stem.with_suffix(ext)
        if candidate.exists():
            existing.append(ext)

    for ext in required:
        if not stem.with_suffix(ext).exists():
            missing_required.append(ext)

    return {
        "componentes_existentes": existing,
        "componentes_requeridos_faltantes": missing_required,
        "shapefile_completo_basico": len(missing_required) == 0,
    }


def build_file_inventory() -> pd.DataFrame:
    rows = []
    all_files = sorted([p for p in ROOT_DIR.rglob("*") if p.is_file()])

    for path in all_files:
        ext = path.suffix.lower()
        product = detect_product(path.name)
        cycle = detect_cycle(str(path))
        format_group = detect_format_group(path)

        obs = []
        shp_components = []
        shp_missing = []
        shp_complete = None

        if ext == ".shp":
            status = shapefile_component_status(path)
            shp_components = status["componentes_existentes"]
            shp_missing = status["componentes_requeridos_faltantes"]
            shp_complete = status["shapefile_completo_basico"]

            if not shp_complete:
                obs.append(f"shapefile_incompleto_faltan={shp_missing}")

        if ext in SHAPEFILE_SIDE_EXTENSIONS and ext != ".shp":
            obs.append("archivo_auxiliar_de_shapefile")

        methodological_use = infer_methodological_use(product, format_group)
        decision = infer_preliminary_decision(product, format_group, "; ".join(obs))

        rows.append({
            "archivo": path.name,
            "ruta": str(path),
            "extension": ext,
            "tamano_mb": file_size_mb(path),
            "grupo_formato": format_group,
            "producto_detectado": product,
            "ciclo_detectado": cycle,
            "componentes_shapefile_existentes": safe_json(shp_components),
            "componentes_shapefile_requeridos_faltantes": safe_json(shp_missing),
            "shapefile_completo_basico": shp_complete,
            "utilidad_metodologica_preliminar": methodological_use,
            "decision_preliminar_du": decision,
            "observaciones": "; ".join(obs),
        })

    return pd.DataFrame(rows)


# =========================================================
# 4) DU-01 INVENTARIO EXCEL
# =========================================================

def top_non_null_columns(sample_df: pd.DataFrame) -> List[str]:
    valid_counts = {}

    for col in sample_df.columns:
        non_null = sample_df[col].notna().sum()
        if non_null > 0:
            valid_counts[str(col)] = int(non_null)

    top = sorted(valid_counts.items(), key=lambda x: x[1], reverse=True)[:10]
    return [k for k, _ in top]


def profile_excel_sheet(excel_path: Path, sheet_name: str) -> Dict[str, object]:
    row = {
        "tipo_fila": "hoja",
        "archivo": excel_path.name,
        "ruta": str(excel_path),
        "tamano_mb": file_size_mb(excel_path),
        "ciclo_detectado": detect_cycle(str(excel_path)),
        "producto_detectado": detect_product(str(excel_path)),
        "hoja": sheet_name,
        "clasificacion_hoja": None,
        "nivel_agregacion_observado": None,
        "n_filas": None,
        "n_columnas": None,
        "columnas": [],
        "columnas_top_no_nulas": [],
        "columnas_totalmente_vacias": [],
        "columnas_candidatas_estado": [],
        "columnas_candidatas_municipio": [],
        "columnas_candidatas_coordenadas": [],
        "columnas_candidatas_anio": [],
        "columnas_candidatas_muestreo": [],
        "columnas_candidatas_agregacion": [],
        "utilidad_metodologica_preliminar": None,
        "decision_preliminar_du": None,
        "observaciones": "",
    }

    try:
        df = pd.read_excel(excel_path, sheet_name=sheet_name)
    except Exception as e:
        row["observaciones"] = f"error_lectura_hoja={e}"
        row["decision_preliminar_du"] = "revisar"
        return row

    row["n_filas"] = int(len(df))
    row["n_columnas"] = int(len(df.columns))
    row["columnas"] = [str(c) for c in df.columns]
    row["clasificacion_hoja"] = classify_sheet(sheet_name, row["columnas"])
    row["nivel_agregacion_observado"] = detect_aggregation_level(row["columnas"], sheet_name)

    if row["n_columnas"] > 0:
        empty_cols = [str(c) for c in df.columns if df[c].isna().all()]
        row["columnas_totalmente_vacias"] = empty_cols

        sample_df = df.head(PROFILE_ROWS).copy()
        row["columnas_top_no_nulas"] = top_non_null_columns(sample_df)

        cols = row["columnas"]

        row["columnas_candidatas_estado"] = candidate_columns(
            cols, ["estado", "cve_estado", "entidad", "nom_ent", "cve_ent"]
        )
        row["columnas_candidatas_municipio"] = candidate_columns(
            cols, ["municipio", "cve_municipio", "nom_mun", "cve_mun"]
        )
        row["columnas_candidatas_coordenadas"] = candidate_columns(
            cols, ["x_", "y_", "lat", "lon", "coord", "coordenada", "utm"]
        )
        row["columnas_candidatas_anio"] = candidate_columns(
            cols, ["anio", "año", "ano", "year", "periodo", "ciclo"]
        )
        row["columnas_candidatas_muestreo"] = candidate_columns(
            cols, ["muestre", "sitio", "conglomerado", "upmid", "idconglomerado", "estatus"]
        )
        row["columnas_candidatas_agregacion"] = candidate_columns(
            cols, [
                "superficie",
                "area",
                "ha",
                "hect",
                "ecosistema",
                "formacion",
                "total",
                "porcentaje",
                "promedio",
                "media",
                "indicador",
                "forestal",
                "deforest",
            ]
        )

    notes = []

    if row["n_filas"] == 0:
        notes.append("hoja_sin_filas")

    if row["n_columnas"] == 0:
        notes.append("hoja_sin_columnas")

    if len(row["columnas_totalmente_vacias"]) > 0:
        notes.append(f"cols_vacias={len(row['columnas_totalmente_vacias'])}")

    if row["clasificacion_hoja"] == "desconocido":
        notes.append("clasificacion_hoja_desconocida")

    if row["nivel_agregacion_observado"] == "desconocido":
        notes.append("nivel_agregacion_desconocido")

    row["observaciones"] = "; ".join(notes)

    row["utilidad_metodologica_preliminar"] = infer_methodological_use(
        product=row["producto_detectado"],
        format_group="tabular",
        aggregation_level=row["nivel_agregacion_observado"],
    )

    row["decision_preliminar_du"] = infer_preliminary_decision(
        product=row["producto_detectado"],
        format_group="tabular",
        observations=row["observaciones"],
    )

    return row


def profile_excel_workbook(excel_path: Path) -> List[Dict[str, object]]:
    rows = []

    try:
        xls = pd.ExcelFile(excel_path)
        sheet_names = xls.sheet_names
    except Exception as e:
        return [{
            "tipo_fila": "archivo_error",
            "archivo": excel_path.name,
            "ruta": str(excel_path),
            "tamano_mb": file_size_mb(excel_path),
            "ciclo_detectado": detect_cycle(str(excel_path)),
            "producto_detectado": detect_product(str(excel_path)),
            "hoja": None,
            "clasificacion_hoja": None,
            "nivel_agregacion_observado": None,
            "n_filas": None,
            "n_columnas": None,
            "columnas": [],
            "columnas_top_no_nulas": [],
            "columnas_totalmente_vacias": [],
            "columnas_candidatas_estado": [],
            "columnas_candidatas_municipio": [],
            "columnas_candidatas_coordenadas": [],
            "columnas_candidatas_anio": [],
            "columnas_candidatas_muestreo": [],
            "columnas_candidatas_agregacion": [],
            "utilidad_metodologica_preliminar": "revisar_utilidad",
            "decision_preliminar_du": "revisar",
            "observaciones": f"error_abrir_workbook={e}",
        }]

    product = detect_product(str(excel_path))
    cycle = detect_cycle(str(excel_path))

    rows.append({
        "tipo_fila": "archivo",
        "archivo": excel_path.name,
        "ruta": str(excel_path),
        "tamano_mb": file_size_mb(excel_path),
        "ciclo_detectado": cycle,
        "producto_detectado": product,
        "hoja": None,
        "clasificacion_hoja": None,
        "nivel_agregacion_observado": None,
        "n_filas": None,
        "n_columnas": len(sheet_names),
        "columnas": sheet_names,
        "columnas_top_no_nulas": [],
        "columnas_totalmente_vacias": [],
        "columnas_candidatas_estado": [],
        "columnas_candidatas_municipio": [],
        "columnas_candidatas_coordenadas": [],
        "columnas_candidatas_anio": [],
        "columnas_candidatas_muestreo": [],
        "columnas_candidatas_agregacion": [],
        "utilidad_metodologica_preliminar": infer_methodological_use(product, "tabular"),
        "decision_preliminar_du": infer_preliminary_decision(product, "tabular"),
        "observaciones": "",
    })

    for sheet in sheet_names:
        rows.append(profile_excel_sheet(excel_path, sheet))

    return rows


def build_excel_inventory() -> pd.DataFrame:
    excel_files = sorted(
        [p for p in ROOT_DIR.rglob("*") if p.is_file() and p.suffix.lower() in EXCEL_EXTENSIONS]
    )

    all_rows = []

    for path in excel_files:
        print(f"  Excel: {path.name}")
        all_rows.extend(profile_excel_workbook(path))

    flat_rows = []

    for r in all_rows:
        flat_rows.append({
            "tipo_fila": r["tipo_fila"],
            "archivo": r["archivo"],
            "ruta": r["ruta"],
            "tamano_mb": r["tamano_mb"],
            "ciclo_detectado": r["ciclo_detectado"],
            "producto_detectado": r["producto_detectado"],
            "hoja": r["hoja"],
            "clasificacion_hoja": r["clasificacion_hoja"],
            "nivel_agregacion_observado": r["nivel_agregacion_observado"],
            "n_filas": r["n_filas"],
            "n_columnas": r["n_columnas"],
            "columnas": safe_json(r["columnas"]),
            "columnas_top_no_nulas": safe_json(r["columnas_top_no_nulas"]),
            "columnas_totalmente_vacias": safe_json(r["columnas_totalmente_vacias"]),
            "columnas_candidatas_estado": safe_json(r["columnas_candidatas_estado"]),
            "columnas_candidatas_municipio": safe_json(r["columnas_candidatas_municipio"]),
            "columnas_candidatas_coordenadas": safe_json(r["columnas_candidatas_coordenadas"]),
            "columnas_candidatas_anio": safe_json(r["columnas_candidatas_anio"]),
            "columnas_candidatas_muestreo": safe_json(r["columnas_candidatas_muestreo"]),
            "columnas_candidatas_agregacion": safe_json(r["columnas_candidatas_agregacion"]),
            "utilidad_metodologica_preliminar": r["utilidad_metodologica_preliminar"],
            "decision_preliminar_du": r["decision_preliminar_du"],
            "observaciones": r["observaciones"],
        })

    return pd.DataFrame(flat_rows)


# =========================================================
# 5) DU-02 PERFIL PRIORITARIO
# =========================================================

def top_values(series: pd.Series, n: int = TOP_N) -> Dict[str, int]:
    vals = series.dropna().astype(str).str.strip()
    vals = vals[vals != ""]
    return vals.value_counts().head(n).to_dict()


def first_rows_sample(df: pd.DataFrame, n: int = SAMPLE_ROWS) -> List[Dict[str, object]]:
    sample = df.head(n).copy()
    sample = sample.astype("object").where(sample.notna(), "")
    return sample.astype(str).to_dict(orient="records")


def profile_priority_sheet(excel_path: Path, sheet_name: str) -> Dict[str, object]:
    row = {
        "tipo_fila": "hoja_prioritaria",
        "archivo": excel_path.name,
        "ruta": str(excel_path),
        "ciclo_detectado": detect_cycle(str(excel_path)),
        "producto_detectado": detect_product(str(excel_path)),
        "hoja": sheet_name,
        "nivel_agregacion_observado": None,
        "n_filas": None,
        "n_columnas": None,
        "columnas": [],
        "columnas_candidatas_estado": [],
        "columnas_candidatas_municipio": [],
        "columnas_candidatas_coordenadas": [],
        "columnas_candidatas_anio": [],
        "columnas_candidatas_superficie": [],
        "columnas_candidatas_deforestacion": [],
        "columnas_candidatas_indicador_forestal": [],
        "n_columnas_totalmente_vacias": None,
        "columnas_totalmente_vacias": [],
        "n_columnas_con_50pct_nulos_o_mas": None,
        "columnas_con_50pct_nulos_o_mas": [],
        "primeras_filas_muestra": [],
        "top_valores_estado": {},
        "top_valores_anio": {},
        "top_valores_muestreo": {},
        "utilidad_metodologica_preliminar": None,
        "decision_preliminar_du": None,
        "observaciones": "",
    }

    try:
        df = pd.read_excel(excel_path, sheet_name=sheet_name)
    except Exception as e:
        row["observaciones"] = f"error_lectura_hoja={e}"
        row["decision_preliminar_du"] = "revisar"
        return row

    row["n_filas"] = int(len(df))
    row["n_columnas"] = int(len(df.columns))
    row["columnas"] = [str(c) for c in df.columns]

    cols = row["columnas"]

    row["columnas_candidatas_estado"] = candidate_columns(
        cols, ["cve_estado", "estado", "cve_ent", "nom_ent", "entidad"]
    )
    row["columnas_candidatas_municipio"] = candidate_columns(
        cols, ["cve_municipio", "municipio", "cve_mun", "nom_mun"]
    )
    row["columnas_candidatas_coordenadas"] = candidate_columns(
        cols, ["x_", "y_", "lat", "lon", "coord", "utm"]
    )
    row["columnas_candidatas_anio"] = candidate_columns(
        cols, ["anio", "año", "ano", "year", "periodo", "ciclo"]
    )
    row["columnas_candidatas_superficie"] = candidate_columns(
        cols, ["superficie", "area", "ha", "hect"]
    )
    row["columnas_candidatas_deforestacion"] = candidate_columns(
        cols, ["deforest", "incertid", "limite", "superior", "inferior"]
    )
    row["columnas_candidatas_indicador_forestal"] = candidate_columns(
        cols,
        [
            "forest",
            "cobertura",
            "volumen",
            "densidad",
            "estructura",
            "composicion",
            "arbol",
            "existencia",
            "incremento",
            "ecosistema",
            "formacion",
            "vegetacion",
        ],
    )

    row["nivel_agregacion_observado"] = detect_aggregation_level(cols, sheet_name)

    if row["n_columnas"] > 0:
        empty_cols = [str(c) for c in df.columns if df[c].isna().all()]
        row["columnas_totalmente_vacias"] = empty_cols
        row["n_columnas_totalmente_vacias"] = len(empty_cols)

        prof_df = df.head(PROFILE_ROWS).copy()

        high_null_cols = []
        for c in prof_df.columns:
            null_pct = prof_df[c].isna().mean() * 100.0
            if null_pct >= 50.0:
                high_null_cols.append(str(c))

        row["columnas_con_50pct_nulos_o_mas"] = high_null_cols
        row["n_columnas_con_50pct_nulos_o_mas"] = len(high_null_cols)

        row["primeras_filas_muestra"] = first_rows_sample(df, SAMPLE_ROWS)

        muestreo_cols = candidate_columns(
            cols, ["muestre", "sitio", "conglomerado", "upmid", "idconglomerado", "estatus", "tipo_cgl"]
        )

        if row["columnas_candidatas_estado"]:
            try:
                row["top_valores_estado"] = top_values(df[row["columnas_candidatas_estado"][0]])
            except Exception:
                row["top_valores_estado"] = {}

        if row["columnas_candidatas_anio"]:
            try:
                row["top_valores_anio"] = top_values(df[row["columnas_candidatas_anio"][0]])
            except Exception:
                row["top_valores_anio"] = {}

        if muestreo_cols:
            try:
                row["top_valores_muestreo"] = top_values(df[muestreo_cols[0]])
            except Exception:
                row["top_valores_muestreo"] = {}

    notes = []

    if row["n_filas"] == 0:
        notes.append("hoja_sin_filas")

    if row["nivel_agregacion_observado"] == "desconocido":
        notes.append("nivel_agregacion_desconocido")

    if row["n_columnas_totalmente_vacias"] and row["n_columnas_totalmente_vacias"] > 0:
        notes.append(f"cols_totalmente_vacias={row['n_columnas_totalmente_vacias']}")

    if row["n_columnas_con_50pct_nulos_o_mas"] and row["n_columnas_con_50pct_nulos_o_mas"] > 0:
        notes.append(f"cols_50pct_nulos={row['n_columnas_con_50pct_nulos_o_mas']}")

    row["observaciones"] = "; ".join(notes)

    row["utilidad_metodologica_preliminar"] = infer_methodological_use(
        product=row["producto_detectado"],
        format_group="tabular",
        aggregation_level=row["nivel_agregacion_observado"],
    )

    row["decision_preliminar_du"] = infer_preliminary_decision(
        product=row["producto_detectado"],
        format_group="tabular",
        observations=row["observaciones"],
    )

    return row


def profile_priority_workbook(excel_path: Path) -> List[Dict[str, object]]:
    rows = []

    try:
        xls = pd.ExcelFile(excel_path)
        sheet_names = xls.sheet_names
    except Exception as e:
        return [{
            "tipo_fila": "archivo_error",
            "archivo": excel_path.name,
            "ruta": str(excel_path),
            "ciclo_detectado": detect_cycle(str(excel_path)),
            "producto_detectado": detect_product(str(excel_path)),
            "hoja": None,
            "nivel_agregacion_observado": None,
            "n_filas": None,
            "n_columnas": None,
            "columnas": [],
            "columnas_candidatas_estado": [],
            "columnas_candidatas_municipio": [],
            "columnas_candidatas_coordenadas": [],
            "columnas_candidatas_anio": [],
            "columnas_candidatas_superficie": [],
            "columnas_candidatas_deforestacion": [],
            "columnas_candidatas_indicador_forestal": [],
            "n_columnas_totalmente_vacias": None,
            "columnas_totalmente_vacias": [],
            "n_columnas_con_50pct_nulos_o_mas": None,
            "columnas_con_50pct_nulos_o_mas": [],
            "primeras_filas_muestra": [],
            "top_valores_estado": {},
            "top_valores_anio": {},
            "top_valores_muestreo": {},
            "utilidad_metodologica_preliminar": "revisar_utilidad",
            "decision_preliminar_du": "revisar",
            "observaciones": f"error_abrir_workbook={e}",
        }]

    product = detect_product(str(excel_path))
    cycle = detect_cycle(str(excel_path))

    rows.append({
        "tipo_fila": "archivo",
        "archivo": excel_path.name,
        "ruta": str(excel_path),
        "ciclo_detectado": cycle,
        "producto_detectado": product,
        "hoja": None,
        "nivel_agregacion_observado": None,
        "n_filas": None,
        "n_columnas": len(sheet_names),
        "columnas": sheet_names,
        "columnas_candidatas_estado": [],
        "columnas_candidatas_municipio": [],
        "columnas_candidatas_coordenadas": [],
        "columnas_candidatas_anio": [],
        "columnas_candidatas_superficie": [],
        "columnas_candidatas_deforestacion": [],
        "columnas_candidatas_indicador_forestal": [],
        "n_columnas_totalmente_vacias": None,
        "columnas_totalmente_vacias": [],
        "n_columnas_con_50pct_nulos_o_mas": None,
        "columnas_con_50pct_nulos_o_mas": [],
        "primeras_filas_muestra": [],
        "top_valores_estado": {},
        "top_valores_anio": {},
        "top_valores_muestreo": {},
        "utilidad_metodologica_preliminar": infer_methodological_use(product, "tabular"),
        "decision_preliminar_du": infer_preliminary_decision(product, "tabular"),
        "observaciones": "",
    })

    for sheet in sheet_names:
        rows.append(profile_priority_sheet(excel_path, sheet))

    return rows


def build_priority_profile() -> pd.DataFrame:
    target_files = []

    for p in ROOT_DIR.rglob("*.xlsx"):
        if p.name in TARGET_WORKBOOKS:
            target_files.append(p)

    target_files = sorted(target_files)
    all_rows = []

    for path in target_files:
        print(f"  Prioritario: {path.name}")
        all_rows.extend(profile_priority_workbook(path))

    flat_rows = []

    for r in all_rows:
        flat_rows.append({
            "tipo_fila": r["tipo_fila"],
            "archivo": r["archivo"],
            "ruta": r["ruta"],
            "ciclo_detectado": r["ciclo_detectado"],
            "producto_detectado": r["producto_detectado"],
            "hoja": r["hoja"],
            "nivel_agregacion_observado": r["nivel_agregacion_observado"],
            "n_filas": r["n_filas"],
            "n_columnas": r["n_columnas"],
            "columnas": safe_json(r["columnas"]),
            "columnas_candidatas_estado": safe_json(r["columnas_candidatas_estado"]),
            "columnas_candidatas_municipio": safe_json(r["columnas_candidatas_municipio"]),
            "columnas_candidatas_coordenadas": safe_json(r["columnas_candidatas_coordenadas"]),
            "columnas_candidatas_anio": safe_json(r["columnas_candidatas_anio"]),
            "columnas_candidatas_superficie": safe_json(r["columnas_candidatas_superficie"]),
            "columnas_candidatas_deforestacion": safe_json(r["columnas_candidatas_deforestacion"]),
            "columnas_candidatas_indicador_forestal": safe_json(r["columnas_candidatas_indicador_forestal"]),
            "n_columnas_totalmente_vacias": r["n_columnas_totalmente_vacias"],
            "columnas_totalmente_vacias": safe_json(r["columnas_totalmente_vacias"]),
            "n_columnas_con_50pct_nulos_o_mas": r["n_columnas_con_50pct_nulos_o_mas"],
            "columnas_con_50pct_nulos_o_mas": safe_json(r["columnas_con_50pct_nulos_o_mas"]),
            "primeras_filas_muestra": safe_json(r["primeras_filas_muestra"]),
            "top_valores_estado": safe_json(r["top_valores_estado"]),
            "top_valores_anio": safe_json(r["top_valores_anio"]),
            "top_valores_muestreo": safe_json(r["top_valores_muestreo"]),
            "utilidad_metodologica_preliminar": r["utilidad_metodologica_preliminar"],
            "decision_preliminar_du": r["decision_preliminar_du"],
            "observaciones": r["observaciones"],
        })

    return pd.DataFrame(flat_rows)


# =========================================================
# 6) RESUMEN GLOBAL DU
# =========================================================

def build_summary(
    file_inventory: pd.DataFrame,
    excel_inventory: pd.DataFrame,
    priority_profile: pd.DataFrame,
) -> pd.DataFrame:
    rows = []

    def add(metric: str, value: object, detail: object = ""):
        rows.append({
            "metrica": metric,
            "valor": value,
            "detalle": detail if isinstance(detail, str) else safe_json(detail),
        })

    add("root_dir", str(ROOT_DIR))
    add("out_dir", str(OUT_DIR))
    add("total_archivos_detectados", len(file_inventory))

    if not file_inventory.empty:
        add("archivos_por_grupo_formato", "", file_inventory["grupo_formato"].value_counts(dropna=False).to_dict())
        add("archivos_por_extension", "", file_inventory["extension"].value_counts(dropna=False).to_dict())
        add("archivos_por_producto_detectado", "", file_inventory["producto_detectado"].value_counts(dropna=False).to_dict())
        add("archivos_por_ciclo_detectado", "", file_inventory["ciclo_detectado"].value_counts(dropna=False).to_dict())
        add("decisiones_preliminares_archivo", "", file_inventory["decision_preliminar_du"].value_counts(dropna=False).to_dict())

        shp_rows = file_inventory[file_inventory["extension"] == ".shp"].copy()
        add("shapefiles_detectados", len(shp_rows))

        if not shp_rows.empty:
            add("shapefiles_completos_basicos", int((shp_rows["shapefile_completo_basico"] == True).sum()))
            add("shapefiles_incompletos_basicos", int((shp_rows["shapefile_completo_basico"] == False).sum()))

    if not excel_inventory.empty:
        excel_files = excel_inventory[excel_inventory["tipo_fila"] == "archivo"]
        excel_sheets = excel_inventory[excel_inventory["tipo_fila"] == "hoja"]

        add("workbooks_excel_analizados", len(excel_files))
        add("hojas_excel_perfiladas", len(excel_sheets))

        if not excel_sheets.empty:
            add("clasificacion_hojas_excel", "", excel_sheets["clasificacion_hoja"].value_counts(dropna=False).to_dict())
            add("niveles_agregacion_excel", "", excel_sheets["nivel_agregacion_observado"].value_counts(dropna=False).to_dict())

    if not priority_profile.empty:
        priority_files = priority_profile[priority_profile["tipo_fila"] == "archivo"]
        priority_sheets = priority_profile[priority_profile["tipo_fila"] == "hoja_prioritaria"]

        add("workbooks_prioritarios_analizados", len(priority_files))
        add("hojas_prioritarias_perfiladas", len(priority_sheets))

        if not priority_sheets.empty:
            add("niveles_agregacion_prioritarios", "", priority_sheets["nivel_agregacion_observado"].value_counts(dropna=False).to_dict())
            add("decisiones_preliminares_prioritarias", "", priority_sheets["decision_preliminar_du"].value_counts(dropna=False).to_dict())

    revisar_archivos = 0
    revisar_excel = 0
    revisar_prioridad = 0

    if not file_inventory.empty and "decision_preliminar_du" in file_inventory.columns:
        revisar_archivos = int((file_inventory["decision_preliminar_du"] == "revisar").sum())

    if not excel_inventory.empty and "decision_preliminar_du" in excel_inventory.columns:
        revisar_excel = int((excel_inventory["decision_preliminar_du"] == "revisar").sum())

    if not priority_profile.empty and "decision_preliminar_du" in priority_profile.columns:
        revisar_prioridad = int((priority_profile["decision_preliminar_du"] == "revisar").sum())

    add("archivos_en_revisar", revisar_archivos)
    add("filas_excel_en_revisar", revisar_excel)
    add("filas_prioritarias_en_revisar", revisar_prioridad)

    if revisar_archivos == 0:
        estado = "cerrable_con_reports_actuales"
        detalle = "No hay archivos con decisión preliminar revisar en el inventario general."
    else:
        estado = "en_revision"
        detalle = "Existen archivos con decisión preliminar revisar; validar antes de cerrar DU."

    add("estado_du_infys", estado, detalle)

    return pd.DataFrame(rows)


# =========================================================
# 7) PIPELINE PRINCIPAL
# =========================================================

def main():
    print("\nINFyS | Data Understanding consolidado")
    print(f"Directorio raíz: {ROOT_DIR}")
    print(f"Directorio reports: {OUT_DIR}")

    if not ROOT_DIR.exists():
        raise FileNotFoundError(f"No existe ROOT_DIR: {ROOT_DIR}")

    print("\n[1/4] Generando inventario general multiformato...")
    file_inventory = build_file_inventory()
    file_inventory.to_csv(OUT_FILE_INVENTORY, index=False, encoding="utf-8-sig")
    print(f"  Archivo generado: {OUT_FILE_INVENTORY}")

    print("\n[2/4] Generando inventario de workbooks y hojas Excel...")
    excel_inventory = build_excel_inventory()
    excel_inventory.to_csv(OUT_EXCEL_INVENTORY, index=False, encoding="utf-8-sig")
    print(f"  Archivo generado: {OUT_EXCEL_INVENTORY}")

    print("\n[3/4] Generando perfil de workbooks prioritarios...")
    priority_profile = build_priority_profile()
    priority_profile.to_csv(OUT_PRIORITY_PROFILE, index=False, encoding="utf-8-sig")
    print(f"  Archivo generado: {OUT_PRIORITY_PROFILE}")

    print("\n[4/4] Generando resumen global DU...")
    summary = build_summary(file_inventory, excel_inventory, priority_profile)
    summary.to_csv(OUT_SUMMARY, index=False, encoding="utf-8-sig")
    print(f"  Archivo generado: {OUT_SUMMARY}")

    print("\n=== RESUMEN DE EJECUCIÓN ===")
    print(f"Archivos detectados: {len(file_inventory)}")

    if not excel_inventory.empty:
        print(f"Filas inventario Excel: {len(excel_inventory)}")

    if not priority_profile.empty:
        print(f"Filas perfil prioritario: {len(priority_profile)}")

    print("\nDU INFyS generado correctamente.")
    print("Siguiente paso: revisar los reports generados antes de pasar a DP.")


if __name__ == "__main__":
    main()