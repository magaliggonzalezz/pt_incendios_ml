# -*- coding: utf-8 -*-
"""
Feature Engineering | Configuración general
-------------------------------------------
Centraliza rutas, nombres de archivos, parámetros metodológicos y columnas clave
para la fase 05_feature_engineering del proyecto de análisis espacio-temporal de
incendios forestales en México.

Este script define:
- rutas base del proyecto,
- rutas de entrada desde 04_integration,
- rutas de salida para 05_feature_engineering,
- granularidades de trabajo,
- periodo temporal del proyecto,
- llaves espaciales y temporales,
- archivos esperados de entrada y salida.

No genera datasets ni reports.
No modifica archivos de Integration.
No ejecuta modelado ni evaluación.
"""

from __future__ import annotations

from pathlib import Path


# =========================================================
# 1) CONFIGURACIÓN GENERAL DEL PROYECTO
# =========================================================

BASE_DIR = Path(r"C:\Users\Hp\OneDrive\Documentos\PT_Analisis")

PROJECT_START_DATE = "2001-01-01"
PROJECT_END_DATE = "2025-12-31"

PRIMARY_GRAIN = "municipio_dia"
SECONDARY_GRAIN = "entidad_dia"


# =========================================================
# 2) DIRECTORIOS DE ENTRADA
# =========================================================

INTEGRATION_DIR = BASE_DIR / "04_integration"
INTEGRATION_DATASETS_DIR = INTEGRATION_DIR / "datasets"
INTEGRATION_REPORTS_DIR = INTEGRATION_DIR / "reports"


# =========================================================
# 3) DIRECTORIOS DE FEATURE ENGINEERING
# =========================================================

FE_DIR = BASE_DIR / "05_feature_engineering"
FE_SCRIPTS_DIR = FE_DIR / "scripts"
FE_DATASETS_DIR = FE_DIR / "datasets"
FE_REPORTS_DIR = FE_DIR / "reports"


def ensure_fe_directories() -> None:
    """
    Crea únicamente los directorios necesarios para Feature Engineering.
    No crea archivos.
    No modifica salidas de Integration.
    """
    FE_DIR.mkdir(parents=True, exist_ok=True)
    FE_SCRIPTS_DIR.mkdir(parents=True, exist_ok=True)
    FE_DATASETS_DIR.mkdir(parents=True, exist_ok=True)
    FE_REPORTS_DIR.mkdir(parents=True, exist_ok=True)


# =========================================================
# 4) ARCHIVOS DE ENTRADA DESDE INTEGRATION
# =========================================================

PATH_CATALOGO_ENTIDADES = (
    INTEGRATION_DATASETS_DIR / "integracion_catalogo_entidades.csv"
)

PATH_CATALOGO_MUNICIPIOS = (
    INTEGRATION_DATASETS_DIR / "integracion_catalogo_municipios.csv"
)

PATH_MUNICIPIO_DIA_BASE = (
    INTEGRATION_DATASETS_DIR / "integracion_municipio_dia_base.csv"
)

PATH_ENTIDAD_DIA_BASE = (
    INTEGRATION_DATASETS_DIR / "integracion_entidad_dia_base.csv"
)

PATH_INEGI_MUNICIPIO_CONTEXTO = (
    INTEGRATION_DATASETS_DIR / "integracion_inegi_municipio_contexto.csv"
)

PATH_INEGI_ENTIDAD_CONTEXTO = (
    INTEGRATION_DATASETS_DIR / "integracion_inegi_entidad_contexto.csv"
)

PATH_INFYS_MUNICIPIO_CONTEXTO = (
    INTEGRATION_DATASETS_DIR / "integracion_infys_municipio_contexto.csv"
)

PATH_INFYS_ENTIDAD_CONTEXTO = (
    INTEGRATION_DATASETS_DIR / "integracion_infys_entidad_contexto.csv"
)


INPUT_FILES = {
    "catalogo_entidades": PATH_CATALOGO_ENTIDADES,
    "catalogo_municipios": PATH_CATALOGO_MUNICIPIOS,
    "municipio_dia_base": PATH_MUNICIPIO_DIA_BASE,
    "entidad_dia_base": PATH_ENTIDAD_DIA_BASE,
    "inegi_municipio_contexto": PATH_INEGI_MUNICIPIO_CONTEXTO,
    "inegi_entidad_contexto": PATH_INEGI_ENTIDAD_CONTEXTO,
    "infys_municipio_contexto": PATH_INFYS_MUNICIPIO_CONTEXTO,
    "infys_entidad_contexto": PATH_INFYS_ENTIDAD_CONTEXTO,
}


# =========================================================
# 5) ARCHIVOS DE SALIDA DE FEATURE ENGINEERING
# =========================================================

PATH_FE_MUNICIPIO_DIA_MATRIZ = (
    FE_DATASETS_DIR / "fe_municipio_dia_matriz.csv"
)

PATH_FE_ENTIDAD_DIA_MATRIZ = (
    FE_DATASETS_DIR / "fe_entidad_dia_matriz.csv"
)

