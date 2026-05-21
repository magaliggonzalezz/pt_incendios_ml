# -*- coding: utf-8 -*-
"""
Integración 08 | Diagnóstico de contexto INFyS

Este script revisa los datasets limpios de INFyS generados en Data Preparation
para identificar su granularidad potencial y decidir reglas de integración
posteriores.

Salida
------
1) 04_integration/reports/integracion_08_diagnostico_contexto_infys.csv

Objetivo
--------
- Revisar datasets limpios INFyS.
- Detectar columnas administrativas, temporales, geográficas y numéricas.
- Clasificar granularidad probable: nacional, entidad, municipio, punto/sitio,
  ciclo/periodo o no determinada.
- Recomendar si el dataset puede alimentar contexto municipal, estatal o ambos.
- No integrar todavía con bases diarias.
- No generar variables avanzadas de Feature Engineering.
"""

from __future__ import annotations

from pathlib import Path
import unicodedata
import pandas as pd


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

OUT_REPORTS_DIR = BASE_DIR / "04_integration" / "reports"
OUT_REPORTS_DIR.mkdir(parents=True, exist_ok=True)

OUT_DIAGNOSTICO = OUT_REPORTS_DIR / "integracion_08_diagnostico_contexto_infys.csv"

INFYS_DATASETS_ESPERADOS = [
    "infys_superficie_base_limpio.csv",
    "infys_superficie_2015_2020_estatal_limpio.csv",
    "infys_superficie_2015_2020_detalle_limpio.csv",

    "infys_secciones_conglomerados_2004_2009_limpio.csv",
    "infys_secciones_sitios_2004_2009_limpio.csv",
    "infys_secciones_conglomerados_2009_2014_limpio.csv",
    "infys_secciones_sitios_2009_2014_limpio.csv",
    "infys_secciones_conglomerados_2015_2020_limpio.csv",
    "infys_secciones_sitios_2015_2020_limpio.csv",

    "infys_deforestacion_superficie_nacional_limpio.csv",
    "infys_deforestacion_incertidumbre_nacional_limpio.csv",

    "infys_suelos_agregados_base_limpio.csv",
    "infys_suelos_2015_2020_base_limpio.csv",
    "infys_suelos_2015_2020_agregados_limpio.csv",

    "infys_indicadores_dasometricos_limpio.csv",
    "infys_indicadores_estructura_limpio.csv",
    "infys_indicadores_salud_forestal_limpio.csv",
    "infys_indicadores_composicion_limpio.csv",
    "infys_indicadores_ivi_ivf_limpio.csv",
    "infys_indicadores_distribucion_at_dn_limpio.csv",
    "infys_indicadores_existencias_limpio.csv",
    "infys_indicadores_incremento_medio_anual_limpio.csv",
    "infys_indicadores_tipo_propiedad_limpio.csv",
]


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


def detect_matching_columns(columns: list[str], candidates: list[str]) -> list[str]:
    norm_cols = {
        normalize_for_detection(col): col
        for col in columns
    }

    found = []

    for candidate in candidates:
        key = normalize_for_detection(candidate)
        if key in norm_cols:
            found.append(norm_cols[key])

    return sorted(set(found))


def compact_list(values: list[str]) -> str:
    if not values:
        return ""

    return " | ".join(values)


def infer_dataset_family(filename: str) -> str:
    name = filename.lower()

    if "superficie" in name:
        return "superficie"
    if "secciones" in name or "conglomerados" in name or "sitios" in name:
        return "secciones_conglomerados_sitios"
    if "deforestacion" in name:
        return "deforestacion"
    if "suelos" in name:
        return "suelos"
    if "indicadores" in name:
        return "indicadores_forestales"

    return "no_determinada"


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


def infer_granularity(
    filename: str,
    columns: list[str],
    n_rows: int,
    admin_cols: list[str],
    municipio_cols: list[str],
    cvegeo_cols: list[str],
    coord_cols: list[str],
    ciclo_cols: list[str]
) -> str:
    name = filename.lower()

    if "nacional" in name:
        return "nacional"

    if cvegeo_cols:
        return "municipal_o_geocodificada"

    if municipio_cols:
        return "municipal_textual"

    if coord_cols:
        if "sitios" in name or "conglomerados" in name:
            return "punto_sitio_conglomerado"
        return "punto_georreferenciado"

    if admin_cols:
        return "estatal"

    if ciclo_cols:
        return "ciclo_sin_clave_espacial"

    if n_rows == 1:
        return "nacional_o_resumen_unico"

    return "no_determinada"


