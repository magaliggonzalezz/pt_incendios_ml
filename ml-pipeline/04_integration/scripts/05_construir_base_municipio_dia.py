# -*- coding: utf-8 -*-
"""
Integración 05 | Construcción de base municipio-día multifuente

Este script construye la base integrada municipio-día a partir de las salidas
limpias de Integration para CONAFOR, FIRMS y SMN.

Salidas
-------
1) 04_integration/datasets/integracion_municipio_dia_base.csv
2) 04_integration/reports/integracion_05_validacion_municipio_dia_base.csv

Objetivo
--------
- Unir CONAFOR, FIRMS y SMN por cvegeo + fecha.
- Mantener una base sparse controlada.
- Conservar trazabilidad mediante banderas de disponibilidad por fuente.
"""

from __future__ import annotations

from pathlib import Path
import pandas as pd


# =========================================================
# 1) CONFIGURACIÓN
# =========================================================

BASE_DIR = Path(r"C:\Users\Hp\OneDrive\Documentos\PT_Analisis")

INTEGRATION_DATASETS_DIR = BASE_DIR / "04_integration" / "datasets"
INTEGRATION_REPORTS_DIR = BASE_DIR / "04_integration" / "reports"

PATH_CATALOGO_MUNICIPIOS = INTEGRATION_DATASETS_DIR / "integracion_catalogo_municipios.csv"
PATH_CONAFOR = INTEGRATION_DATASETS_DIR / "integracion_conafor_municipio_dia.csv"
PATH_FIRMS = INTEGRATION_DATASETS_DIR / "integracion_firms_municipio_dia.csv"
PATH_SMN = INTEGRATION_DATASETS_DIR / "integracion_smn_municipio_dia.csv"

OUT_BASE = INTEGRATION_DATASETS_DIR / "integracion_municipio_dia_base.csv"
OUT_VALIDACION = INTEGRATION_REPORTS_DIR / "integracion_05_validacion_municipio_dia_base.csv"

INTEGRATION_DATASETS_DIR.mkdir(parents=True, exist_ok=True)
INTEGRATION_REPORTS_DIR.mkdir(parents=True, exist_ok=True)

PROJECT_START = "2001-01-01"
PROJECT_END = "2025-12-31"

CONAFOR_START = "2005-01-01"
CONAFOR_END = "2025-12-31"


# =========================================================
# 2) UTILIDADES
# =========================================================

def normalize_code(series: pd.Series, width: int) -> pd.Series:
    s = series.astype(str).str.strip()
    s = s.str.replace(r"\.0$", "", regex=True)
    extracted = s.str.extract(r"(\d+)", expand=False)
    return extracted.where(extracted.notna(), pd.NA).str.zfill(width)


def normalize_cvegeo(series: pd.Series) -> pd.Series:
    return normalize_code(series, 5)


def normalize_cve_ent(series: pd.Series) -> pd.Series:
    return normalize_code(series, 2)


def normalize_cve_mun(series: pd.Series) -> pd.Series:
    return normalize_code(series, 3)


def build_report_row(indicador: str, valor, estatus: str, observacion: str) -> dict:
    return {
        "indicador": indicador,
        "valor": valor,
        "estatus": estatus,
        "observacion": observacion,
    }


def validate_input_exists() -> None:
    paths = {
        "catalogo_municipios": PATH_CATALOGO_MUNICIPIOS,
        "conafor_municipio_dia": PATH_CONAFOR,
        "firms_municipio_dia": PATH_FIRMS,
        "smn_municipio_dia": PATH_SMN,
    }

    missing = [label for label, path in paths.items() if not path.exists()]

    if missing:
        detail = "\n".join([f"- {label}: {paths[label]}" for label in missing])
        raise FileNotFoundError(f"Faltan insumos para construir municipio-día:\n{detail}")


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


def load_municipio_dia(path: Path, label: str) -> pd.DataFrame:
    df = pd.read_csv(path, encoding="utf-8-sig", dtype={"cvegeo": str}, low_memory=False)

    required = {"cvegeo", "fecha"}
    missing = required - set(df.columns)

    if missing:
        raise ValueError(f"{label} no contiene columnas requeridas {required}. Faltan: {missing}")

    df["cvegeo"] = normalize_cvegeo(df["cvegeo"])
    df["fecha"] = pd.to_datetime(df["fecha"], errors="coerce").dt.date

    dup = df.duplicated(subset=["cvegeo", "fecha"]).sum()
    if dup > 0:
        raise ValueError(f"{label} tiene duplicados por cvegeo + fecha: {dup}")

    return df


