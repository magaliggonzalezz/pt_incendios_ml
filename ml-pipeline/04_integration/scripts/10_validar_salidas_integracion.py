# -*- coding: utf-8 -*-
"""
Integración 10 | Validación general de salidas de integración

Este script valida las salidas principales generadas durante la fase de
Integration multifuente.

Salida
------
1) 04_integration/reports/integracion_10_validacion_general.csv

Objetivo
--------
- Verificar existencia de salidas esperadas.
- Validar llaves principales.
- Validar duplicados.
- Validar dimensiones principales.
- Confirmar disponibilidad de los dos flujos:
  1) Flujo principal municipio-día.
  2) Flujo complementario entidad-día.
- Confirmar disponibilidad de contextos estructurales INEGI e INFyS.
"""

from __future__ import annotations

from pathlib import Path
import pandas as pd


# =========================================================
# 1) CONFIGURACIÓN
# =========================================================

BASE_DIR = Path(r"C:\Users\Hp\OneDrive\Documentos\PT_Analisis")

DATASETS_DIR = BASE_DIR / "04_integration" / "datasets"
REPORTS_DIR = BASE_DIR / "04_integration" / "reports"

OUT_VALIDACION = REPORTS_DIR / "integracion_10_validacion_general.csv"

REPORTS_DIR.mkdir(parents=True, exist_ok=True)

PROJECT_START = "2001-01-01"
PROJECT_END = "2025-12-31"


ARCHIVOS_ESPERADOS = {
    # Catálogos
    "catalogo_entidades": DATASETS_DIR / "integracion_catalogo_entidades.csv",
    "catalogo_municipios": DATASETS_DIR / "integracion_catalogo_municipios.csv",

    # Fuente dinámica contextualizada
    "conafor_eventos_contexto": DATASETS_DIR / "integracion_conafor_eventos_contexto.csv",
    "conafor_municipio_dia": DATASETS_DIR / "integracion_conafor_municipio_dia.csv",
    "firms_puntos_contexto": DATASETS_DIR / "integracion_firms_puntos_contexto.csv",
    "firms_municipio_dia": DATASETS_DIR / "integracion_firms_municipio_dia.csv",
    "smn_estaciones_contexto": DATASETS_DIR / "integracion_smn_estaciones_contexto.csv",
    "smn_municipio_dia": DATASETS_DIR / "integracion_smn_municipio_dia.csv",

    # Bases dinámicas
    "municipio_dia_base": DATASETS_DIR / "integracion_municipio_dia_base.csv",
    "entidad_dia_base": DATASETS_DIR / "integracion_entidad_dia_base.csv",

    # Contexto estructural INEGI
    "inegi_municipio_contexto": DATASETS_DIR / "integracion_inegi_municipio_contexto.csv",
    "inegi_entidad_contexto": DATASETS_DIR / "integracion_inegi_entidad_contexto.csv",

    # Contexto estructural INFyS
    "infys_municipio_contexto": DATASETS_DIR / "integracion_infys_municipio_contexto.csv",
    "infys_entidad_contexto": DATASETS_DIR / "integracion_infys_entidad_contexto.csv",
}


REPORTES_ESPERADOS = {
    "validacion_01_geo_catalogs": REPORTS_DIR / "integracion_01_validacion_geo_catalogos.csv",
    "validacion_02_conafor": REPORTS_DIR / "integracion_02_validacion_conafor_contexto.csv",
    "validacion_03_firms": REPORTS_DIR / "integracion_03_validacion_firms_contexto.csv",
    "validacion_04_smn": REPORTS_DIR / "integracion_04_validacion_smn_contexto.csv",
    "validacion_05_municipio_dia": REPORTS_DIR / "integracion_05_validacion_municipio_dia_base.csv",
    "validacion_06_entidad_dia": REPORTS_DIR / "integracion_06_validacion_entidad_dia_base.csv",
    "validacion_07_inegi": REPORTS_DIR / "integracion_07_validacion_contexto_geografico_inegi.csv",
    "diagnostico_08_infys": REPORTS_DIR / "integracion_08_diagnostico_contexto_infys.csv",
    "validacion_09_infys": REPORTS_DIR / "integracion_09_validacion_contexto_infys.csv",
}


