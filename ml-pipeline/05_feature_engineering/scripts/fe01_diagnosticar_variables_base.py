# -*- coding: utf-8 -*-
"""
Feature Engineering | 01 Diagnóstico de variables base
------------------------------------------------------
Perfila las salidas principales de Integration para preparar la construcción
de matrices de Feature Engineering.

Este script:
- revisa bases dinámicas municipio-día y entidad-día,
- revisa contextos INEGI e INFyS a nivel municipal y estatal,
- clasifica columnas por rol metodológico,
- identifica posibles identificadores, trazabilidad, proxies/targets y leakage,
- genera reports para decidir qué variables pasan a las matrices FE.

Salidas:
- fe_01_diagnostico_variables_base.csv
- fe_01_resumen_variables_base.csv
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import pandas as pd


# =========================================================
# 1) IMPORTAR CONFIGURACIÓN
# =========================================================

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.append(str(SCRIPT_DIR))

from fe00_config import (  # type: ignore
    ensure_fe_directories,
    PROJECT_START_DATE,
    PROJECT_END_DATE,
    PATH_MUNICIPIO_DIA_BASE,
    PATH_ENTIDAD_DIA_BASE,
    PATH_INEGI_MUNICIPIO_CONTEXTO,
    PATH_INEGI_ENTIDAD_CONTEXTO,
    PATH_INFYS_MUNICIPIO_CONTEXTO,
    PATH_INFYS_ENTIDAD_CONTEXTO,
    PATH_FE_DIAGNOSTICO_VARIABLES_BASE,
    PATH_FE_RESUMEN_VARIABLES_BASE,
    MUNICIPIO_DUPLICATE_KEY,
    ENTIDAD_DUPLICATE_KEY,
    NON_FEATURE_COLS_COMMON,
    POTENTIAL_TARGET_OR_PROXY_COLS,
    SOURCE_FLAG_COLS,
    TRACEABILITY_COL_PATTERNS,
)


# =========================================================
# 2) DEFINICIÓN DE INSUMOS A DIAGNOSTICAR
# =========================================================

DATASETS_TO_PROFILE = {
    "municipio_dia_base": {
        "path": PATH_MUNICIPIO_DIA_BASE,
        "granularidad": "municipio_dia",
        "tipo_bloque": "base_dinamica",
        "duplicate_key": MUNICIPIO_DUPLICATE_KEY,
    },
    "entidad_dia_base": {
        "path": PATH_ENTIDAD_DIA_BASE,
        "granularidad": "entidad_dia",
        "tipo_bloque": "base_dinamica",
        "duplicate_key": ENTIDAD_DUPLICATE_KEY,
    },
    "inegi_municipio_contexto": {
        "path": PATH_INEGI_MUNICIPIO_CONTEXTO,
        "granularidad": "municipio",
        "tipo_bloque": "contexto_inegi",
        "duplicate_key": ["cvegeo"],
    },
    "inegi_entidad_contexto": {
        "path": PATH_INEGI_ENTIDAD_CONTEXTO,
        "granularidad": "entidad",
        "tipo_bloque": "contexto_inegi",
        "duplicate_key": ["cve_ent"],
    },
    "infys_municipio_contexto": {
        "path": PATH_INFYS_MUNICIPIO_CONTEXTO,
        "granularidad": "municipio",
        "tipo_bloque": "contexto_infys",
        "duplicate_key": ["cvegeo"],
    },
    "infys_entidad_contexto": {
        "path": PATH_INFYS_ENTIDAD_CONTEXTO,
        "granularidad": "entidad",
        "tipo_bloque": "contexto_infys",
        "duplicate_key": ["cve_ent"],
    },
}


# =========================================================
# 3) UTILIDADES GENERALES
# =========================================================

def safe_pct(num: int | float, den: int | float) -> float:
    if den == 0:
        return 0.0
    return round((num / den) * 100.0, 4)


def safe_read_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"No existe archivo de entrada: {path}")

    return pd.read_csv(path, encoding="utf-8-sig", low_memory=False)


def normalize_colname(col: str) -> str:
    return str(col).strip().lower()


def contains_any_pattern(text: str, patterns: list[str]) -> bool:
    text_low = text.lower()
    return any(p.lower() in text_low for p in patterns)


def infer_source_from_column(col: str, dataset_name: str, tipo_bloque: str) -> str:
    low = normalize_colname(col)

    if low.startswith("firms_") or "firms" in low:
        return "firms"
    if low.startswith("smn_") or "smn" in low:
        return "smn"
    if low.startswith("conafor_") or "conafor" in low:
        return "conafor"
    if low.startswith("inegi_") or tipo_bloque == "contexto_inegi":
        return "inegi"
    if low.startswith("infys_") or tipo_bloque == "contexto_infys":
        return "infys"
    if low in {"cve_ent", "nom_ent", "cve_mun", "nom_mun", "cvegeo", "fecha"}:
        return "llave_trazabilidad"
    if low in {"has_conafor", "has_firms", "has_smn"}:
        return "bandera_fuente"

    if "municipio" in dataset_name:
        return "mixta_municipal"
    if "entidad" in dataset_name:
        return "mixta_estatal"

    return "no_determinada"


def infer_variable_role(col: str) -> str:
    low = normalize_colname(col)

    if low in {"fecha"}:
        return "llave_temporal"

    if low in {"cve_ent", "nom_ent", "cve_mun", "nom_mun", "cvegeo"}:
        return "llave_espacial"

    if low in SOURCE_FLAG_COLS:
        return "bandera_disponibilidad_fuente"

    if low in POTENTIAL_TARGET_OR_PROXY_COLS:
        return "target_o_proxy_potencial"

    if contains_any_pattern(low, TRACEABILITY_COL_PATTERNS):
        return "trazabilidad"

    if low.startswith("has_"):
        return "bandera_disponibilidad_fuente"

    if low.endswith("_count"):
        return "conteo"

    if low.endswith("_sum"):
        return "acumulado"

    if low.endswith("_mean") or low.endswith("_avg"):
        return "promedio"

    if low.endswith("_min"):
        return "minimo"

    if low.endswith("_max"):
        return "maximo"

    if low.startswith("pct_") or low.endswith("_pct"):
        return "porcentaje"

    if low.startswith("sup_") or "superficie" in low or "area" in low:
        return "superficie_area"

    if low.startswith("long_") or "longitud" in low:
        return "longitud"

    if "lat" in low or "lon" in low:
        return "coordenada"

    return "variable_base"


def infer_feature_status(col: str, role: str, source: str) -> str:
    low = normalize_colname(col)

    if low in NON_FEATURE_COLS_COMMON:
        return "no_feature_trazabilidad"

    if role in {"llave_temporal", "llave_espacial", "trazabilidad"}:
        return "no_feature_trazabilidad"

    if role == "bandera_disponibilidad_fuente":
        return "no_feature_directa_revisar"

    if role == "target_o_proxy_potencial":
        return "no_feature_directa_target_o_proxy"

    if source == "llave_trazabilidad":
        return "no_feature_trazabilidad"

    return "candidata_revisar"


def infer_leakage_risk(col: str, role: str, source: str) -> str:
    low = normalize_colname(col)

    if low in {"has_conafor", "conafor_event_count", "conafor_sup_ha_sum"}:
        return "alto_si_objetivo_es_incendio_confirmado"

    if low.startswith("conafor_"):
        return "medio_alto_depende_del_objetivo"

    if low.startswith("has_"):
        return "medio_bandera_de_disponibilidad"

    if "future" in low or "posterior" in low or "siguiente" in low:
        return "alto_posible_informacion_futura"

    if role in {"llave_temporal", "llave_espacial", "trazabilidad"}:
        return "no_aplica_no_feature"

    return "bajo_revisar_contexto"


def get_top_value_info(s: pd.Series) -> tuple[Any, int | None, float | None]:
    non_null = s.dropna()

    if non_null.empty:
        return None, None, None

    vc = non_null.astype(str).value_counts(dropna=True)
    if vc.empty:
        return None, None, None

    top_value = vc.index[0]
    top_freq = int(vc.iloc[0])
    top_pct = safe_pct(top_freq, len(non_null))

    return top_value, top_freq, top_pct


def get_numeric_stats(s: pd.Series) -> dict[str, Any]:
    s_num = pd.to_numeric(s, errors="coerce")

    if not s_num.notna().any():
        return {
            "numeric_min": None,
            "numeric_max": None,
            "numeric_mean": None,
            "numeric_median": None,
            "numeric_std": None,
            "numeric_p01": None,
            "numeric_p99": None,
            "valores_negativos": None,
            "valores_cero": None,
            "valores_infinitos_aprox": None,
        }

    return {
        "numeric_min": float(s_num.min()),
        "numeric_max": float(s_num.max()),
        "numeric_mean": float(s_num.mean()),
        "numeric_median": float(s_num.median()),
        "numeric_std": float(s_num.std()) if s_num.notna().sum() > 1 else 0.0,
        "numeric_p01": float(s_num.quantile(0.01)),
        "numeric_p99": float(s_num.quantile(0.99)),
        "valores_negativos": int((s_num < 0).sum()),
        "valores_cero": int((s_num == 0).sum()),
        "valores_infinitos_aprox": int(s_num.isin([float("inf"), float("-inf")]).sum()),
    }


def diagnose_date_range(df: pd.DataFrame) -> dict[str, Any]:
    if "fecha" not in df.columns:
        return {
            "fecha_min": None,
            "fecha_max": None,
            "fechas_nulas": None,
            "fechas_fuera_periodo": None,
        }

    fechas = pd.to_datetime(df["fecha"], errors="coerce")
    start = pd.to_datetime(PROJECT_START_DATE)
    end = pd.to_datetime(PROJECT_END_DATE)

    return {
        "fecha_min": fechas.min().date().isoformat() if fechas.notna().any() else None,
        "fecha_max": fechas.max().date().isoformat() if fechas.notna().any() else None,
        "fechas_nulas": int(fechas.isna().sum()),
        "fechas_fuera_periodo": int(((fechas < start) | (fechas > end)).sum()),
    }


def count_duplicate_key_rows(df: pd.DataFrame, key_cols: list[str]) -> int | None:
    if not set(key_cols).issubset(df.columns):
        return None

    return int(df.duplicated(subset=key_cols, keep=False).sum())


# =========================================================
# 4) DIAGNÓSTICO POR DATASET
# =========================================================

def profile_dataset(
    dataset_name: str,
    path: Path,
    granularidad: str,
    tipo_bloque: str,
    duplicate_key: list[str],
) -> tuple[list[dict], dict]:
    print(f"\nDiagnosticando: {dataset_name}")
    print(f"Archivo: {path}")

    df = safe_read_csv(path)

    n_rows = len(df)
    n_cols = len(df.columns)

    duplicate_key_rows = count_duplicate_key_rows(df, duplicate_key)
    date_diag = diagnose_date_range(df)

    profile_rows = []

    for col in df.columns:
        s = df[col]

        nulls = int(s.isna().sum())
        null_pct = safe_pct(nulls, n_rows)

        try:
            nunique = int(s.nunique(dropna=True))
        except Exception:
            nunique = None

        top_value, top_freq, top_pct = get_top_value_info(s)

        numeric_stats = get_numeric_stats(s)

        role = infer_variable_role(col)
        source = infer_source_from_column(col, dataset_name, tipo_bloque)
        feature_status = infer_feature_status(col, role, source)
        leakage_risk = infer_leakage_risk(col, role, source)

        is_constant = bool(nunique is not None and nunique <= 1)
        is_high_null = bool(null_pct >= 50.0)
        is_all_null = bool(nulls == n_rows)
        is_candidate_numeric = bool(
            feature_status == "candidata_revisar"
            and numeric_stats["numeric_min"] is not None
        )

        profile_rows.append({
            "dataset": dataset_name,
            "ruta": str(path),
            "granularidad": granularidad,
            "tipo_bloque": tipo_bloque,
            "columna": col,
            "fuente_inferida": source,
            "rol_metodologico": role,
            "estatus_feature": feature_status,
            "riesgo_leakage": leakage_risk,
            "dtype_observado": str(s.dtype),
            "filas_dataset": n_rows,
            "columnas_dataset": n_cols,
            "nulos": nulls,
            "nulos_pct": null_pct,
            "unicos": nunique,
            "valor_mas_frecuente": top_value,
            "valor_mas_frecuente_freq": top_freq,
            "valor_mas_frecuente_pct": top_pct,
            "es_constante": is_constant,
            "nulos_50pct_o_mas": is_high_null,
            "columna_totalmente_nula": is_all_null,
            "candidata_numerica": is_candidate_numeric,
            **numeric_stats,
        })

    summary = {
        "dataset": dataset_name,
        "ruta": str(path),
        "granularidad": granularidad,
        "tipo_bloque": tipo_bloque,
        "filas": n_rows,
        "columnas": n_cols,
        "llave_duplicados_revisada": "|".join(duplicate_key),
        "filas_con_llave_duplicada": duplicate_key_rows,
        "columnas_con_nulos": int(sum(row["nulos"] > 0 for row in profile_rows)),
        "columnas_sin_nulos": int(sum(row["nulos"] == 0 for row in profile_rows)),
        "columnas_totalmente_nulas": int(sum(row["columna_totalmente_nula"] for row in profile_rows)),
        "columnas_nulos_50pct_o_mas": int(sum(row["nulos_50pct_o_mas"] for row in profile_rows)),
        "columnas_constantes": int(sum(row["es_constante"] for row in profile_rows)),
        "columnas_candidatas_revisar": int(sum(row["estatus_feature"] == "candidata_revisar" for row in profile_rows)),
        "columnas_candidatas_numericas": int(sum(row["candidata_numerica"] for row in profile_rows)),
        "columnas_no_feature_trazabilidad": int(sum(row["estatus_feature"] == "no_feature_trazabilidad" for row in profile_rows)),
        "columnas_target_o_proxy": int(sum(row["estatus_feature"] == "no_feature_directa_target_o_proxy" for row in profile_rows)),
        "columnas_posible_leakage_alto": int(sum(str(row["riesgo_leakage"]).startswith("alto") for row in profile_rows)),
        **date_diag,
    }

    print(f"Filas: {n_rows:,}")
    print(f"Columnas: {n_cols:,}")
    print(f"Columnas candidatas a revisar: {summary['columnas_candidatas_revisar']:,}")
    print(f"Columnas target/proxy: {summary['columnas_target_o_proxy']:,}")

    return profile_rows, summary


# =========================================================
# 5) PIPELINE PRINCIPAL
# =========================================================

def main() -> None:
    print("\nFeature Engineering 01 | Diagnóstico de variables base")

    ensure_fe_directories()

    all_profile_rows = []
    all_summary_rows = []

    for dataset_name, cfg in DATASETS_TO_PROFILE.items():
        profile_rows, summary = profile_dataset(
            dataset_name=dataset_name,
            path=cfg["path"],
            granularidad=cfg["granularidad"],
            tipo_bloque=cfg["tipo_bloque"],
            duplicate_key=cfg["duplicate_key"],
        )

        all_profile_rows.extend(profile_rows)
        all_summary_rows.append(summary)

    profile_df = pd.DataFrame(all_profile_rows)
    summary_df = pd.DataFrame(all_summary_rows)

    if not profile_df.empty:
        profile_df = profile_df.sort_values(
            by=[
                "granularidad",
                "tipo_bloque",
                "dataset",
                "estatus_feature",
                "riesgo_leakage",
                "nulos_pct",
                "columna",
            ],
            ascending=[True, True, True, True, True, False, True],
        ).reset_index(drop=True)

    summary_df = summary_df.sort_values(
        by=["granularidad", "tipo_bloque", "dataset"],
        ascending=[True, True, True],
    ).reset_index(drop=True)

    profile_df.to_csv(
        PATH_FE_DIAGNOSTICO_VARIABLES_BASE,
        index=False,
        encoding="utf-8-sig",
    )

    summary_df.to_csv(
        PATH_FE_RESUMEN_VARIABLES_BASE,
        index=False,
        encoding="utf-8-sig",
    )

    print("\nArchivos generados:")
    print(f"- {PATH_FE_DIAGNOSTICO_VARIABLES_BASE}")
    print(f"- {PATH_FE_RESUMEN_VARIABLES_BASE}")

    print("\nResumen general:")
    print(f"- Datasets diagnosticados: {len(summary_df):,}")
    print(f"- Variables perfiladas: {len(profile_df):,}")
    print(f"- Candidatas a revisar: {(profile_df['estatus_feature'] == 'candidata_revisar').sum():,}")
    print(f"- Target/proxy potenciales: {(profile_df['estatus_feature'] == 'no_feature_directa_target_o_proxy').sum():,}")
    print(f"- Posible leakage alto: {profile_df['riesgo_leakage'].astype(str).str.startswith('alto').sum():,}")

    print("\nProceso terminado.")


if __name__ == "__main__":
    main()