# -*- coding: utf-8 -*-
"""
Integration 01 | Catálogos geográficos base INEGI

Este script construye los catálogos geográficos mínimos de entidades y municipios
a partir del GeoPackage limpio generado en Data Preparation de INEGI.

Salidas
-------
1) 04_integration/datasets/integracion_catalogo_entidades.csv
2) 04_integration/datasets/integracion_catalogo_municipios.csv
3) 04_integration/reports/integracion_01_validacion_geo_catalogs.csv

Objetivo
--------
Crear una referencia única de claves administrativas para la integración multifuente:
- cve_ent
- nom_ent
- cve_mun
- nom_mun
- cvegeo

Estos catálogos se usarán después para integrar CONAFOR, FIRMS y SMN.
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

INEGI_GPKG = (
    BASE_DIR
    / "03_data-preparation"
    / "inegi"
    / "datasets"
    / "inegi_capas_limpias.gpkg"
)

OUT_DATASETS_DIR = BASE_DIR / "04_integration" / "datasets"
OUT_REPORTS_DIR = BASE_DIR / "04_integration" / "reports"

OUT_DATASETS_DIR.mkdir(parents=True, exist_ok=True)
OUT_REPORTS_DIR.mkdir(parents=True, exist_ok=True)

OUT_ENTIDADES = OUT_DATASETS_DIR / "integracion_catalogo_entidades.csv"
OUT_MUNICIPIOS = OUT_DATASETS_DIR / "integracion_catalogo_municipios.csv"
OUT_VALIDACION = OUT_REPORTS_DIR / "integracion_01_validacion_geo_catalogos.csv"

LAYER_ENTIDADES = "entidades_limpio"
LAYER_MUNICIPIOS = "municipios_limpio"


# =========================================================
# 2) UTILIDADES
# =========================================================

def normalize_text(value) -> str:
    """
    Normaliza texto para catálogos:
    - convierte a string
    - elimina espacios extremos
    - compacta espacios internos
    - conserva acentos en salida final
    """
    if pd.isna(value):
        return ""

    s = str(value).strip()
    s = " ".join(s.split())
    return s


def normalize_for_detection(value: str) -> str:
    """
    Normaliza nombres de columnas para detección robusta:
    - minúsculas
    - sin acentos
    - sin espacios
    """
    s = str(value).strip().lower()
    s = unicodedata.normalize("NFKD", s)
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    s = s.replace(" ", "").replace("_", "").replace("-", "")
    return s


def detect_column(df: pd.DataFrame, candidates: list[str], label: str) -> str:
    """
    Detecta una columna usando una lista de nombres candidatos.
    """
    normalized_cols = {
        normalize_for_detection(col): col
        for col in df.columns
    }

    for candidate in candidates:
        key = normalize_for_detection(candidate)
        if key in normalized_cols:
            return normalized_cols[key]

    raise ValueError(
        f"No se pudo detectar la columna requerida para '{label}'. "
        f"Columnas disponibles: {list(df.columns)}"
    )


def normalize_cve_ent(series: pd.Series) -> pd.Series:
    """
    Normaliza clave de entidad a dos dígitos.
    """
    s = series.astype(str).str.strip()
    s = s.str.replace(r"\.0$", "", regex=True)
    s = s.str.extract(r"(\d+)", expand=False)
    return s.str.zfill(2)


def normalize_cve_mun(series: pd.Series) -> pd.Series:
    """
    Normaliza clave municipal a tres dígitos.
    """
    s = series.astype(str).str.strip()
    s = s.str.replace(r"\.0$", "", regex=True)
    s = s.str.extract(r"(\d+)", expand=False)
    return s.str.zfill(3)


def normalize_cvegeo(series: pd.Series) -> pd.Series:
    """
    Normaliza CVEGEO municipal a cinco dígitos.
    """
    s = series.astype(str).str.strip()
    s = s.str.replace(r"\.0$", "", regex=True)
    s = s.str.extract(r"(\d+)", expand=False)
    return s.str.zfill(5)


def build_validation_row(
    archivo: str,
    registros: int,
    clave: str,
    duplicados: int,
    nulos_clave: int,
    geometria_nula: int,
    crs: str,
    estatus: str,
    observacion: str
) -> dict:
    return {
        "archivo": archivo,
        "registros": registros,
        "clave_validada": clave,
        "duplicados_clave": duplicados,
        "nulos_clave": nulos_clave,
        "geometrias_nulas": geometria_nula,
        "crs": crs,
        "estatus_validacion": estatus,
        "observacion": observacion,
    }


# =========================================================
# 3) CARGA Y CONSTRUCCIÓN DE CATÁLOGOS
# =========================================================

def build_catalogo_entidades(entidades_gdf: gpd.GeoDataFrame) -> tuple[pd.DataFrame, dict]:
    """
    Construye catálogo de entidades.
    """
    cve_ent_col = detect_column(
        entidades_gdf,
        ["cve_ent", "cvegeo", "cve_entidad", "clave_entidad", "entidad"],
        "clave de entidad"
    )

    nom_ent_col = detect_column(
        entidades_gdf,
        ["nom_ent", "nombre_entidad", "entidad", "nomgeo", "nombre"],
        "nombre de entidad"
    )

    entidades = entidades_gdf.copy()

    entidades["cve_ent"] = normalize_cve_ent(entidades[cve_ent_col])
    entidades["nom_ent"] = entidades[nom_ent_col].map(normalize_text)

    catalogo = (
        entidades[["cve_ent", "nom_ent"]]
        .drop_duplicates()
        .sort_values("cve_ent")
        .reset_index(drop=True)
    )

    duplicados = int(catalogo.duplicated(subset=["cve_ent"]).sum())
    nulos_clave = int(catalogo["cve_ent"].isna().sum() + (catalogo["cve_ent"] == "").sum())
    geometria_nula = int(entidades_gdf.geometry.isna().sum()) if "geometry" in entidades_gdf else -1
    crs = str(entidades_gdf.crs)

    estatus = "ok"
    observacion = ""

    if duplicados > 0:
        estatus = "error"
        observacion += "Existen cve_ent duplicadas. "

    if nulos_clave > 0:
        estatus = "error"
        observacion += "Existen cve_ent nulas. "

    if len(catalogo) == 0:
        estatus = "error"
        observacion += "Catálogo vacío. "

    if observacion == "":
        observacion = "Catálogo de entidades construido correctamente."

    validacion = build_validation_row(
        archivo=OUT_ENTIDADES.name,
        registros=len(catalogo),
        clave="cve_ent",
        duplicados=duplicados,
        nulos_clave=nulos_clave,
        geometria_nula=geometria_nula,
        crs=crs,
        estatus=estatus,
        observacion=observacion
    )

    return catalogo, validacion


def build_catalogo_municipios(
    municipios_gdf: gpd.GeoDataFrame,
    catalogo_entidades: pd.DataFrame
) -> tuple[pd.DataFrame, dict]:
    """
    Construye catálogo de municipios.

    La capa municipal puede no contener nom_ent. En ese caso, nom_ent se recupera
    desde el catálogo de entidades usando cve_ent.
    """
    cve_ent_col = detect_column(
        municipios_gdf,
        ["cve_ent", "cve_entidad", "clave_entidad"],
        "clave de entidad"
    )

    cve_mun_col = detect_column(
        municipios_gdf,
        ["cve_mun", "cve_municipio", "clave_municipio", "municipio_clave"],
        "clave de municipio"
    )

    nom_mun_col = detect_column(
        municipios_gdf,
        ["nom_mun", "nombre_municipio", "municipio", "nomgeo", "nombre"],
        "nombre de municipio"
    )

    municipios = municipios_gdf.copy()

    municipios["cve_ent"] = normalize_cve_ent(municipios[cve_ent_col])
    municipios["cve_mun"] = normalize_cve_mun(municipios[cve_mun_col])
    municipios["nom_mun"] = municipios[nom_mun_col].map(normalize_text)

    # Si existe cvegeo se usa; si no existe, se construye con cve_ent + cve_mun.
    possible_cvegeo_cols = [
        col for col in municipios.columns
        if normalize_for_detection(col) in {
            "cvegeo",
            "cvegeomun",
            "clavegeo",
            "clavegeografica"
        }
    ]

    if possible_cvegeo_cols:
        cvegeo_col = possible_cvegeo_cols[0]
        municipios["cvegeo"] = normalize_cvegeo(municipios[cvegeo_col])
    else:
        municipios["cvegeo"] = municipios["cve_ent"] + municipios["cve_mun"]

    catalogo = (
        municipios[["cve_ent", "cve_mun", "nom_mun", "cvegeo"]]
        .drop_duplicates()
        .sort_values(["cve_ent", "cve_mun"])
        .reset_index(drop=True)
    )

    # Recuperar nom_ent desde catálogo de entidades
    catalogo = catalogo.merge(
        catalogo_entidades[["cve_ent", "nom_ent"]],
        on="cve_ent",
        how="left"
    )

    # Reordenar columnas
    catalogo = catalogo[
        ["cve_ent", "nom_ent", "cve_mun", "nom_mun", "cvegeo"]
    ].copy()

    duplicados = int(catalogo.duplicated(subset=["cvegeo"]).sum())
    nulos_clave = int(catalogo["cvegeo"].isna().sum() + (catalogo["cvegeo"] == "").sum())
    geometria_nula = int(municipios_gdf.geometry.isna().sum()) if "geometry" in municipios_gdf else -1
    crs = str(municipios_gdf.crs)

    entidades_no_catalogo = sorted(
        set(catalogo["cve_ent"].dropna()) - set(catalogo_entidades["cve_ent"].dropna())
    )

    municipios_sin_nom_ent = int(catalogo["nom_ent"].isna().sum())
    cvegeo_inconsistente = int((catalogo["cvegeo"].str.len() != 5).sum())

    estatus = "ok"
    observacion = ""

    if duplicados > 0:
        estatus = "error"
        observacion += "Existen cvegeo duplicadas. "

    if nulos_clave > 0:
        estatus = "error"
        observacion += "Existen cvegeo nulas. "

    if cvegeo_inconsistente > 0:
        estatus = "error"
        observacion += "Existen cvegeo con longitud distinta de 5. "

    if entidades_no_catalogo:
        estatus = "error"
        observacion += f"Hay cve_ent municipales no presentes en catálogo de entidades: {entidades_no_catalogo}. "

    if municipios_sin_nom_ent > 0:
        estatus = "error"
        observacion += f"Hay municipios sin nom_ent recuperado desde catálogo de entidades: {municipios_sin_nom_ent}. "

    if len(catalogo) == 0:
        estatus = "error"
        observacion += "Catálogo vacío. "

    if observacion == "":
        observacion = "Catálogo de municipios construido correctamente."

    validacion = build_validation_row(
        archivo=OUT_MUNICIPIOS.name,
        registros=len(catalogo),
        clave="cvegeo",
        duplicados=duplicados,
        nulos_clave=nulos_clave,
        geometria_nula=geometria_nula,
        crs=crs,
        estatus=estatus,
        observacion=observacion
    )

    return catalogo, validacion


# =========================================================
# 4) PIPELINE PRINCIPAL
# =========================================================

def main() -> None:
    print("\nIntegration 01 | Catálogos geográficos base INEGI")

    if not INEGI_GPKG.exists():
        raise FileNotFoundError(f"No existe el GeoPackage limpio de INEGI: {INEGI_GPKG}")

    print(f"GeoPackage INEGI: {INEGI_GPKG}")

    print(f"Cargando capa: {LAYER_ENTIDADES}")
    entidades_gdf = gpd.read_file(INEGI_GPKG, layer=LAYER_ENTIDADES)

    print(f"Cargando capa: {LAYER_MUNICIPIOS}")
    municipios_gdf = gpd.read_file(INEGI_GPKG, layer=LAYER_MUNICIPIOS)

    print(f"Entidades leídas: {len(entidades_gdf):,}")
    print(f"Municipios leídos: {len(municipios_gdf):,}")

    catalogo_entidades, validacion_entidades = build_catalogo_entidades(entidades_gdf)
    catalogo_municipios, validacion_municipios = build_catalogo_municipios(
        municipios_gdf,
        catalogo_entidades
    )

    validaciones = pd.DataFrame([
        validacion_entidades,
        validacion_municipios
    ])

    errores = validaciones[validaciones["estatus_validacion"] != "ok"]

    if not errores.empty:
        print("\nSe detectaron errores de validación:")
        print(errores.to_string(index=False))
        raise ValueError(
            "La construcción de catálogos terminó con errores. "
            "Revisa integration_01_validacion_geo_catalogs.csv."
        )

    catalogo_entidades.to_csv(OUT_ENTIDADES, index=False, encoding="utf-8-sig")
    catalogo_municipios.to_csv(OUT_MUNICIPIOS, index=False, encoding="utf-8-sig")
    validaciones.to_csv(OUT_VALIDACION, index=False, encoding="utf-8-sig")

    print("\nArchivos generados:")
    print(f"- {OUT_ENTIDADES}")
    print(f"- {OUT_MUNICIPIOS}")
    print(f"- {OUT_VALIDACION}")

    print("\nResumen:")
    print(f"- Entidades en catálogo: {len(catalogo_entidades):,}")
    print(f"- Municipios en catálogo: {len(catalogo_municipios):,}")
    print("- Validación: ok")

    print("\nProceso terminado.")


if __name__ == "__main__":
    main()