# =========================================================
# 2) UTILIDADES
# =========================================================

def build_row(
    bloque: str,
    archivo: str,
    indicador: str,
    valor,
    estatus: str,
    observacion: str
) -> dict:
    return {
        "bloque": bloque,
        "archivo": archivo,
        "indicador": indicador,
        "valor": valor,
        "estatus": estatus,
        "observacion": observacion,
    }


def read_csv_safe(path: Path, dtype=None, usecols=None) -> pd.DataFrame:
    return pd.read_csv(
        path,
        encoding="utf-8-sig",
        dtype=dtype,
        usecols=usecols,
        low_memory=False
    )


def check_file_exists(nombre: str, path: Path, bloque: str) -> dict:
    return build_row(
        bloque=bloque,
        archivo=nombre,
        indicador="archivo_existe",
        valor=str(path),
        estatus="ok" if path.exists() else "error",
        observacion="Archivo esperado encontrado." if path.exists() else "Archivo esperado no encontrado."
    )


def validate_unique_key(
    df: pd.DataFrame,
    key_cols: list[str],
    bloque: str,
    archivo: str
) -> list[dict]:
    rows = []

    missing = [col for col in key_cols if col not in df.columns]

    if missing:
        rows.append(build_row(
            bloque,
            archivo,
            "columnas_llave_disponibles",
            "faltan: " + ", ".join(missing),
            "error",
            "No se puede validar llave porque faltan columnas."
        ))
        return rows

    duplicated = int(df.duplicated(subset=key_cols).sum())

    rows.append(build_row(
        bloque,
        archivo,
        "duplicados_llave_" + "_".join(key_cols),
        duplicated,
        "ok" if duplicated == 0 else "error",
        f"Duplicados usando llave: {', '.join(key_cols)}."
    ))

    nulls = int(df[key_cols].isna().any(axis=1).sum())

    rows.append(build_row(
        bloque,
        archivo,
        "registros_con_llave_nula_" + "_".join(key_cols),
        nulls,
        "ok" if nulls == 0 else "warning",
        f"Registros con algún valor nulo en llave: {', '.join(key_cols)}."
    ))

    return rows


def validate_period(
    df: pd.DataFrame,
    date_col: str,
    bloque: str,
    archivo: str
) -> list[dict]:
    rows = []

    if date_col not in df.columns:
        rows.append(build_row(
            bloque,
            archivo,
            f"{date_col}_disponible",
            "no",
            "error",
            f"No existe la columna temporal {date_col}."
        ))
        return rows

    fecha = pd.to_datetime(df[date_col], errors="coerce")

    invalid = int(fecha.isna().sum())

    rows.append(build_row(
        bloque,
        archivo,
        "fechas_invalidas",
        invalid,
        "ok" if invalid == 0 else "error",
        "Fechas no convertibles a datetime."
    ))

    if fecha.notna().any():
        fecha_min = fecha.min().date()
        fecha_max = fecha.max().date()

        rows.append(build_row(
            bloque,
            archivo,
            "fecha_min",
            fecha_min,
            "ok",
            "Fecha mínima detectada."
        ))

        rows.append(build_row(
            bloque,
            archivo,
            "fecha_max",
            fecha_max,
            "ok",
            "Fecha máxima detectada."
        ))

        fuera_periodo = int(
            (
                (fecha < pd.to_datetime(PROJECT_START))
                | (fecha > pd.to_datetime(PROJECT_END))
            ).sum()
        )

        rows.append(build_row(
            bloque,
            archivo,
            "registros_fuera_periodo_2001_2025",
            fuera_periodo,
            "ok" if fuera_periodo == 0 else "warning",
            "Registros fuera del periodo general del proyecto."
        ))

    return rows


def validate_required_columns(
    df: pd.DataFrame,
    required_cols: list[str],
    bloque: str,
    archivo: str
) -> list[dict]:
    missing = [col for col in required_cols if col not in df.columns]

    return [
        build_row(
            bloque,
            archivo,
            "columnas_requeridas",
            "ok" if not missing else "faltan: " + ", ".join(missing),
            "ok" if not missing else "error",
            "Validación de columnas mínimas requeridas."
        )
    ]