def recommend_integration(granularity: str, family: str) -> tuple[str, str]:
    """
    Devuelve:
    - integracion_recomendada
    - observacion_metodologica
    """

    if granularity in {"nacional", "nacional_o_resumen_unico"}:
        return (
            "no_integrar_a_flujos_diarios",
            "Dataset nacional; puede documentarse como contexto general, pero no debe asignarse a municipio-día ni entidad-día sin supuestos adicionales."
        )

    if granularity == "estatal":
        return (
            "entidad_contexto",
            "Puede integrarse al flujo complementario entidad-día como contexto estructural/ciclo, sin duplicarse todavía en la base diaria."
        )

    if granularity in {"municipal_o_geocodificada", "municipal_textual"}:
        return (
            "municipio_contexto_y_entidad_contexto_derivado",
            "Puede alimentar el flujo principal municipal y derivarse a entidad si las claves o nombres se validan contra catálogos."
        )

    if granularity in {"punto_sitio_conglomerado", "punto_georreferenciado"}:
        return (
            "agregar_espacialmente_antes_de_integrar",
            "Requiere agregación espacial previa por municipio o entidad; no debe unirse directamente a bases diarias."
        )

    if granularity == "ciclo_sin_clave_espacial":
        return (
            "revisar_manual",
            "Tiene temporalidad/ciclo pero no clave espacial detectada; requiere revisión de columnas antes de integrar."
        )

    if family == "indicadores_forestales":
        return (
            "revisar_manual",
            "Dataset de indicadores; revisar si los indicadores tienen entidad, ciclo, tipo de vegetación, sitio o categoría antes de agregar."
        )

    return (
        "revisar_manual",
        "No se detectó granularidad suficiente para integrar automáticamente."
    )


def read_sample(path: Path, nrows: int = 5000) -> pd.DataFrame:
    try:
        return pd.read_csv(path, encoding="utf-8-sig", low_memory=False, nrows=nrows)
    except UnicodeDecodeError:
        return pd.read_csv(path, encoding="latin-1", low_memory=False, nrows=nrows)


def read_header(path: Path) -> list[str]:
    try:
        return list(pd.read_csv(path, encoding="utf-8-sig", nrows=0).columns)
    except UnicodeDecodeError:
        return list(pd.read_csv(path, encoding="latin-1", nrows=0).columns)


def count_rows_fast(path: Path) -> int:
    try:
        with open(path, "r", encoding="utf-8-sig", errors="replace") as f:
            return max(sum(1 for _ in f) - 1, 0)
    except Exception:
        return -1


# =========================================================
# 3) DIAGNÓSTICO POR DATASET
# =========================================================

def diagnose_dataset(path: Path) -> dict:
    filename = path.name
    columns = read_header(path)
    n_rows = count_rows_fast(path)

    sample = read_sample(path)

    admin_cols = detect_matching_columns(
        columns,
        [
            "cve_ent",
            "clave_entidad",
            "clave_estado",
            "entidad",
            "estado",
            "nom_ent",
            "nombre_entidad",
            "nombre_estado",
        ]
    )

    municipio_cols = detect_matching_columns(
        columns,
        [
            "cve_mun",
            "clave_municipio",
            "municipio",
            "nom_mun",
            "nombre_municipio",
            "cvegeo",
            "cve_geo",
            "clave_geoestadistica",
        ]
    )

    cvegeo_cols = detect_matching_columns(
        columns,
        [
            "cvegeo",
            "cve_geo",
            "clave_geoestadistica",
            "clavegeo",
        ]
    )

    coord_cols = detect_matching_columns(
        columns,
        [
            "latitud",
            "latitude",
            "lat",
            "longitud",
            "longitude",
            "lon",
            "lng",
            "x",
            "y",
        ]
    )

    temporal_cols = detect_matching_columns(
        columns,
        [
            "anio",
            "año",
            "year",
            "fecha",
            "periodo",
            "ciclo",
            "ciclo_infys",
            "levantamiento",
        ]
    )

    ciclo_cols = temporal_cols + [
        col for col in columns
        if any(token in normalize_for_detection(col) for token in ["20042009", "20092014", "20152020"])
    ]

    numeric_cols = [
        col for col in sample.columns
        if pd.api.types.is_numeric_dtype(sample[col])
    ]

    text_cols = [
        col for col in sample.columns
        if not pd.api.types.is_numeric_dtype(sample[col])
    ]

    family = infer_dataset_family(filename)
    ciclo_archivo = infer_cycle_from_filename(filename)

    granularity = infer_granularity(
        filename=filename,
        columns=columns,
        n_rows=n_rows,
        admin_cols=admin_cols,
        municipio_cols=municipio_cols,
        cvegeo_cols=cvegeo_cols,
        coord_cols=coord_cols,
        ciclo_cols=ciclo_cols
    )

    integracion_recomendada, observacion = recommend_integration(
        granularity=granularity,
        family=family
    )

    # Revisión ligera de columnas con posible identificador de sitio/conglomerado.
    sitio_cols = detect_matching_columns(
        columns,
        [
            "id_sitio",
            "sitio",
            "conglomerado",
            "id_conglomerado",
            "upm",
            "unidad_muestreo",
        ]
    )

    # Revisión de faltantes en columnas clave detectadas sobre muestra.
    cols_clave = sorted(set(admin_cols + municipio_cols + cvegeo_cols + coord_cols + temporal_cols + sitio_cols))
    faltantes_clave_muestra = {}

    for col in cols_clave:
        if col in sample.columns:
            faltantes_clave_muestra[col] = int(sample[col].isna().sum())

    return {
        "archivo": filename,
        "existe": "si",
        "familia_infys": family,
        "registros": n_rows,
        "columnas_total": len(columns),
        "ciclo_detectado_archivo": ciclo_archivo,
        "granularidad_probable": granularity,
        "integracion_recomendada": integracion_recomendada,
        "columnas_administrativas_detectadas": compact_list(admin_cols),
        "columnas_municipales_detectadas": compact_list(municipio_cols),
        "columnas_cvegeo_detectadas": compact_list(cvegeo_cols),
        "columnas_coordenadas_detectadas": compact_list(coord_cols),
        "columnas_temporales_ciclo_detectadas": compact_list(sorted(set(ciclo_cols))),
        "columnas_sitio_conglomerado_detectadas": compact_list(sitio_cols),
        "n_columnas_numericas_muestra": len(numeric_cols),
        "n_columnas_texto_muestra": len(text_cols),
        "faltantes_clave_muestra": str(faltantes_clave_muestra),
        "observacion_metodologica": observacion,
    }