def strip_admin_cols(df: pd.DataFrame) -> pd.DataFrame:
    """
    Elimina columnas administrativas para imponer las canónicas del catálogo.
    """
    admin_cols = ["cve_ent", "nom_ent", "cve_mun", "nom_mun"]
    return df.drop(columns=[c for c in admin_cols if c in df.columns], errors="ignore")


# =========================================================
# 3) CONSTRUCCIÓN DE BASE
# =========================================================

def build_key_universe(
    conafor: pd.DataFrame,
    firms: pd.DataFrame,
    smn: pd.DataFrame
) -> pd.DataFrame:
    keys = pd.concat(
        [
            conafor[["cvegeo", "fecha"]],
            firms[["cvegeo", "fecha"]],
            smn[["cvegeo", "fecha"]],
        ],
        ignore_index=True
    )

    keys = keys.dropna(subset=["cvegeo", "fecha"]).drop_duplicates()
    keys = keys.sort_values(["fecha", "cvegeo"]).reset_index(drop=True)

    return keys


def build_base_municipio_dia(
    catalogo: pd.DataFrame,
    conafor: pd.DataFrame,
    firms: pd.DataFrame,
    smn: pd.DataFrame
) -> pd.DataFrame:
    keys = build_key_universe(conafor, firms, smn)

    print(f"Universo sparse cvegeo-fecha: {len(keys):,} registros")

    base = keys.merge(
        catalogo,
        on="cvegeo",
        how="left"
    )

    # Imponer columnas administrativas al inicio.
    id_cols = ["cve_ent", "nom_ent", "cve_mun", "nom_mun", "cvegeo", "fecha"]
    base = base[id_cols].copy()

    conafor_merge = strip_admin_cols(conafor)
    firms_merge = strip_admin_cols(firms)
    smn_merge = strip_admin_cols(smn)

    print("Uniendo CONAFOR...")
    base = base.merge(
        conafor_merge,
        on=["cvegeo", "fecha"],
        how="left"
    )

    print("Uniendo FIRMS...")
    base = base.merge(
        firms_merge,
        on=["cvegeo", "fecha"],
        how="left"
    )

    print("Uniendo SMN...")
    base = base.merge(
        smn_merge,
        on=["cvegeo", "fecha"],
        how="left"
    )

    base = base.sort_values(["fecha", "cvegeo"]).reset_index(drop=True)

    return base


def apply_availability_rules(base: pd.DataFrame) -> pd.DataFrame:
    base = base.copy()

    fecha_dt = pd.to_datetime(base["fecha"], errors="coerce")

    # CONAFOR solo está disponible en el dataset final de 2005 a 2025.
    conafor_period_mask = (
        (fecha_dt >= pd.to_datetime(CONAFOR_START))
        & (fecha_dt <= pd.to_datetime(CONAFOR_END))
    )

    base["conafor_disponible"] = conafor_period_mask.astype(int)

    if "conafor_event_count" in base.columns:
        base["has_conafor"] = base["conafor_event_count"].notna().astype(int)

        # Para 2005-2025, ausencia de registro CONAFOR en municipio-día se interpreta
        # como 0 eventos registrados en la base integrada.
        base.loc[
            conafor_period_mask & base["conafor_event_count"].isna(),
            "conafor_event_count"
        ] = 0

        # Para 2001-2004 no se rellena con 0 porque CONAFOR no está disponible.
    else:
        base["has_conafor"] = 0

    # FIRMS: si no aparece en municipio-día integrado, se marca ausencia de detección.
    if "firms_count" in base.columns:
        base["has_firms"] = base["firms_count"].notna().astype(int)
        base["firms_count"] = base["firms_count"].fillna(0)
    else:
        base["has_firms"] = 0

    # SMN: no se rellenan variables meteorológicas con 0.
    # Solo se marca disponibilidad.
    if "smn_n_estaciones" in base.columns:
        base["has_smn"] = base["smn_n_estaciones"].notna().astype(int)
    else:
        base["has_smn"] = 0

    # Rellenos seguros para conteos auxiliares, no para medias meteorológicas.
    count_like_cols = [
        "firms_day_count",
        "firms_night_count",
        "firms_frp_valid_count",
        "firms_brightness_valid_count",
        "firms_bright_t31_valid_count",
        "firms_confidence_valid_count",
        "smn_precip_mm_valid_count",
        "smn_evap_mm_valid_count",
        "smn_tmin_c_valid_count",
        "smn_tmax_c_valid_count",
    ]

    for col in count_like_cols:
        if col in base.columns:
            base[col] = base[col].fillna(0)

    # Sumas FIRMS pueden ir en 0 cuando no hubo detecciones.
    firms_sum_cols = [
        "firms_frp_sum",
    ]

    for col in firms_sum_cols:
        if col in base.columns:
            base[col] = base[col].fillna(0)

    # Superficie CONAFOR: si no hay evento en periodo disponible, suma = 0.
    if "conafor_total_hectareas_sum" in base.columns:
        base.loc[
            conafor_period_mask & base["conafor_total_hectareas_sum"].isna(),
            "conafor_total_hectareas_sum"
        ] = 0

    # Banderas finales de trazabilidad.
    base["fuentes_disponibles"] = (
        "CONAFOR:" + base["has_conafor"].astype(str)
        + "|FIRMS:" + base["has_firms"].astype(str)
        + "|SMN:" + base["has_smn"].astype(str)
    )

    return base