# =========================================================
# 3) VALIDACIONES ESPECÍFICAS
# =========================================================

def validate_catalogos(rows: list[dict]) -> None:
    print("Validando catálogos...")

    ent_path = ARCHIVOS_ESPERADOS["catalogo_entidades"]
    mun_path = ARCHIVOS_ESPERADOS["catalogo_municipios"]

    if ent_path.exists():
        ent = read_csv_safe(ent_path, dtype=str)

        rows.append(build_row(
            "catalogos",
            "integracion_catalogo_entidades.csv",
            "registros",
            len(ent),
            "ok" if len(ent) == 32 else "warning",
            "Número de entidades en catálogo."
        ))

        rows.extend(validate_unique_key(
            ent,
            ["cve_ent"],
            "catalogos",
            "integracion_catalogo_entidades.csv"
        ))

    if mun_path.exists():
        mun = read_csv_safe(mun_path, dtype=str)

        rows.append(build_row(
            "catalogos",
            "integracion_catalogo_municipios.csv",
            "registros",
            len(mun),
            "ok" if len(mun) == 2478 else "warning",
            "Número de municipios en catálogo."
        ))

        rows.extend(validate_unique_key(
            mun,
            ["cvegeo"],
            "catalogos",
            "integracion_catalogo_municipios.csv"
        ))


def validate_fuentes_dinamicas(rows: list[dict]) -> None:
    print("Validando fuentes dinámicas contextualizadas...")

    specs = [
        (
            "conafor_municipio_dia",
            "integracion_conafor_municipio_dia.csv",
            ["cvegeo", "fecha"],
            ["cvegeo", "fecha", "conafor_event_count"]
        ),
        (
            "firms_municipio_dia",
            "integracion_firms_municipio_dia.csv",
            ["cvegeo", "fecha"],
            ["cvegeo", "fecha", "firms_count"]
        ),
        (
            "smn_municipio_dia",
            "integracion_smn_municipio_dia.csv",
            ["cvegeo", "fecha"],
            ["cvegeo", "fecha", "smn_n_estaciones"]
        ),
    ]

    for key, filename, key_cols, required_cols in specs:
        path = ARCHIVOS_ESPERADOS[key]

        if not path.exists():
            continue

        df = read_csv_safe(path, dtype={"cvegeo": str})

        rows.append(build_row(
            "fuentes_dinamicas",
            filename,
            "registros",
            len(df),
            "ok" if len(df) > 0 else "error",
            "Registros disponibles en fuente dinámica integrada."
        ))

        rows.extend(validate_required_columns(df, required_cols, "fuentes_dinamicas", filename))
        rows.extend(validate_unique_key(df, key_cols, "fuentes_dinamicas", filename))
        rows.extend(validate_period(df, "fecha", "fuentes_dinamicas", filename))


