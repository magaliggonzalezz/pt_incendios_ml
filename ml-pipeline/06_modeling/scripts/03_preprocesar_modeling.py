# -*- coding: utf-8 -*-
"""
Modeling 03 | Preprocesamiento para modelado

Este script prepara la matriz numérica para PCA/SOM/Clustering.

Hace lo siguiente:
- Lee el dataset base de Modeling.
- Lee el diagnóstico de columnas.
- Separa IDs/perfilado de variables candidatas.
- Convierte variables candidatas a numéricas.
- Imputa nulos de forma controlada según familia de variable.
- Escala variables candidatas con StandardScaler.
- Genera matriz escalada, IDs y reporte de imputación.
"""

from pathlib import Path
import json
import pandas as pd
import numpy as np
from sklearn.preprocessing import StandardScaler
import joblib


# ============================================================
# CONFIGURACIÓN
# ============================================================

BASE_DIR = Path(r"C:\Users\Hp\OneDrive\Documentos\PT_Analisis")

FLUJO = "entidad_dia"

INPUT_BASE = BASE_DIR / "06_modeling" / "datasets" / FLUJO / f"modeling_{FLUJO}_base.csv"
INPUT_DIAG = BASE_DIR / "06_modeling" / "reports" / f"modeling_01_diagnostico_{FLUJO}.csv"

OUT_DATASETS = BASE_DIR / "06_modeling" / "datasets" / FLUJO
OUT_REPORTS = BASE_DIR / "06_modeling" / "reports"
OUT_MODELS = BASE_DIR / "06_modeling" / "models" / FLUJO / "preprocessing"

OUT_DATASETS.mkdir(parents=True, exist_ok=True)
OUT_REPORTS.mkdir(parents=True, exist_ok=True)
OUT_MODELS.mkdir(parents=True, exist_ok=True)

OUT_IDS = OUT_DATASETS / f"modeling_{FLUJO}_ids.csv"
OUT_SCALED = OUT_DATASETS / f"modeling_{FLUJO}_scaled.csv"
OUT_IMPUTATION_REPORT = OUT_REPORTS / f"modeling_03_imputacion_{FLUJO}.csv"
OUT_FEATURES = OUT_REPORTS / f"modeling_03_features_{FLUJO}.csv"
OUT_SCALER = OUT_MODELS / "standard_scaler.joblib"
OUT_IMPUTATION_VALUES = OUT_MODELS / "imputation_values.json"


# ============================================================
# COLUMNAS ID POR FLUJO
# ============================================================

ID_COLS_BY_FLOW = {
    "entidad_dia": [
        "cve_ent",
        "nom_ent",
        "fecha",
    ],
    "municipio_dia": [
        "cvegeo",
        "cve_ent",
        "cve_mun",
        "nom_ent",
        "nom_mun",
        "fecha",
    ],
}


# ============================================================
# FUNCIONES AUXILIARES
# ============================================================

def ensure_columns(df: pd.DataFrame, required_cols: list[str], context: str) -> None:
    missing = [c for c in required_cols if c not in df.columns]
    if missing:
        raise ValueError(f"Faltan columnas en {context}: {missing}")


def get_columns_from_diagnostic(df_diag: pd.DataFrame, uso: str) -> list[str]:
    return (
        df_diag.loc[df_diag["uso_sugerido"] == uso, "columna"]
        .dropna()
        .astype(str)
        .tolist()
    )


def get_family_from_diagnostic(df_diag: pd.DataFrame, col: str) -> str:
    match = df_diag.loc[df_diag["columna"] == col, "familia"]
    if match.empty:
        return "desconocida"
    return str(match.iloc[0])


def classify_imputation_strategy(col: str, family: str) -> str:
    c = col.lower()

    if family == "firms":
        return "zero_event_absence"

    if family == "temporal":
        return "mode_or_median"

    if family == "smn":
        return "median_by_entity_month_then_entity_then_global"

    if family in {"inegi", "infys"}:
        return "median_by_entity_then_global"

    return "global_median"