def build_missing_row(filename: str) -> dict:
    return {
        "archivo": filename,
        "existe": "no",
        "familia_infys": infer_dataset_family(filename),
        "registros": "",
        "columnas_total": "",
        "ciclo_detectado_archivo": infer_cycle_from_filename(filename),
        "granularidad_probable": "no_disponible",
        "integracion_recomendada": "no_integrar",
        "columnas_administrativas_detectadas": "",
        "columnas_municipales_detectadas": "",
        "columnas_cvegeo_detectadas": "",
        "columnas_coordenadas_detectadas": "",
        "columnas_temporales_ciclo_detectadas": "",
        "columnas_sitio_conglomerado_detectadas": "",
        "n_columnas_numericas_muestra": "",
        "n_columnas_texto_muestra": "",
        "faltantes_clave_muestra": "",
        "observacion_metodologica": "Archivo esperado no encontrado en datasets INFyS.",
    }


# =========================================================
# 4) PIPELINE PRINCIPAL
# =========================================================

def main() -> None:
    print("\nIntegración 08 | Diagnóstico de contexto INFyS")
    print(f"Directorio INFyS datasets: {PATH_INFYS_DATASETS}")

    if not PATH_INFYS_DATASETS.exists():
        raise FileNotFoundError(f"No existe el directorio de datasets INFyS: {PATH_INFYS_DATASETS}")

    rows = []

    for filename in INFYS_DATASETS_ESPERADOS:
        path = PATH_INFYS_DATASETS / filename

        print(f"\nRevisando: {filename}")

        if not path.exists():
            print("- No encontrado")
            rows.append(build_missing_row(filename))
            continue

        try:
            row = diagnose_dataset(path)
            rows.append(row)

            print(f"- Registros: {row['registros']:,}" if isinstance(row["registros"], int) else f"- Registros: {row['registros']}")
            print(f"- Granularidad probable: {row['granularidad_probable']}")
            print(f"- Integración recomendada: {row['integracion_recomendada']}")

        except Exception as exc:
            rows.append({
                "archivo": filename,
                "existe": "si",
                "familia_infys": infer_dataset_family(filename),
                "registros": "",
                "columnas_total": "",
                "ciclo_detectado_archivo": infer_cycle_from_filename(filename),
                "granularidad_probable": "error_diagnostico",
                "integracion_recomendada": "revisar_manual",
                "columnas_administrativas_detectadas": "",
                "columnas_municipales_detectadas": "",
                "columnas_cvegeo_detectadas": "",
                "columnas_coordenadas_detectadas": "",
                "columnas_temporales_ciclo_detectadas": "",
                "columnas_sitio_conglomerado_detectadas": "",
                "n_columnas_numericas_muestra": "",
                "n_columnas_texto_muestra": "",
                "faltantes_clave_muestra": "",
                "observacion_metodologica": f"Error durante diagnóstico: {exc}",
            })

            print(f"- Error durante diagnóstico: {exc}")

    diagnostico = pd.DataFrame(rows)

    diagnostico.to_csv(
        OUT_DIAGNOSTICO,
        index=False,
        encoding="utf-8-sig"
    )

    print("\nArchivo generado:")
    print(f"- {OUT_DIAGNOSTICO}")

    print("\nResumen:")
    print(f"- Archivos esperados: {len(INFYS_DATASETS_ESPERADOS):,}")
    print(f"- Archivos encontrados: {(diagnostico['existe'] == 'si').sum():,}")
    print(f"- Archivos faltantes: {(diagnostico['existe'] == 'no').sum():,}")

    if "integracion_recomendada" in diagnostico.columns:
        print("\nIntegración recomendada:")
        print(diagnostico["integracion_recomendada"].value_counts(dropna=False).to_string())

    print("\nProceso terminado.")


if __name__ == "__main__":
    main()