def validate_bases_dinamicas(rows: list[dict]) -> None:
    print("Validando bases dinámicas principales...")

    municipio_path = ARCHIVOS_ESPERADOS["municipio_dia_base"]
    entidad_path = ARCHIVOS_ESPERADOS["entidad_dia_base"]

    if municipio_path.exists():
        df = read_csv_safe(
            municipio_path,
            dtype={"cve_ent": str, "cve_mun": str, "cvegeo": str}
        )

        rows.append(build_row(
            "flujo_principal_municipio_dia",
            "integracion_municipio_dia_base.csv",
            "registros",
            len(df),
            "ok" if len(df) > 0 else "error",
            "Base dinámica principal municipio-día."
        ))

        rows.append(build_row(
            "flujo_principal_municipio_dia",
            "integracion_municipio_dia_base.csv",
            "municipios_unicos",
            df["cvegeo"].nunique() if "cvegeo" in df.columns else None,
            "ok" if "cvegeo" in df.columns and df["cvegeo"].nunique() > 0 else "error",
            "Municipios únicos presentes en base principal."
        ))

        rows.extend(validate_required_columns(
            df,
            [
                "cve_ent",
                "nom_ent",
                "cve_mun",
                "nom_mun",
                "cvegeo",
                "fecha",
                "has_conafor",
                "has_firms",
                "has_smn",
            ],
            "flujo_principal_municipio_dia",
            "integracion_municipio_dia_base.csv"
        ))

        rows.extend(validate_unique_key(
            df,
            ["cvegeo", "fecha"],
            "flujo_principal_municipio_dia",
            "integracion_municipio_dia_base.csv"
        ))

        rows.extend(validate_period(
            df,
            "fecha",
            "flujo_principal_municipio_dia",
            "integracion_municipio_dia_base.csv"
        ))

    if entidad_path.exists():
        df = read_csv_safe(entidad_path, dtype={"cve_ent": str})

        rows.append(build_row(
            "flujo_complementario_entidad_dia",
            "integracion_entidad_dia_base.csv",
            "registros",
            len(df),
            "ok" if len(df) > 0 else "error",
            "Base dinámica complementaria entidad-día."
        ))

        rows.append(build_row(
            "flujo_complementario_entidad_dia",
            "integracion_entidad_dia_base.csv",
            "entidades_unicas",
            df["cve_ent"].nunique() if "cve_ent" in df.columns else None,
            "ok" if "cve_ent" in df.columns and df["cve_ent"].nunique() == 32 else "warning",
            "Entidades únicas presentes en base complementaria."
        ))

        rows.extend(validate_required_columns(
            df,
            [
                "cve_ent",
                "nom_ent",
                "fecha",
                "has_conafor",
                "has_firms",
                "has_smn",
            ],
            "flujo_complementario_entidad_dia",
            "integracion_entidad_dia_base.csv"
        ))

        rows.extend(validate_unique_key(
            df,
            ["cve_ent", "fecha"],
            "flujo_complementario_entidad_dia",
            "integracion_entidad_dia_base.csv"
        ))

        rows.extend(validate_period(
            df,
            "fecha",
            "flujo_complementario_entidad_dia",
            "integracion_entidad_dia_base.csv"
        ))


def validate_contextos(rows: list[dict]) -> None:
    print("Validando contextos estructurales...")

    specs = [
        (
            "contexto_inegi_municipal",
            "inegi_municipio_contexto",
            "integracion_inegi_municipio_contexto.csv",
            ["cvegeo"],
            2478,
        ),
        (
            "contexto_inegi_estatal",
            "inegi_entidad_contexto",
            "integracion_inegi_entidad_contexto.csv",
            ["cve_ent"],
            32,
        ),
        (
            "contexto_infys_municipal",
            "infys_municipio_contexto",
            "integracion_infys_municipio_contexto.csv",
            ["cvegeo"],
            2478,
        ),
        (
            "contexto_infys_estatal",
            "infys_entidad_contexto",
            "integracion_infys_entidad_contexto.csv",
            ["cve_ent"],
            32,
        ),
    ]

    for bloque, key, filename, key_cols, expected_rows in specs:
        path = ARCHIVOS_ESPERADOS[key]

        if not path.exists():
            continue

        dtype = {"cvegeo": str, "cve_ent": str}
        df = read_csv_safe(path, dtype=dtype)

        rows.append(build_row(
            bloque,
            filename,
            "registros",
            len(df),
            "ok" if len(df) == expected_rows else "warning",
            f"Registros esperados: {expected_rows}."
        ))

        rows.append(build_row(
            bloque,
            filename,
            "columnas",
            len(df.columns),
            "ok" if len(df.columns) > len(key_cols) else "warning",
            "Número de columnas disponibles en contexto estructural."
        ))

        rows.extend(validate_unique_key(
            df,
            key_cols,
            bloque,
            filename
        ))