PATH_FE_DIAGNOSTICO_VARIABLES_BASE = (
    FE_REPORTS_DIR / "fe_01_diagnostico_variables_base.csv"
)

PATH_FE_RESUMEN_VARIABLES_BASE = (
    FE_REPORTS_DIR / "fe_01_resumen_variables_base.csv"
)

PATH_FE_DICCIONARIO_VARIABLES = (
    FE_REPORTS_DIR / "fe_diccionario_variables.csv"
)

PATH_FE_VALIDACION_SALIDAS = (
    FE_REPORTS_DIR / "fe_04_validacion_salidas.csv"
)


OUTPUT_FILES = {
    "fe_municipio_dia_matriz": PATH_FE_MUNICIPIO_DIA_MATRIZ,
    "fe_entidad_dia_matriz": PATH_FE_ENTIDAD_DIA_MATRIZ,
    "diagnostico_variables_base": PATH_FE_DIAGNOSTICO_VARIABLES_BASE,
    "resumen_variables_base": PATH_FE_RESUMEN_VARIABLES_BASE,
    "diccionario_variables": PATH_FE_DICCIONARIO_VARIABLES,
    "validacion_salidas": PATH_FE_VALIDACION_SALIDAS,
}


# =========================================================
# 6) LLAVES Y COLUMNAS DE TRAZABILIDAD
# =========================================================

MUNICIPIO_KEY_COLS = [
    "cve_ent",
    "nom_ent",
    "cve_mun",
    "nom_mun",
    "cvegeo",
    "fecha",
]

ENTIDAD_KEY_COLS = [
    "cve_ent",
    "nom_ent",
    "fecha",
]

MUNICIPIO_DUPLICATE_KEY = [
    "cvegeo",
    "fecha",
]

ENTIDAD_DUPLICATE_KEY = [
    "cve_ent",
    "fecha",
]

TEMPORAL_TRACE_COLS = [
    "fecha",
    "anio",
    "mes",
    "dia",
    "dia_del_anio",
    "semana_iso",
    "trimestre",
]

SOURCE_FLAG_COLS = [
    "has_conafor",
    "has_firms",
    "has_smn",
]


# =========================================================
# 7) COLUMNAS QUE NO DEBEN USARSE COMO FEATURES DIRECTAS
# =========================================================

NON_FEATURE_COLS_COMMON = [
    "fecha",
    "cve_ent",
    "nom_ent",
    "cve_mun",
    "nom_mun",
    "cvegeo",
    "has_conafor",
    "has_firms",
    "has_smn",
]

POTENTIAL_TARGET_OR_PROXY_COLS = [
    "conafor_event_count",
    "conafor_sup_ha_sum",
    "has_conafor",
]

TRACEABILITY_COL_PATTERNS = [
    "fuente",
    "origen",
    "archivo",
    "validacion",
    "observacion",
    "comentario",
]


# =========================================================
# 8) PARÁMETROS DE FEATURE ENGINEERING
# =========================================================

TEMPORAL_WINDOWS_DAYS = [
    7,
    15,
    30,
]

LOG1P_CANDIDATE_SUFFIXES = [
    "_count",
    "_sum",
]

EVENT_PREFIXES = [
    "firms_",
    "conafor_",
]

METEO_PREFIXES = [
    "smn_",
]

STATIC_CONTEXT_PREFIXES = [
    "inegi_",
    "infys_",
    "pct_",
    "sup_",
    "long_",
    "area_",
]


# =========================================================
# 9) VALIDACIÓN BÁSICA DE CONFIGURACIÓN
# =========================================================

def validate_input_files() -> list[dict]:
    """
    Verifica la existencia de los archivos de entrada esperados.

    Regresa una lista de diccionarios con:
    - nombre lógico,
    - ruta,
    - existe.
    """
    rows = []

    for name, path in INPUT_FILES.items():
        rows.append({
            "archivo_logico": name,
            "ruta": str(path),
            "existe": path.exists(),
        })

    return rows


def print_config_summary() -> None:
    """
    Imprime un resumen corto de la configuración de Feature Engineering.
    """
    print("\nFeature Engineering | Configuración general")
    print(f"Directorio base: {BASE_DIR}")
    print(f"Periodo del proyecto: {PROJECT_START_DATE} a {PROJECT_END_DATE}")
    print(f"Flujo principal: {PRIMARY_GRAIN}")
    print(f"Flujo complementario: {SECONDARY_GRAIN}")

    print("\nDirectorios FE:")
    print(f"- scripts:  {FE_SCRIPTS_DIR}")
    print(f"- datasets: {FE_DATASETS_DIR}")
    print(f"- reports:  {FE_REPORTS_DIR}")

    print("\nArchivos de entrada esperados:")
    for row in validate_input_files():
        status = "OK" if row["existe"] else "NO ENCONTRADO"
        print(f"- {row['archivo_logico']}: {status}")


if __name__ == "__main__":
    ensure_fe_directories()
    print_config_summary()