def fill_with_group_medians(
    df: pd.DataFrame,
    col: str,
    group_cols_list: list[list[str]],
) -> tuple[pd.Series, dict]:
    s = df[col].copy()
    values_used = {}

    for group_cols in group_cols_list:
        available_group_cols = [g for g in group_cols if g in df.columns]

        if not available_group_cols:
            continue

        before = int(s.isna().sum())
        group_medians = df.groupby(available_group_cols)[col].transform("median")
        s = s.fillna(group_medians)
        after = int(s.isna().sum())

        values_used["+".join(available_group_cols)] = {
            "filled": before - after,
            "remaining": after,
        }

    before_global = int(s.isna().sum())
    global_median = df[col].median()

    if pd.isna(global_median):
        global_median = 0

    s = s.fillna(global_median)
    after_global = int(s.isna().sum())

    values_used["global_median"] = {
        "value": float(global_median) if pd.notna(global_median) else None,
        "filled": before_global - after_global,
        "remaining": after_global,
    }

    return s, values_used


def impute_column(df: pd.DataFrame, col: str, family: str) -> tuple[pd.Series, str, dict]:
    strategy = classify_imputation_strategy(col, family)

    if strategy == "zero_event_absence":
        s = df[col].fillna(0)
        values_used = {"zero": {"value": 0, "filled": int(df[col].isna().sum()), "remaining": int(s.isna().sum())}}
        return s, strategy, values_used

    if strategy == "median_by_entity_month_then_entity_then_global":
        s, values_used = fill_with_group_medians(
            df=df,
            col=col,
            group_cols_list=[
                ["cve_ent", "mes"],
                ["cve_ent"],
            ],
        )
        return s, strategy, values_used

    if strategy == "median_by_entity_then_global":
        s, values_used = fill_with_group_medians(
            df=df,
            col=col,
            group_cols_list=[
                ["cve_ent"],
            ],
        )
        return s, strategy, values_used

    if strategy == "mode_or_median":
        if df[col].isna().sum() == 0:
            return df[col], strategy, {"none": {"filled": 0, "remaining": 0}}

        median_value = df[col].median()
        if pd.isna(median_value):
            median_value = 0

        s = df[col].fillna(median_value)
        values_used = {
            "median": {
                "value": float(median_value),
                "filled": int(df[col].isna().sum()),
                "remaining": int(s.isna().sum()),
            }
        }
        return s, strategy, values_used

    s, values_used = fill_with_group_medians(
        df=df,
        col=col,
        group_cols_list=[],
    )
    return s, strategy, values_used


# ============================================================
# PIPELINE PRINCIPAL
# ============================================================