def validate_reportes_previos(rows: list[dict]) -> None:
    print("Validando reportes previos...")

    for nombre, path in REPORTES_ESPERADOS.items():
        rows.append(check_file_exists(nombre, path, "reportes_previos"))

        if not path.exists():
            continue

        try:
            df = read_csv_safe(path)

            rows.append(build_row(
                "reportes_previos",
                nombre,
                "registros_reporte",
                len(df),
                "ok" if len(df) > 0 else "warning",
                "Registros dentro del reporte de validación previo."
            ))

            if "estatus" in df.columns:
                n_error = int((df["estatus"] == "error").sum())
                n_warning = int((df["estatus"] == "warning").sum())

                rows.append(build_row(
                    "reportes_previos",
                    nombre,
                    "errores_reportados",
                    n_error,
                    "ok" if n_error == 0 else "warning",
                    "Errores reportados por script previo."
                ))

                rows.append(build_row(
                    "reportes_previos",
                    nombre,
                    "warnings_reportados",
                    n_warning,
                    "ok",
                    "Warnings reportados por script previo. Algunos son metodológicos no bloqueantes."
                ))

        except Exception as exc:
            rows.append(build_row(
                "reportes_previos",
                nombre,
                "lectura_reporte",
                "error",
                "warning",
                f"No se pudo leer el reporte previo: {exc}"
            ))


def validate_integration_readiness(rows: list[dict]) -> None:
    print("Validando disponibilidad de flujos...")

    required_principal = [
        "municipio_dia_base",
        "inegi_municipio_contexto",
        "infys_municipio_contexto",
    ]

    required_complementario = [
        "entidad_dia_base",
        "inegi_entidad_contexto",
        "infys_entidad_contexto",
    ]

    principal_ok = all(ARCHIVOS_ESPERADOS[key].exists() for key in required_principal)
    complementario_ok = all(ARCHIVOS_ESPERADOS[key].exists() for key in required_complementario)

    rows.append(build_row(
        "cierre_integration",
        "flujo_principal",
        "municipio_dia_disponible",
        principal_ok,
        "ok" if principal_ok else "error",
        "Disponibilidad del flujo principal: municipio-día + contexto INEGI + contexto INFyS."
    ))

    rows.append(build_row(
        "cierre_integration",
        "flujo_complementario",
        "entidad_dia_disponible",
        complementario_ok,
        "ok" if complementario_ok else "error",
        "Disponibilidad del flujo complementario: entidad-día + contexto INEGI + contexto INFyS."
    ))

    rows.append(build_row(
        "cierre_integration",
        "estado_fase",
        "integration_lista_para_feature_engineering",
        principal_ok and complementario_ok,
        "ok" if principal_ok and complementario_ok else "error",
        "La fase Integration queda lista para pasar posteriormente a Feature Engineering, no a Modeling directo."
    ))


# =========================================================
# 4) PIPELINE PRINCIPAL
# =========================================================

def main() -> None:
    print("\nIntegración 10 | Validación general de salidas")

    rows = []

    print("Verificando archivos esperados...")
    for nombre, path in ARCHIVOS_ESPERADOS.items():
        rows.append(check_file_exists(nombre, path, "datasets_integracion"))

    validate_catalogos(rows)
    validate_fuentes_dinamicas(rows)
    validate_bases_dinamicas(rows)
    validate_contextos(rows)
    validate_reportes_previos(rows)
    validate_integration_readiness(rows)

    validacion = pd.DataFrame(rows)

    validacion.to_csv(
        OUT_VALIDACION,
        index=False,
        encoding="utf-8-sig"
    )

    n_errors = int((validacion["estatus"] == "error").sum())
    n_warnings = int((validacion["estatus"] == "warning").sum())

    print("\nArchivo generado:")
    print(f"- {OUT_VALIDACION}")

    print("\nResumen:")
    print(f"- Validaciones totales: {len(validacion):,}")
    print(f"- Errores: {n_errors:,}")
    print(f"- Warnings: {n_warnings:,}")

    if n_errors > 0:
        print("\nErrores detectados:")
        print(
            validacion[validacion["estatus"] == "error"][
                ["bloque", "archivo", "indicador", "valor", "observacion"]
            ].to_string(index=False)
        )
        raise ValueError("La validación general de Integration terminó con errores.")

    print("\nProceso terminado.")
    print("Integration queda validada. El siguiente bloque metodológico sería Feature Engineering.")


if __name__ == "__main__":
    main()