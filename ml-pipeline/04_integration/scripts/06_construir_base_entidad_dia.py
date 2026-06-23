# -*- coding: utf-8 -*-
"""
Integración 06 | Construcción de base entidad-día multifuente

Este script construye la base integrada entidad-día a partir de la base
municipio-día validada.

Salidas
-------
1) 04_integration/datasets/integracion_entidad_dia_base.csv
2) 04_integration/reports/integracion_06_validacion_entidad_dia_base.csv

Objetivo
--------
- Derivar una base estatal diaria desde integracion_municipio_dia_base.csv.
- Mantener coherencia con la integración municipal.
- Preparar una salida útil para visualización estatal, mapas coropléticos
  estatales y análisis exploratorio agregado.
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

PATH_MUNICIPIO_DIA = INTEGRATION_DATASETS_DIR / "integracion_municipio_dia_base.csv"
PATH_CATALOGO_ENTIDADES = INTEGRATION_DATASETS_DIR / "integracion_catalogo_entidades.csv"

OUT_ENTIDAD_DIA = INTEGRATION_DATASETS_DIR / "integracion_entidad_dia_base.csv"
OUT_VALIDACION = INTEGRATION_REPORTS_DIR / "integracion_06_validacion_entidad_dia_base.csv"

INTEGRATION_DATASETS_DIR.mkdir(parents=True, exist_ok=True)
INTEGRATION_REPORTS_DIR.mkdir(parents=True, exist_ok=True)

PROJECT_START = "2001-01-01"
PROJECT_END = "2025-12-31"


# =========================================================
# 2) UTILIDADES
# =========================================================

def normalize_code(series: pd.Series, width: int) -> pd.Series:
    s = series.astype(str).str.strip()
    s = s.str.replace(r"\.0$", "", regex=True)
    extracted = s.str.extract(r"(\d+)", expand=False)
    return extracted.where(extracted.notna(), pd.NA).str.zfill(width)


def normalize_cve_ent(series: pd.Series) -> pd.Series:
    return normalize_code(series, 2)


def build_report_row(indicador: str, valor, estatus: str, observacion: str) -> dict:
    return {
        "indicador": indicador,
        "valor": valor,
        "estatus": estatus,
        "observacion": observacion,
    }


def safe_weighted_mean_from_mean_and_count(
    df: pd.DataFrame,
    mean_col: str,
    count_col: str
) -> pd.Series:
    """
    Calcula media ponderada cuando la tabla de entrada ya está agregada.

    Ejemplo:
    media estatal = suma(media_municipal * n_validos_municipales) / suma(n_validos_municipales)
    """
    weighted_sum = (df[mean_col] * df[count_col]).sum(min_count=1)
    valid_count = df[count_col].sum(min_count=1)

    if pd.isna(valid_count) or valid_count == 0:
        return pd.NA

    return weighted_sum / valid_count


def validate_input_exists() -> None:
    missing = []

    if not PATH_MUNICIPIO_DIA.exists():
        missing.append(f"- municipio-día: {PATH_MUNICIPIO_DIA}")

    if not PATH_CATALOGO_ENTIDADES.exists():
        missing.append(f"- catálogo entidades: {PATH_CATALOGO_ENTIDADES}")

    if missing:
        detail = "\n".join(missing)
        raise FileNotFoundError(f"Faltan insumos para construir entidad-día:\n{detail}")


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


def load_municipio_dia() -> pd.DataFrame:
    df = pd.read_csv(
        PATH_MUNICIPIO_DIA,
        encoding="utf-8-sig",
        dtype={"cve_ent": str, "cve_mun": str, "cvegeo": str},
        low_memory=False
    )

    required = {"cve_ent", "nom_ent", "cvegeo", "fecha"}
    missing = required - set(df.columns)

    if missing:
        raise ValueError(f"Faltan columnas requeridas en municipio-día: {missing}")

    df["cve_ent"] = normalize_cve_ent(df["cve_ent"])
    df["fecha"] = pd.to_datetime(df["fecha"], errors="coerce").dt.date

    dup = int(df.duplicated(subset=["cvegeo", "fecha"]).sum())
    if dup > 0:
        raise ValueError(f"La base municipio-día tiene duplicados cvegeo + fecha: {dup}")

    return df


# =========================================================
# 3) CONSTRUCCIÓN ENTIDAD-DÍA
# =========================================================

def aggregate_entidad_dia(municipio_dia: pd.DataFrame, catalogo_entidades: pd.DataFrame) -> pd.DataFrame:
    df = municipio_dia.copy()

    numeric_defaults = {
        "conafor_event_count": 0,
        "conafor_total_hectareas_sum": 0,
        "firms_count": 0,
        "firms_frp_sum": 0,
        "firms_day_count": 0,
        "firms_night_count": 0,
        "has_conafor": 0,
        "has_firms": 0,
        "has_smn": 0,
        "conafor_disponible": 0,
        "smn_n_estaciones": 0,
    }

    for col, default in numeric_defaults.items():
        if col not in df.columns:
            df[col] = default
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(default)

    # Columnas de conteo válido usadas para medias ponderadas.
    valid_count_cols = [
        "firms_frp_valid_count",
        "firms_brightness_valid_count",
        "firms_bright_t31_valid_count",
        "firms_confidence_valid_count",
        "smn_precip_mm_valid_count",
        "smn_evap_mm_valid_count",
        "smn_tmin_c_valid_count",
        "smn_tmax_c_valid_count",
    ]

    for col in valid_count_cols:
        if col not in df.columns:
            df[col] = 0
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    mean_cols = [
        "firms_frp_mean",
        "firms_brightness_mean",
        "firms_bright_t31_mean",
        "firms_confidence_mean",
        "smn_precip_mm_mean",
        "smn_evap_mm_mean",
        "smn_tmin_c_mean",
        "smn_tmax_c_mean",
    ]

    for col in mean_cols:
        if col not in df.columns:
            df[col] = pd.NA
        df[col] = pd.to_numeric(df[col], errors="coerce")

    grouped_rows = []

    group_cols = ["cve_ent", "fecha"]

    for (cve_ent, fecha), group in df.groupby(group_cols, dropna=False):
        row = {
            "cve_ent": cve_ent,
            "fecha": fecha,

            # Cobertura municipal dentro de la base sparse.
            "n_municipios_base": group["cvegeo"].nunique(),
            "n_municipios_con_conafor": int((group["has_conafor"] == 1).sum()),
            "n_municipios_con_firms": int((group["has_firms"] == 1).sum()),
            "n_municipios_con_smn": int((group["has_smn"] == 1).sum()),

            # Disponibilidad / presencia.
            "conafor_disponible": int(group["conafor_disponible"].max()),
            "has_conafor": int(group["has_conafor"].max()),
            "has_firms": int(group["has_firms"].max()),
            "has_smn": int(group["has_smn"].max()),

            # CONAFOR.
            "conafor_event_count": group["conafor_event_count"].sum(min_count=1),
            "conafor_total_hectareas_sum": group["conafor_total_hectareas_sum"].sum(min_count=1),

            # FIRMS.
            "firms_count": group["firms_count"].sum(min_count=1),
            "firms_frp_sum": group["firms_frp_sum"].sum(min_count=1),
            "firms_day_count": group["firms_day_count"].sum(min_count=1),
            "firms_night_count": group["firms_night_count"].sum(min_count=1),

            # SMN.
            "smn_n_estaciones": group["smn_n_estaciones"].sum(min_count=1),

            # Conteos válidos auxiliares.
            "firms_frp_valid_count": group["firms_frp_valid_count"].sum(min_count=1),
            "firms_brightness_valid_count": group["firms_brightness_valid_count"].sum(min_count=1),
            "firms_bright_t31_valid_count": group["firms_bright_t31_valid_count"].sum(min_count=1),
            "firms_confidence_valid_count": group["firms_confidence_valid_count"].sum(min_count=1),
            "smn_precip_mm_valid_count": group["smn_precip_mm_valid_count"].sum(min_count=1),
            "smn_evap_mm_valid_count": group["smn_evap_mm_valid_count"].sum(min_count=1),
            "smn_tmin_c_valid_count": group["smn_tmin_c_valid_count"].sum(min_count=1),
            "smn_tmax_c_valid_count": group["smn_tmax_c_valid_count"].sum(min_count=1),
        }

        # Media de hectáreas por evento CONAFOR a nivel entidad-día.
        if row["conafor_event_count"] and row["conafor_event_count"] > 0:
            row["conafor_total_hectareas_mean"] = (
                row["conafor_total_hectareas_sum"] / row["conafor_event_count"]
            )
        else:
            row["conafor_total_hectareas_mean"] = pd.NA

        # Medias FIRMS ponderadas por número de valores válidos.
        row["firms_frp_mean"] = safe_weighted_mean_from_mean_and_count(
            group, "firms_frp_mean", "firms_frp_valid_count"
        )
        row["firms_brightness_mean"] = safe_weighted_mean_from_mean_and_count(
            group, "firms_brightness_mean", "firms_brightness_valid_count"
        )
        row["firms_bright_t31_mean"] = safe_weighted_mean_from_mean_and_count(
            group, "firms_bright_t31_mean", "firms_bright_t31_valid_count"
        )
        row["firms_confidence_mean"] = safe_weighted_mean_from_mean_and_count(
            group, "firms_confidence_mean", "firms_confidence_valid_count"
        )

        # Medias SMN ponderadas por número de observaciones válidas.
        row["smn_precip_mm_mean"] = safe_weighted_mean_from_mean_and_count(
            group, "smn_precip_mm_mean", "smn_precip_mm_valid_count"
        )
        row["smn_evap_mm_mean"] = safe_weighted_mean_from_mean_and_count(
            group, "smn_evap_mm_mean", "smn_evap_mm_valid_count"
        )
        row["smn_tmin_c_mean"] = safe_weighted_mean_from_mean_and_count(
            group, "smn_tmin_c_mean", "smn_tmin_c_valid_count"
        )
        row["smn_tmax_c_mean"] = safe_weighted_mean_from_mean_and_count(
            group, "smn_tmax_c_mean", "smn_tmax_c_valid_count"
        )

        grouped_rows.append(row)

    entidad_dia = pd.DataFrame(grouped_rows)

    entidad_dia = entidad_dia.merge(
        catalogo_entidades,
        on="cve_ent",
        how="left"
    )

    # Reordenar columnas.
    priority_cols = [
        "cve_ent",
        "nom_ent",
        "fecha",
        "conafor_disponible",
        "has_conafor",
        "has_firms",
        "has_smn",
        "n_municipios_base",
        "n_municipios_con_conafor",
        "n_municipios_con_firms",
        "n_municipios_con_smn",
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
        "firms_frp_valid_count",
        "firms_brightness_valid_count",
        "firms_bright_t31_valid_count",
        "firms_confidence_valid_count",
        "smn_precip_mm_valid_count",
        "smn_evap_mm_valid_count",
        "smn_tmin_c_valid_count",
        "smn_tmax_c_valid_count",
    ]

    ordered = [col for col in priority_cols if col in entidad_dia.columns]
    rest = [col for col in entidad_dia.columns if col not in ordered]

    entidad_dia = entidad_dia[ordered + rest].copy()
    entidad_dia = entidad_dia.sort_values(["fecha", "cve_ent"]).reset_index(drop=True)

    return entidad_dia


# =========================================================
# 4) VALIDACIÓN
# =========================================================

def build_validation_report(
    municipio_dia: pd.DataFrame,
    catalogo_entidades: pd.DataFrame,
    entidad_dia: pd.DataFrame
) -> pd.DataFrame:
    rows = []

    fecha_dt = pd.to_datetime(entidad_dia["fecha"], errors="coerce")

    dup_ent_dia = int(entidad_dia.duplicated(subset=["cve_ent", "fecha"]).sum())
    cve_ent_sin_catalogo = int(entidad_dia["nom_ent"].isna().sum())

    rows.append(build_report_row(
        "municipio_dia_registros_insumo",
        len(municipio_dia),
        "ok" if len(municipio_dia) > 0 else "error",
        "Registros de integracion_municipio_dia_base.csv usados como insumo."
    ))

    rows.append(build_report_row(
        "catalogo_entidades_registros",
        len(catalogo_entidades),
        "ok" if len(catalogo_entidades) == 32 else "warning",
        "Entidades disponibles en catálogo de integración."
    ))

    rows.append(build_report_row(
        "entidad_dia_registros",
        len(entidad_dia),
        "ok" if len(entidad_dia) > 0 else "error",
        "Registros generados en integracion_entidad_dia_base.csv."
    ))

    rows.append(build_report_row(
        "entidades_unicas_base",
        entidad_dia["cve_ent"].nunique(),
        "ok" if entidad_dia["cve_ent"].nunique() <= 32 else "error",
        "Entidades únicas presentes en la base entidad-día."
    ))

    rows.append(build_report_row(
        "entidad_dia_fecha_min",
        fecha_dt.min().date() if fecha_dt.notna().any() else None,
        "ok",
        "Fecha mínima en base entidad-día."
    ))

    rows.append(build_report_row(
        "entidad_dia_fecha_max",
        fecha_dt.max().date() if fecha_dt.notna().any() else None,
        "ok",
        "Fecha máxima en base entidad-día."
    ))

    rows.append(build_report_row(
        "entidad_dia_duplicados_cve_ent_fecha",
        dup_ent_dia,
        "ok" if dup_ent_dia == 0 else "error",
        "Duplicados por clave cve_ent + fecha en base entidad-día."
    ))

    rows.append(build_report_row(
        "entidad_dia_cve_ent_sin_catalogo",
        cve_ent_sin_catalogo,
        "ok" if cve_ent_sin_catalogo == 0 else "error",
        "Registros cuyo cve_ent no encontró correspondencia en catálogo de entidades."
    ))

    fuera_periodo = int(
        (
            (fecha_dt < pd.to_datetime(PROJECT_START))
            | (fecha_dt > pd.to_datetime(PROJECT_END))
        ).sum()
    )

    rows.append(build_report_row(
        "entidad_dia_fuera_periodo_proyecto_2001_2025",
        fuera_periodo,
        "ok" if fuera_periodo == 0 else "warning",
        "Registros fuera del periodo general del proyecto."
    ))

    for col in ["has_conafor", "has_firms", "has_smn"]:
        if col in entidad_dia.columns:
            rows.append(build_report_row(
                f"{col}_suma",
                int(entidad_dia[col].sum()),
                "ok",
                f"Total de entidad-día con {col}=1."
            ))

    if "conafor_event_count" in entidad_dia.columns and "conafor_event_count" in municipio_dia.columns:
        suma_entidad = float(entidad_dia["conafor_event_count"].sum())
        suma_municipio = float(pd.to_numeric(municipio_dia["conafor_event_count"], errors="coerce").fillna(0).sum())

        rows.append(build_report_row(
            "control_suma_conafor_event_count",
            f"entidad={suma_entidad} | municipio={suma_municipio}",
            "ok" if abs(suma_entidad - suma_municipio) < 0.0001 else "error",
            "Control de consistencia: suma estatal debe coincidir con suma municipal."
        ))

    if "firms_count" in entidad_dia.columns and "firms_count" in municipio_dia.columns:
        suma_entidad = float(entidad_dia["firms_count"].sum())
        suma_municipio = float(pd.to_numeric(municipio_dia["firms_count"], errors="coerce").fillna(0).sum())

        rows.append(build_report_row(
            "control_suma_firms_count",
            f"entidad={suma_entidad} | municipio={suma_municipio}",
            "ok" if abs(suma_entidad - suma_municipio) < 0.0001 else "error",
            "Control de consistencia: suma estatal debe coincidir con suma municipal."
        ))

    return pd.DataFrame(rows)


# =========================================================
# 5) PIPELINE PRINCIPAL
# =========================================================

def main() -> None:
    print("\nIntegración 06 | Construcción de base entidad-día multifuente")

    validate_input_exists()

    print("Cargando catálogo de entidades...")
    catalogo_entidades = load_catalogo_entidades()
    print(f"Catálogo entidades: {len(catalogo_entidades):,} registros")

    print("Cargando base municipio-día...")
    municipio_dia = load_municipio_dia()
    print(f"Municipio-día: {len(municipio_dia):,} registros")

    print("Agregando a entidad-día...")
    entidad_dia = aggregate_entidad_dia(
        municipio_dia=municipio_dia,
        catalogo_entidades=catalogo_entidades
    )

    validacion = build_validation_report(
        municipio_dia=municipio_dia,
        catalogo_entidades=catalogo_entidades,
        entidad_dia=entidad_dia
    )

    entidad_dia.to_csv(OUT_ENTIDAD_DIA, index=False, encoding="utf-8-sig")
    validacion.to_csv(OUT_VALIDACION, index=False, encoding="utf-8-sig")

    errores = validacion[validacion["estatus"] == "error"]

    if not errores.empty:
        print("\nErrores de validación:")
        print(errores.to_string(index=False))
        raise ValueError("La construcción de base entidad-día terminó con errores.")

    print("\nArchivos generados:")
    print(f"- {OUT_ENTIDAD_DIA}")
    print(f"- {OUT_VALIDACION}")

    print("\nResumen:")
    print(f"- Base entidad-día: {len(entidad_dia):,} registros")
    print(f"- Entidades únicas: {entidad_dia['cve_ent'].nunique():,}")
    print(f"- Fecha mínima: {entidad_dia['fecha'].min()}")
    print(f"- Fecha máxima: {entidad_dia['fecha'].max()}")
    print(f"- has_conafor=1: {int(entidad_dia['has_conafor'].sum()):,}")
    print(f"- has_firms=1: {int(entidad_dia['has_firms'].sum()):,}")
    print(f"- has_smn=1: {int(entidad_dia['has_smn'].sum()):,}")
    print(f"- Warnings: {(validacion['estatus'] == 'warning').sum()}")
    print(f"- Errores: {(validacion['estatus'] == 'error').sum()}")

    print("\nProceso terminado.")


if __name__ == "__main__":
    main()