def main():
    print("\nModeling 03 | Preprocesamiento para modelado")
    print(f"Flujo: {FLUJO}")

    if not INPUT_BASE.exists():
        raise FileNotFoundError(f"No existe dataset base: {INPUT_BASE}")

    if not INPUT_DIAG.exists():
        raise FileNotFoundError(f"No existe diagnóstico: {INPUT_DIAG}")

    print(f"\nLeyendo dataset base:")
    print(f"- {INPUT_BASE}")

    df = pd.read_csv(INPUT_BASE, encoding="utf-8-sig", low_memory=False)

    print(f"Filas: {len(df):,}")
    print(f"Columnas: {len(df.columns):,}")

    print(f"\nLeyendo diagnóstico:")
    print(f"- {INPUT_DIAG}")

    df_diag = pd.read_csv(INPUT_DIAG, encoding="utf-8-sig")

    ensure_columns(df_diag, ["columna", "familia", "uso_sugerido"], "diagnóstico Modeling 01")

    id_cols = ID_COLS_BY_FLOW[FLUJO]
    candidate_cols = get_columns_from_diagnostic(df_diag, "candidata_modelado")
    profiling_cols = get_columns_from_diagnostic(df_diag, "perfilado")

    ensure_columns(df, id_cols, "dataset base")
    ensure_columns(df, candidate_cols, "dataset base")
    ensure_columns(df, profiling_cols, "dataset base")

    print(f"\nColumnas ID: {len(id_cols):,}")
    print(f"Columnas candidatas: {len(candidate_cols):,}")
    print(f"Columnas perfilado/contraste: {len(profiling_cols):,}")

    # IDs + perfilado se conservan fuera de la matriz escalada
    ids = df[id_cols + profiling_cols].copy()

    # Convertir fecha
    ids["fecha"] = pd.to_datetime(ids["fecha"], errors="coerce").dt.strftime("%Y-%m-%d")

    if ids["fecha"].isna().sum() > 0:
        raise ValueError("Se detectaron fechas inválidas en IDs.")

    # Matriz de features
    X = df[candidate_cols].copy()

    for col in candidate_cols:
        X[col] = pd.to_numeric(X[col], errors="coerce")

    nulls_before_total = int(X.isna().sum().sum())

    print(f"\nNulos antes de imputación: {nulls_before_total:,}")

    imputation_rows = []
    imputation_values = {}

    # DataFrame auxiliar con IDs para imputación agrupada
    df_impute = pd.concat([df[id_cols].copy(), X], axis=1)

    if "fecha" in df_impute.columns:
        df_impute["fecha"] = pd.to_datetime(df_impute["fecha"], errors="coerce")
        df_impute["mes"] = df_impute["fecha"].dt.month

    for col in candidate_cols:
        family = get_family_from_diagnostic(df_diag, col)

        nulls_before = int(df_impute[col].isna().sum())
        unique_before = int(df_impute[col].nunique(dropna=True))

        imputed_series, strategy, values_used = impute_column(df_impute, col, family)

        df_impute[col] = imputed_series
        nulls_after = int(df_impute[col].isna().sum())

        imputation_values[col] = {
            "family": family,
            "strategy": strategy,
            "values_used": values_used,
        }

        imputation_rows.append({
            "columna": col,
            "familia": family,
            "estrategia_imputacion": strategy,
            "n_null_before": nulls_before,
            "n_null_after": nulls_after,
            "n_imputed": nulls_before - nulls_after,
            "n_unique_before": unique_before,
            "n_unique_after": int(df_impute[col].nunique(dropna=True)),
        })

    X_imputed = df_impute[candidate_cols].copy()

    nulls_after_total = int(X_imputed.isna().sum().sum())

    print(f"Nulos después de imputación: {nulls_after_total:,}")

    if nulls_after_total > 0:
        cols_with_nulls = X_imputed.columns[X_imputed.isna().any()].tolist()
        raise ValueError(f"Aún quedan nulos después de imputación en columnas: {cols_with_nulls}")

    # Validar constantes después de imputación
    constant_cols = [c for c in X_imputed.columns if X_imputed[c].nunique(dropna=True) <= 1]

    if constant_cols:
        raise ValueError(
            "Se detectaron columnas constantes después de imputación. "
            f"Revísalas antes de escalar: {constant_cols}"
        )

    # Escalado
    print("\nAplicando StandardScaler...")

    scaler = StandardScaler()
    X_scaled_array = scaler.fit_transform(X_imputed)

    X_scaled = pd.DataFrame(
        X_scaled_array,
        columns=candidate_cols,
        index=X_imputed.index,
    )

    # Validación final
    if X_scaled.isna().sum().sum() > 0:
        raise ValueError("La matriz escalada contiene nulos.")

    if np.isinf(X_scaled.to_numpy()).sum() > 0:
        raise ValueError("La matriz escalada contiene valores infinitos.")

    # Guardar salidas
    ids.to_csv(OUT_IDS, index=False, encoding="utf-8-sig")
    X_scaled.to_csv(OUT_SCALED, index=False, encoding="utf-8-sig")

    df_imputation_report = pd.DataFrame(imputation_rows)
    df_imputation_report.to_csv(OUT_IMPUTATION_REPORT, index=False, encoding="utf-8-sig")

    df_features = pd.DataFrame({
        "feature": candidate_cols,
        "familia": [get_family_from_diagnostic(df_diag, c) for c in candidate_cols],
        "mean_original_imputed": [float(X_imputed[c].mean()) for c in candidate_cols],
        "std_original_imputed": [float(X_imputed[c].std()) for c in candidate_cols],
        "min_original_imputed": [float(X_imputed[c].min()) for c in candidate_cols],
        "max_original_imputed": [float(X_imputed[c].max()) for c in candidate_cols],
    })
    df_features.to_csv(OUT_FEATURES, index=False, encoding="utf-8-sig")

    joblib.dump(scaler, OUT_SCALER)

    with open(OUT_IMPUTATION_VALUES, "w", encoding="utf-8") as f:
        json.dump(imputation_values, f, ensure_ascii=False, indent=2)

    print(f"\nArchivos generados:")
    print(f"- {OUT_IDS}")
    print(f"- {OUT_SCALED}")
    print(f"- {OUT_IMPUTATION_REPORT}")
    print(f"- {OUT_FEATURES}")
    print(f"- {OUT_SCALER}")
    print(f"- {OUT_IMPUTATION_VALUES}")

    print(f"\nFilas matriz escalada: {len(X_scaled):,}")
    print(f"Columnas matriz escalada: {len(X_scaled.columns):,}")

    print("\nProceso terminado.")


if __name__ == "__main__":
    main()