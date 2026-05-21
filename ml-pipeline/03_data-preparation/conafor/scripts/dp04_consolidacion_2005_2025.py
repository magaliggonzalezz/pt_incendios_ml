# -*- coding: utf-8 -*-
"""
CONAFOR | DP04 - Consolidación histórica 2005-2025

Entradas
--------
1) Dataset integrado 2015-2025 generado en DP03:
   - conafor_eventos_2015_2025_integrado.csv

2) SHP histórico de puntos CONAFOR:
   - historico_incendios_activos_2001-2025.shp

3) Catálogo INEGI de municipios:
   - AGEEML_utf8.csv

Salidas
-------
- datasets/conafor_eventos_2005_2025_consolidado.csv
- reports/dp04_resumen_consolidacion_2005_2025.csv

Objetivo
--------
Construir una base CONAFOR consolidada 2005-2025:

- 2005-2014: registros provenientes del SHP histórico.
- 2015-2025: registros integrados tabular + SHP, ya cerrados en DP03.

Notas metodológicas
-------------------
- Este script pertenece a Data Preparation.
- No realiza modelado, escalado, PCA ni clustering.
- No vuelve a hacer match tabular-SHP.
- No reinvierte coordenadas.
- Conserva trazabilidad mínima de DP03.
- Complementa claves geográficas con catálogo INEGI cuando es posible.
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

PATH_INTEGRADO_2015_2025 = (
    BASE_DIR
    / "03_data-preparation"
    / "conafor"
    / "datasets"
    / "conafor_eventos_2015_2025_integrado.csv"
)

PATH_SHP_PUNTOS = (
    BASE_DIR
    / "01_raw-data"
    / "conafor"
    / "historico_incendios_2001-2025"
    / "historico_incendios_activos_2001-2025.shp"
)

PATH_CATALOGO_MUN = (
    BASE_DIR
    / "01_raw-data"
    / "inegi"
    / "catun_municipio"
    / "AGEEML_utf8.csv"
)

OUT_DIR = BASE_DIR / "03_data-preparation" / "conafor"
OUT_DATASETS = OUT_DIR / "datasets"
OUT_REPORTS = OUT_DIR / "reports"

OUT_DATASETS.mkdir(parents=True, exist_ok=True)
OUT_REPORTS.mkdir(parents=True, exist_ok=True)

OUT_CONSOLIDADO = OUT_DATASETS / "conafor_eventos_2005_2025_consolidado.csv"
OUT_RESUMEN = OUT_REPORTS / "dp04_resumen_consolidacion_2005_2025.csv"

ANIO_HIST_MIN = 2005
ANIO_HIST_MAX = 2014
ANIO_FULL_MIN = 2005
ANIO_FULL_MAX = 2025

MEX_BBOX = {
    "min_lon": -118.366667,
    "min_lat": 14.533334,
    "max_lon": -86.708334,
    "max_lat": 32.716667,
}


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
# NORMALIZACIÓN
# ============================================================

def strip_accents(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", text)
    return "".join(ch for ch in normalized if not unicodedata.combining(ch))


def repair_mojibake(value: Any) -> Any:
    if pd.isna(value):
        return pd.NA

    s = str(value)

    # Casos típicos: MÃ©xico, MichoacÃ¡n, QuerÃ©taro, Ãlamos
    if any(token in s for token in ["Ã", "Â", "�"]):
        for encoding in ["latin1", "cp1252"]:
            try:
                repaired = s.encode(encoding).decode("utf-8")
                return repaired
            except Exception:
                continue

    return s


def normalize_column_name(name: Any) -> str:
    if pd.isna(name):
        return ""

    s = str(name).strip()
    s = strip_accents(s).lower()
    s = re.sub(r"[\s/\\\-]+", "_", s)
    s = re.sub(r"[^a-z0-9_]", "", s)
    s = re.sub(r"_+", "_", s).strip("_")
    return s


def normalize_base_text(value: Any) -> Any:
    """
    Normaliza texto para comparación interna:
    - repara mojibake;
    - quita acentos;
    - convierte a minúsculas;
    - limpia espacios.

    Esta función se usa para empatar contra el catálogo INEGI.
    """
    if pd.isna(value):
        return pd.NA

    s = repair_mojibake(value)
    s = str(s).strip()

    if not s or s.lower() in {"nan", "nan.0", "<na>", "none"}:
        return pd.NA

    s = strip_accents(s).lower()
    s = re.sub(r"\s+", " ", s).strip()

    return s


def normalize_estado_value(value: Any) -> Any:
    s = normalize_base_text(value)
    if pd.isna(s):
        return pd.NA

    replacements = {
        "distrito federal": "ciudad de mexico",
        "df": "ciudad de mexico",
        "cdmx": "ciudad de mexico",
        "edo mexico": "mexico",
        "edo. mexico": "mexico",
        "estado de mexico": "mexico",
        "tlaxacala": "tlaxcala",
        "coahuila": "coahuila de zaragoza",
        "veracruz": "veracruz de ignacio de la llave",
        "michoacan": "michoacan de ocampo",
        "san luis potisi": "san luis potosi",
        "san luis potosí": "san luis potosi",
    }

    return replacements.get(s, s)


def normalize_municipio_value(value: Any) -> Any:
    s = normalize_base_text(value)
    if pd.isna(s):
        return pd.NA

    s = s.replace("cd. ", "ciudad ")
    s = s.replace("cd ", "ciudad ")
    s = s.replace("mpio.", "")
    s = s.replace("mpio ", "")
    s = re.sub(r"\s+", " ", s).strip()
    return s


MUNICIPIO_ALIAS = {
    ("chiapas", "cintalapa"): "cintalapa de figueroa",
    ("chihuahua", "batopilas"): "batopilas de manuel gomez morin",
    ("mexico", "acambay"): "acambay de ruiz castaneda",
    ("mexico", "san bartolo morelos"): "morelos",
    ("mexico", "naucalpan"): "naucalpan de juarez",
    ("guanajuato", "silao"): "silao de la victoria",
    ("guanajuato", "san jose iturbide"): "san jose de iturbide",
    ("guerrero", "taxco"): "taxco de alarcon",
    ("guerrero", "huitzuco"): "huitzuco de los figueroa",
    ("guerrero", "alcozauca"): "alcozauca de guerrero",
    ("guerrero", "tecuanapa"): "tecoanapa",
    ("jalisco", "cuautitlan"): "cuautitlan de garcia barragan",
    ("michoacan de ocampo", "coalcoman"): "coalcoman de vazquez pallares",
    ("michoacan de ocampo", "ario de rosales"): "ario",
    ("michoacan de ocampo", "huacana"): "la huacana",
    ("michoacan de ocampo", "villa madero"): "madero",
    ("michoacan de ocampo", "villa jimenez"): "jimenez",
    ("morelos", "tlaltizapan"): "tlaltizapan de zapata",
    ("nayarit", "el nayar"): "del nayar",
    ("nuevo leon", "gral. zaragoza"): "general zaragoza",
    ("nuevo leon", "dr. arroyo"): "doctor arroyo",
    ("nuevo leon", "dr arroyo"): "doctor arroyo",
    ("oaxaca", "h. cd. de tlaxiaco"): "heroica ciudad de tlaxiaco",
    ("oaxaca", "ciudad de tlaxiaco"): "heroica ciudad de tlaxiaco",
    ("oaxaca", "heroica ciudad de tlaxiaco"): "heroica ciudad de tlaxiaco",
    ("oaxaca", "h. ciudad de tlaxiaco"): "heroica ciudad de tlaxiaco",
    ("oaxaca", "capulalpan de mendez"): "capulalpam de mendez",
    ("oaxaca", "santa ma. chimalapa"): "santa maria chimalapa",
    ("oaxaca", "nochixtlan"): "asuncion nochixtlan",
    ("puebla", "tlatlauqitepec"): "tlatlauquitepec",
    ("puebla", "felipe angeles"): "general felipe angeles",
    ("puebla", "chalchicomula"): "chalchicomula de sesma",
    ("puebla", "san felipe teotlancingo"): "san felipe teotlalcingo",
    ("puebla", "tepatlaxco"): "tepatlaxco de hidalgo",
    ("queretaro", "jalpan de la sierra"): "jalpan de serra",
    ("quintana roo", "solidaridad"): "playa del carmen",
    ("san luis potosi", "ahualulco"): "ahualulco del sonido 13",
    ("sinaloa", "el rosario"): "rosario",
    ("sonora", "huachineras"): "huachinera",
    ("sonora", "nacozari"): "nacozari de garcia",
    ("tlaxcala", "contla"): "contla de juan cuamatzi",
    ("tlaxcala", "juan cuamatzi"): "contla de juan cuamatzi",
    ("tlaxcala", "tetla"): "tetla de la solidaridad",
    ("tlaxcala", "solidaridad"): "tetla de la solidaridad",
    ("tlaxcala", "san francisco"): "san francisco tetlanohcan",
    ("tlaxcala", "tetlanohcan"): "san francisco tetlanohcan",
    ("tlaxcala", "zitlaltepec"): "ziltlaltepec de trinidad sanchez santos",
    ("tlaxcala", "ziltlaltepec"): "ziltlaltepec de trinidad sanchez santos",
    ("tlaxcala", "mariano arista"): "nanacamilpa de mariano arista",
    ("tlaxcala", "nanacamilpa"): "nanacamilpa de mariano arista",
    ("tlaxcala", "miguel hidalgo"): "acuamanala de miguel hidalgo",
    ("tlaxcala", "jose maria morelos"): "mazatecochco de jose maria morelos",
    ("tlaxcala", "papalotla"): "papalotla de xicohtencatl",
    ("tlaxcala", "xicohtencatl"): "papalotla de xicohtencatl",
    ("tlaxcala", "sanctorum"): "sanctorum de lazaro cardenas",
    ("tlaxcala", "ixtacuixtla"): "ixtacuixtla de mariano matamoros",
    ("tlaxcala", "altzayanca"): "atltzayanca",
    ("tlaxcala", "teacalco"): "san jose teacalco",
    ("tlaxcala", "santa catarina"): "santa catarina ayometla",
    ("tlaxcala", "ayometla"): "santa catarina ayometla",
    ("tlaxcala", "mazatecochco"): "mazatecochco de jose maria morelos",
    ("veracruz de ignacio de la llave", "cd mendoza"): "camerino z mendoza",
    ("veracruz de ignacio de la llave", "ciudad mendoza"): "camerino z mendoza",
    ("veracruz de ignacio de la llave", "las vigas"): "las vigas de ramirez",
    ("veracruz de ignacio de la llave", "cosautlan"): "cosautlan de carvajal",
    ("veracruz de ignacio de la llave", "zacualapan"): "zacualpan",
    ("veracruz de ignacio de la llave", "tatahuicapan"): "tatahuicapan de juarez",
    ("yucatan", "tixcocob"): "tixkokob",
    ("zacatecas", "tlaltenango"): "tlaltenango de sanchez roman",
    ("zacatecas", "nochistlan"): "nochistlan de mejia",
}


def apply_municipio_alias(estado_norm: Any, municipio_norm: Any) -> Any:
    if pd.isna(estado_norm) or pd.isna(municipio_norm):
        return municipio_norm

    return MUNICIPIO_ALIAS.get((estado_norm, municipio_norm), municipio_norm)


def repair_mojibake(value: Any) -> Any:
    """
    Repara textos con mojibake típico por problemas de codificación.

    Ejemplos:
    - MÃ©xico -> México
    - MichoacÃ¡n -> Michoacán
    - QuerÃ©taro -> Querétaro
    - Mar�a -> María

    Si el texto no tiene problemas, lo devuelve igual.
    """
    if pd.isna(value):
        return pd.NA

    s = str(value)

    # Reparación iterativa para casos tipo MÃ©xico, MichoacÃ¡n, QuerÃ©taro.
    for _ in range(3):
        if not any(token in s for token in ["Ã", "Â", "�"]):
            break

        repaired = s

        for encoding in ["latin1", "cp1252"]:
            try:
                repaired = s.encode(encoding).decode("utf-8")
                break
            except Exception:
                continue

        if repaired == s:
            break

        s = repaired

    # Correcciones puntuales que no siempre se arreglan con encode/decode.
    s = s.replace("Mar�a", "María")
    s = s.replace("Jos�", "José")
    s = s.replace("Gonz�lez", "González")
    s = s.replace("S�nchez", "Sánchez")
    s = s.replace("M�xico", "México")
    s = s.replace("Potos�", "Potosí")
    s = s.replace("Le�n", "León")
    s = s.replace("Yucat�n", "Yucatán")
    s = s.replace("Michoac�n", "Michoacán")
    s = s.replace("Quer�taro", "Querétaro")

    return s


def safe_string(value: Any) -> Any:
    """
    Convierte valores a texto limpio y repara mojibake antes de guardar.
    Esta función afecta el texto visible en el CSV final.
    """
    if pd.isna(value):
        return pd.NA

    s = repair_mojibake(value)
    s = str(s).strip()

    if not s or s.lower() in {"nan", "nan.0", "<na>", "none"}:
        return pd.NA

    return s


def normalize_code(value: Any, width: int) -> Any:
    if pd.isna(value):
        return pd.NA

    s = str(value).strip()

    if not s or s.lower() in {"nan", "nan.0", "<na>", "none"}:
        return pd.NA

    num = pd.to_numeric(pd.Series([s]), errors="coerce").iloc[0]
    if pd.notna(num):
        try:
            s = str(int(num))
        except Exception:
            s = str(s)

    digits = re.sub(r"\D", "", s)

    if not digits:
        return pd.NA

    # Si llega un valor compuesto tipo CVEGEO y se está pidiendo CVE_MUN,
    # se conservan los últimos 3 dígitos.
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


def first_existing_col(df: pd.DataFrame, candidates: list[str]) -> str | None:
    cols = set(df.columns)
    for c in candidates:
        if c in cols:
            return c
    return None


def validate_bbox_mexico(lat: pd.Series, lon: pd.Series) -> pd.Series:
    lat_num = pd.to_numeric(lat, errors="coerce")
    lon_num = pd.to_numeric(lon, errors="coerce")

    return (
        lat_num.between(MEX_BBOX["min_lat"], MEX_BBOX["max_lat"], inclusive="both")
        & lon_num.between(MEX_BBOX["min_lon"], MEX_BBOX["max_lon"], inclusive="both")
    )


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

        s = normalize_base_text(value)
        if pd.isna(s):
            continue

        if s in IMPACTO_MAP and pd.isna(impacto):
            impacto = IMPACTO_MAP[s]

        if s in REGIMEN_MAP and pd.isna(regimen):
            regimen = REGIMEN_MAP[s]

    return impacto, regimen


# ============================================================
# LECTURA FLEXIBLE CSV
# ============================================================

def read_csv_flexible(path: Path) -> pd.DataFrame:
    encodings = ["utf-8-sig", "utf-8", "latin-1", "cp1252"]
    last_error = None

    for enc in encodings:
        try:
            return pd.read_csv(path, dtype=str, encoding=enc)
        except Exception as exc:
            last_error = exc

    raise ValueError(f"No se pudo leer el CSV: {path}\nÚltimo error: {last_error}")


def pick_first_existing(columns: list[str], candidates: list[str]) -> str | None:
    cols_set = set(columns)
    for c in candidates:
        if c in cols_set:
            return c
    return None


# ============================================================
# CATÁLOGO INEGI
# ============================================================

def read_catalog_municipios(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"No existe el catálogo de municipios: {path}")

    print("Cargando catálogo INEGI de municipios...")

    cat = read_csv_flexible(path)
    cat.columns = [normalize_column_name(c) for c in cat.columns]

    estado_col = pick_first_existing(
        list(cat.columns),
        ["nom_ent", "estado", "entidad", "nom_entidad", "nombre_entidad"],
    )
    municipio_col = pick_first_existing(
        list(cat.columns),
        ["nom_mun", "municipio", "nom_municipio", "nombre_municipio"],
    )
    cve_ent_col = pick_first_existing(
        list(cat.columns),
        ["cve_ent", "cv_ent", "clave_entidad"],
    )
    cve_mun_col = pick_first_existing(
        list(cat.columns),
        ["cve_mun", "cv_mun", "clave_municipio"],
    )
    cvegeo_col = pick_first_existing(
        list(cat.columns),
        ["cvegeo", "cve_geo"],
    )

    if estado_col is None or municipio_col is None:
        raise ValueError(
            "No se identificaron correctamente las columnas de estado/municipio en el catálogo INEGI."
        )

    cat = cat.copy()

    if cve_ent_col is None and cvegeo_col is not None:
        cat["cve_ent_tmp"] = cat[cvegeo_col].astype("string").str.extract(r"^(\d{2})", expand=False)
        cve_ent_col = "cve_ent_tmp"

    if cve_mun_col is None and cvegeo_col is not None:
        cat["cve_mun_tmp"] = cat[cvegeo_col].astype("string").str.extract(r"^\d{2}(\d{3})", expand=False)
        cve_mun_col = "cve_mun_tmp"

    if cve_ent_col is None or cve_mun_col is None:
        raise ValueError(
            "No se identificaron correctamente las claves cve_ent / cve_mun en el catálogo INEGI."
        )

    cat["estado_norm"] = cat[estado_col].map(normalize_estado_value)
    cat["municipio_norm"] = cat[municipio_col].map(normalize_municipio_value)
    cat["municipio_norm"] = [
        apply_municipio_alias(e, m)
        for e, m in zip(cat["estado_norm"], cat["municipio_norm"])
    ]

    cat["cve_ent"] = cat[cve_ent_col].map(lambda x: normalize_code(x, 2))
    cat["cve_mun"] = cat[cve_mun_col].map(lambda x: normalize_code(x, 3))

    cat = cat[
        cat["estado_norm"].notna()
        & cat["municipio_norm"].notna()
        & cat["cve_ent"].notna()
        & cat["cve_mun"].notna()
    ].copy()

    cat = cat.drop_duplicates(subset=["estado_norm", "municipio_norm", "cve_ent", "cve_mun"])

    by_state_mun = {
        (row["estado_norm"], row["municipio_norm"]): row["cve_mun"]
        for _, row in cat.iterrows()
    }

    by_ent_mun = {
        (row["cve_ent"], row["municipio_norm"]): row["cve_mun"]
        for _, row in cat.iterrows()
    }

    by_state_to_ent = (
        cat[["estado_norm", "cve_ent"]]
        .drop_duplicates(subset=["estado_norm", "cve_ent"])
        .drop_duplicates(subset=["estado_norm"])
        .set_index("estado_norm")["cve_ent"]
        .to_dict()
    )

    print(f"Índice catálogo (estado + municipio):  {len(by_state_mun):,}")
    print(f"Índice catálogo (cve_ent + municipio): {len(by_ent_mun):,}")
    print(f"Índice catálogo (estado):              {len(by_state_to_ent):,}")

    return {
        "by_state_mun": by_state_mun,
        "by_ent_mun": by_ent_mun,
        "by_state_to_ent": by_state_to_ent,
    }


def resolve_geo_keys(
    estado: Any,
    cve_ent: Any,
    municipio: Any,
    cve_mun: Any,
    catalog: dict[str, Any],
) -> tuple[Any, Any]:
    estado_norm = normalize_estado_value(estado)
    municipio_norm = normalize_municipio_value(municipio)
    municipio_norm = apply_municipio_alias(estado_norm, municipio_norm)

    cve_ent_out = normalize_code(cve_ent, 2)
    cve_mun_out = normalize_code(cve_mun, 3)

    if pd.isna(cve_ent_out) and pd.notna(estado_norm):
        cve_ent_out = catalog["by_state_to_ent"].get(estado_norm, pd.NA)

    if pd.isna(cve_mun_out) and pd.notna(municipio_norm):
        if pd.notna(cve_ent_out):
            cve_mun_out = catalog["by_ent_mun"].get((cve_ent_out, municipio_norm), pd.NA)

        if pd.isna(cve_mun_out) and pd.notna(estado_norm):
            cve_mun_out = catalog["by_state_mun"].get((estado_norm, municipio_norm), pd.NA)

    return cve_ent_out, cve_mun_out


# ============================================================
# LECTURA DATASET 2015-2025
# ============================================================

def read_integrado_2015_2025(path: Path, catalog: dict[str, Any]) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"No existe el dataset integrado 2015-2025: {path}")

    df = pd.read_csv(path, encoding="utf-8-sig", dtype=str)
    df.columns = [normalize_column_name(c) for c in df.columns]

    for col in FINAL_COLUMNS:
        if col not in df.columns:
            df[col] = pd.NA

    df = df[FINAL_COLUMNS].copy()

    # Limpieza de textos visibles heredados del integrado 2015-2025.
    # Esto corrige mojibake en registros como solo_shp que venían del DP03.
    text_cols = [
        "estado",
        "municipio",
        "region",
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
        "superficie_categoria",
        "estado_integracion",
        "clasificacion_match",
        "fuente_tabular",
        "fuente_preferente",
    ]

    for col in text_cols:
        if col in df.columns:
            df[col] = df[col].map(safe_string)

    # Normalización básica
    df["anio"] = pd.to_numeric(df["anio"], errors="coerce").astype("Int64")
    df["clave_incendio"] = df["clave_incendio"].map(normalize_clave_incendio)
    df["fecha_inicio"] = df["fecha_inicio"].map(parse_date_scalar)
    df["fecha_termino"] = df["fecha_termino"].map(parse_date_scalar)
    df["latitud"] = pd.to_numeric(df["latitud"], errors="coerce")
    df["longitud"] = pd.to_numeric(df["longitud"], errors="coerce")
    df["superficie_total_ha"] = pd.to_numeric(df["superficie_total_ha"], errors="coerce")

    cve_ent_out = []
    cve_mun_out = []

    for _, row in df.iterrows():
        cve_ent, cve_mun = resolve_geo_keys(
            estado=row.get("estado"),
            cve_ent=row.get("cve_ent"),
            municipio=row.get("municipio"),
            cve_mun=row.get("cve_mun"),
            catalog=catalog,
        )
        cve_ent_out.append(cve_ent)
        cve_mun_out.append(cve_mun)

    df["cve_ent"] = cve_ent_out
    df["cve_mun"] = cve_mun_out

    return df


# ============================================================
# LECTURA SHP HISTÓRICO 2005-2014
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
        "cveent": "cve_ent",
        "cv_ent": "cve_ent",
        "cvemun": "cve_mun",
        "cv_mun": "cve_mun",
        "nom_ent": "estado",
        "entidad": "estado",
        "nomedo": "estado",
        "edo": "estado",
        "nom_mun": "municipio",
        "nommun": "municipio",
        "muni": "municipio",
    }

    gdf = gdf.rename(columns={k: v for k, v in rename_map.items() if k in gdf.columns})

    cve_ent_src = first_existing_col(
        gdf,
        ["cve_ent", "cveent", "cv_ent", "clvent", "ent_cve", "clave_ent"],
    )
    cve_mun_src = first_existing_col(
        gdf,
        ["cve_mun", "cvemun", "cv_mun", "clvmun", "mun_cve", "clave_mun"],
    )
    estado_src = first_existing_col(
        gdf,
        ["estado", "nom_ent", "entidad", "nomedo", "edo"],
    )
    municipio_src = first_existing_col(
        gdf,
        ["municipio", "nom_mun", "nommun", "muni"],
    )

    if cve_ent_src and cve_ent_src != "cve_ent":
        gdf = gdf.rename(columns={cve_ent_src: "cve_ent"})
    if cve_mun_src and cve_mun_src != "cve_mun":
        gdf = gdf.rename(columns={cve_mun_src: "cve_mun"})
    if estado_src and estado_src != "estado":
        gdf = gdf.rename(columns={estado_src: "estado"})
    if municipio_src and municipio_src != "municipio":
        gdf = gdf.rename(columns={municipio_src: "municipio"})

    needed = [
        "clave_incendio",
        "estado",
        "municipio",
        "predio",
        "fecha_inicio",
        "fecha_termino",
        "superficie_total_ha",
        "cve_ent",
        "cve_mun",
        "region",
        "tipo_incendio",
        "tipo_vegetacion",
        "clasificac",
        "clasifi_01",
    ]

    for col in needed:
        if col not in gdf.columns:
            gdf[col] = pd.NA

    print("\nColumnas detectadas en SHP raw histórico:")
    print(f"- estado:    {estado_src if estado_src else 'no detectada'}")
    print(f"- municipio: {municipio_src if municipio_src else 'no detectada'}")
    print(f"- cve_ent:   {cve_ent_src if cve_ent_src else 'no detectada'}")
    print(f"- cve_mun:   {cve_mun_src if cve_mun_src else 'no detectada'}")

    if "geometry" in gdf.columns:
        gdf["longitud"] = gdf.geometry.x
        gdf["latitud"] = gdf.geometry.y
    else:
        if "x" in gdf.columns:
            gdf["longitud"] = pd.to_numeric(gdf["x"], errors="coerce")
        else:
            gdf["longitud"] = pd.NA

        if "y" in gdf.columns:
            gdf["latitud"] = pd.to_numeric(gdf["y"], errors="coerce")
        else:
            gdf["latitud"] = pd.NA

    gdf["clave_incendio"] = gdf["clave_incendio"].map(normalize_clave_incendio)
    gdf["fecha_inicio"] = gdf["fecha_inicio"].map(parse_date_scalar)
    gdf["fecha_termino"] = gdf["fecha_termino"].map(parse_date_scalar)
    gdf["superficie_total_ha"] = pd.to_numeric(gdf["superficie_total_ha"], errors="coerce")
    gdf["latitud"] = pd.to_numeric(gdf["latitud"], errors="coerce")
    gdf["longitud"] = pd.to_numeric(gdf["longitud"], errors="coerce")

    fi = pd.to_datetime(gdf["fecha_inicio"], errors="coerce")
    gdf["anio"] = fi.dt.year.astype("Int64")

    if "geometry" in gdf.columns:
        gdf = pd.DataFrame(gdf.drop(columns=["geometry"]))

    return gdf


def build_row_hist_shp(row: pd.Series, catalog: dict[str, Any]) -> dict[str, Any]:
    shp_impacto, shp_regimen = recover_shp_impacto_regimen(
        row.get("clasificac"),
        row.get("clasifi_01"),
    )

    estado = safe_string(row.get("estado"))
    municipio = safe_string(row.get("municipio"))

    cve_ent, cve_mun = resolve_geo_keys(
        estado=estado,
        cve_ent=row.get("cve_ent"),
        municipio=municipio,
        cve_mun=row.get("cve_mun"),
        catalog=catalog,
    )

    return {
        "anio": to_numeric_scalar(row.get("anio")),
        "clave_incendio": normalize_clave_incendio(row.get("clave_incendio")),
        "estado": estado,
        "cve_ent": cve_ent,
        "municipio": municipio,
        "cve_mun": cve_mun,
        "region": safe_string(row.get("region")),
        "latitud": to_numeric_scalar(row.get("latitud")),
        "longitud": to_numeric_scalar(row.get("longitud")),
        "fecha_inicio": parse_date_scalar(row.get("fecha_inicio")),
        "fecha_termino": parse_date_scalar(row.get("fecha_termino")),
        "deteccion": pd.NA,
        "llegada": pd.NA,
        "duracion": pd.NA,
        "duracion_categoria": pd.NA,
        "causa": pd.NA,
        "causa_especifica": pd.NA,
        "predio": safe_string(row.get("predio")),
        "regimen_fuego": shp_regimen,
        "tipo_incendio": safe_string(row.get("tipo_incendio")),
        "tipo_impacto": shp_impacto,
        "tipo_vegetacion": safe_string(row.get("tipo_vegetacion")),
        "superficie_total_ha": to_numeric_scalar(row.get("superficie_total_ha")),
        "superficie_categoria": pd.NA,
        "arbolado_adulto": pd.NA,
        "arbustivo": pd.NA,
        "herbaceo": pd.NA,
        "hojarasca": pd.NA,
        "renuevo": pd.NA,
        "estado_integracion": "historico_shp_2005_2014",
        "clasificacion_match": "historico_solo_shp",
        "score_consistencia": pd.NA,
        "coord_dist_deg": pd.NA,
        "fuente_tabular": pd.NA,
        "fuente_preferente": "shp",
    }


# ============================================================
# SALIDA Y RESUMEN
# ============================================================

def apply_final_schema(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()

    for col in FINAL_COLUMNS:
        if col not in out.columns:
            out[col] = pd.NA

    return out[FINAL_COLUMNS].copy()


def sort_output(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()

    out["_fecha_inicio_dt"] = pd.to_datetime(out["fecha_inicio"], errors="coerce")
    out["_anio_num"] = pd.to_numeric(out["anio"], errors="coerce")

    out = out.sort_values(
        by=["_anio_num", "_fecha_inicio_dt", "estado", "municipio", "clave_incendio"],
        ascending=[True, True, True, True, True],
        na_position="last",
    ).reset_index(drop=True)

    out = out.drop(columns=["_fecha_inicio_dt", "_anio_num"])

    return out


def build_summary(df_2015: pd.DataFrame, df_hist: pd.DataFrame, df_full: pd.DataFrame) -> pd.DataFrame:
    fi = pd.to_datetime(df_full["fecha_inicio"], errors="coerce")
    ft = pd.to_datetime(df_full["fecha_termino"], errors="coerce")
    anio = pd.to_numeric(df_full["anio"], errors="coerce")
    lat = pd.to_numeric(df_full["latitud"], errors="coerce")
    lon = pd.to_numeric(df_full["longitud"], errors="coerce")

    fechas_invertidas = fi.notna() & ft.notna() & (ft < fi)
    coord_fuera_bbox = ~validate_bbox_mexico(lat, lon)

    rows = [
        {"metrica": "registros_2015_2025_integrado", "valor": len(df_2015)},
        {"metrica": "registros_2005_2014_shp_historico", "valor": len(df_hist)},
        {"metrica": "registros_consolidado_2005_2025", "valor": len(df_full)},
        {"metrica": "columnas_consolidado", "valor": len(df_full.columns)},
        {"metrica": "periodo_min", "valor": int(anio.min()) if anio.notna().any() else pd.NA},
        {"metrica": "periodo_max", "valor": int(anio.max()) if anio.notna().any() else pd.NA},
        {"metrica": "fuera_periodo_2005_2025", "valor": int((~anio.between(ANIO_FULL_MIN, ANIO_FULL_MAX, inclusive="both")).fillna(True).sum())},
        {"metrica": "clave_incendio_nula", "valor": int(df_full["clave_incendio"].isna().sum())},
        {"metrica": "duplicados_clave_incendio", "valor": int(df_full["clave_incendio"].duplicated(keep=False).fillna(False).sum())},
        {"metrica": "fecha_inicio_nula", "valor": int(df_full["fecha_inicio"].isna().sum())},
        {"metrica": "fecha_termino_nula", "valor": int(df_full["fecha_termino"].isna().sum())},
        {"metrica": "fechas_invertidas", "valor": int(fechas_invertidas.sum())},
        {"metrica": "latitud_nula", "valor": int(lat.isna().sum())},
        {"metrica": "longitud_nula", "valor": int(lon.isna().sum())},
        {"metrica": "coord_fuera_bbox_mexico", "valor": int(coord_fuera_bbox.sum())},
        {"metrica": "cve_ent_nula", "valor": int(df_full["cve_ent"].isna().sum())},
        {"metrica": "cve_mun_nula", "valor": int(df_full["cve_mun"].isna().sum())},
    ]

    for value, count in df_full["estado_integracion"].value_counts(dropna=False).items():
        rows.append({
            "metrica": f"estado_integracion_{value}",
            "valor": int(count),
        })

    for value, count in df_full["clasificacion_match"].value_counts(dropna=False).items():
        rows.append({
            "metrica": f"clasificacion_match_{value}",
            "valor": int(count),
        })

    return pd.DataFrame(rows)


# ============================================================
# MAIN
# ============================================================

def main() -> None:
    print("CONAFOR | DP04 - Consolidación histórica 2005-2025")
    print("Leyendo insumos...")

    catalog = read_catalog_municipios(PATH_CATALOGO_MUN)

    print("\nLeyendo dataset integrado 2015-2025...")
    df_2015 = read_integrado_2015_2025(PATH_INTEGRADO_2015_2025, catalog)
    df_2015 = apply_final_schema(df_2015)

    print(f"Registros 2015-2025: {len(df_2015):,}")

    print(f"\nLeyendo SHP histórico y filtrando {ANIO_HIST_MIN}-{ANIO_HIST_MAX}...")
    shp_raw = read_shp_points(PATH_SHP_PUNTOS)

    shp_hist = shp_raw[
        shp_raw["anio"].between(ANIO_HIST_MIN, ANIO_HIST_MAX, inclusive="both")
    ].copy()

    rows_hist: list[dict[str, Any]] = []

    for _, row in shp_hist.iterrows():
        rows_hist.append(build_row_hist_shp(row, catalog))

    df_hist = pd.DataFrame(rows_hist)
    df_hist = apply_final_schema(df_hist)

    print(f"Registros históricos agregados desde SHP: {len(df_hist):,}")

    print("\nConstruyendo consolidado final 2005-2025...")

    df_full = pd.concat([df_hist, df_2015], ignore_index=True)
    df_full = apply_final_schema(df_full)
    df_full = sort_output(df_full)

    print("Construyendo resumen...")
    resumen = build_summary(df_2015, df_hist, df_full)

    print("Guardando salidas...")
    df_full.to_csv(OUT_CONSOLIDADO, index=False, encoding="utf-8-sig")
    resumen.to_csv(OUT_RESUMEN, index=False, encoding="utf-8-sig")

    print("\nProceso finalizado.")
    print(f"Dataset consolidado: {OUT_CONSOLIDADO}")
    print(f"Resumen:             {OUT_RESUMEN}")

    print("\nResumen rápido por estado_integracion:")
    print(df_full["estado_integracion"].value_counts(dropna=False))


if __name__ == "__main__":
    main()