def reorder_columns(base: pd.DataFrame) -> pd.DataFrame:
    priority_cols = [
        "cve_ent",
        "nom_ent",
        "cve_mun",
        "nom_mun",
        "cvegeo",
        "fecha",
        "conafor_disponible",
        "has_conafor",
        "has_firms",
        "has_smn",
        "fuentes_disponibles",
        "conafor_event_count",
        "conafor_total_hectareas_sum",
        "conafor_total_hectareas_mean",
        "firms_count",
        "firms_frp_sum",
        "firms_frp_mean",
        "firms_brightness_mean",
        "firms_bright_t31_mean",
        "firms_confidence_mean",
        "firms_day_count",
        "firms_night_count",
        "smn_n_estaciones",
        "smn_precip_mm_mean",
        "smn_evap_mm_mean",
        "smn_tmin_c_mean",
        "smn_tmax_c_mean",
    ]

    ordered = [col for col in priority_cols if col in base.columns]
    rest = [col for col in base.columns if col not in ordered]

    return base[ordered + rest].copy()


# =========================================================
# 4) VALIDACIÓN
# =========================================================

def build_validation_report(
    catalogo: pd.DataFrame,
    conafor: pd.DataFrame,
    firms: pd.DataFrame,
    smn: pd.DataFrame,
    base: pd.DataFrame
) -> pd.DataFrame:
    rows = []

    fecha_dt = pd.to_datetime(base["fecha"], errors="coerce")
    dup_base = int(base.duplicated(subset=["cvegeo", "fecha"]).sum())
    cvegeo_sin_catalogo = int(base["nom_mun"].isna().sum())

    rows.append(build_report_row(
        "catalogo_municipios_registros",
        len(catalogo),
        "ok" if len(catalogo) > 0 else "error",
        "Municipios disponibles en catálogo de integración."
    ))

    rows.append(build_report_row(
        "conafor_municipio_dia_registros",
        len(conafor),
        "ok" if len(conafor) > 0 else "warning",
        "Registros de CONAFOR municipio-día usados como insumo."
    ))

    rows.append(build_report_row(
        "firms_municipio_dia_registros",
        len(firms),
        "ok" if len(firms) > 0 else "warning",
        "Registros de FIRMS municipio-día usados como insumo."
    ))

    rows.append(build_report_row(
        "smn_municipio_dia_registros",
        len(smn),
        "ok" if len(smn) > 0 else "warning",
        "Registros de SMN municipio-día usados como insumo."
    ))

    rows.append(build_report_row(
        "base_municipio_dia_registros",
        len(base),
        "ok" if len(base) > 0 else "error",
        "Registros generados en integracion_municipio_dia_base.csv."
    ))

    rows.append(build_report_row(
        "base_fecha_min",
        fecha_dt.min().date() if fecha_dt.notna().any() else None,
        "ok",
        "Fecha mínima en base municipio-día."
    ))

    rows.append(build_report_row(
        "base_fecha_max",
        fecha_dt.max().date() if fecha_dt.notna().any() else None,
        "ok",
        "Fecha máxima en base municipio-día."
    ))

    rows.append(build_report_row(
        "base_duplicados_cvegeo_fecha",
        dup_base,
        "ok" if dup_base == 0 else "error",
        "Duplicados por clave cvegeo + fecha en base integrada."
    ))

    rows.append(build_report_row(
        "base_cvegeo_sin_catalogo",
        cvegeo_sin_catalogo,
        "ok" if cvegeo_sin_catalogo == 0 else "error",
        "Registros de base cuyo cvegeo no encontró correspondencia en catálogo municipal."
    ))

    fuera_periodo = int(
        (
            (fecha_dt < pd.to_datetime(PROJECT_START))
            | (fecha_dt > pd.to_datetime(PROJECT_END))
        ).sum()
    )

    rows.append(build_report_row(
        "base_fuera_periodo_proyecto_2001_2025",
        fuera_periodo,
        "ok" if fuera_periodo == 0 else "warning",
        "Registros fuera del periodo general del proyecto."
    ))

    for col in ["has_conafor", "has_firms", "has_smn"]:
        if col in base.columns:
            rows.append(build_report_row(
                f"{col}_suma",
                int(base[col].sum()),
                "ok",
                f"Total de filas con {col}=1."
            ))

    if "conafor_disponible" in base.columns:
        rows.append(build_report_row(
            "conafor_disponible_suma",
            int(base["conafor_disponible"].sum()),
            "ok",
            "Filas dentro del periodo con disponibilidad CONAFOR 2005-2025."
        ))

    return pd.DataFrame(rows)


# =========================================================
# 5) PIPELINE PRINCIPAL
# =========================================================

def main() -> None:
    print("\nIntegración 05 | Construcción de base municipio-día multifuente")

    validate_input_exists()

    print("Cargando catálogo municipal...")
    catalogo = load_catalogo_municipios()
    print(f"Catálogo municipal: {len(catalogo):,} registros")

    print("Cargando CONAFOR municipio-día...")
    conafor = load_municipio_dia(PATH_CONAFOR, "integracion_conafor_municipio_dia.csv")
    print(f"CONAFOR municipio-día: {len(conafor):,} registros")

    print("Cargando FIRMS municipio-día...")
    firms = load_municipio_dia(PATH_FIRMS, "integracion_firms_municipio_dia.csv")
    print(f"FIRMS municipio-día: {len(firms):,} registros")

    print("Cargando SMN municipio-día...")
    smn = load_municipio_dia(PATH_SMN, "integracion_smn_municipio_dia.csv")
    print(f"SMN municipio-día: {len(smn):,} registros")

    base = build_base_municipio_dia(
        catalogo=catalogo,
        conafor=conafor,
        firms=firms,
        smn=smn
    )

    base = apply_availability_rules(base)
    base = reorder_columns(base)

    validacion = build_validation_report(
        catalogo=catalogo,
        conafor=conafor,
        firms=firms,
        smn=smn,
        base=base
    )

    base.to_csv(OUT_BASE, index=False, encoding="utf-8-sig")
    validacion.to_csv(OUT_VALIDACION, index=False, encoding="utf-8-sig")

    errores = validacion[validacion["estatus"] == "error"]

    if not errores.empty:
        print("\nErrores de validación:")
        print(errores.to_string(index=False))
        raise ValueError("La construcción de base municipio-día terminó con errores.")

    print("\nArchivos generados:")
    print(f"- {OUT_BASE}")
    print(f"- {OUT_VALIDACION}")

    print("\nResumen:")
    print(f"- Base municipio-día: {len(base):,} registros")
    print(f"- Municipios únicos: {base['cvegeo'].nunique():,}")
    print(f"- Fecha mínima: {base['fecha'].min()}")
    print(f"- Fecha máxima: {base['fecha'].max()}")
    print(f"- has_conafor=1: {int(base['has_conafor'].sum()):,}")
    print(f"- has_firms=1: {int(base['has_firms'].sum()):,}")
    print(f"- has_smn=1: {int(base['has_smn'].sum()):,}")
    print(f"- Warnings: {(validacion['estatus'] == 'warning').sum()}")
    print(f"- Errores: {(validacion['estatus'] == 'error').sum()}")

    print("\nProceso terminado.")


if __name__ == "__main__":
    main()