# -*- coding: utf-8 -*-
"""
Modeling 03 | Preprocesamiento para modelado municipio-día

Este script prepara la matriz municipio-día para PCA/SOM/clustering.

Hace lo siguiente:
- Lee el dataset base de Modeling por chunks.
- Lee el diagnóstico de columnas generado en Modeling 01.
- Separa columnas ID, perfilado y candidatas de modelado.
- Calcula valores de imputación controlada usando una muestra distribuida por chunks.
- Imputa columnas candidatas sin modificar datasets de Feature Engineering.
- Ajusta StandardScaler con partial_fit por chunks.
- Genera matriz escalada por chunks.
- Guarda IDs/perfilado, matriz escalada, reporte de imputación, reporte de features y objetos de preprocesamiento.
"""

from pathlib import Path
import json
import numpy as np
import pandas as pd
import joblib
from sklearn.preprocessing import StandardScaler


# ============================================================
# CONFIGURACIÓN
# ============================================================

BASE_DIR = Path(r"C:\Users\Hp\OneDrive\Documentos\PT_Analisis")

FLUJO = "municipio_dia"

CHUNKSIZE = 300_000
SAMPLE_PER_CHUNK = 10_000
RANDOM_STATE = 42

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
OUT_FEATURES_REPORT = OUT_REPORTS / f"modeling_03_features_{FLUJO}.csv"

OUT_SCALER = OUT_MODELS / "standard_scaler.joblib"
OUT_IMPUTATION_VALUES = OUT_MODELS / "imputation_values.json"


ID_COLS = [
    "cvegeo",
    "cve_ent",
    "cve_mun",
    "nom_ent",
    "nom_mun",
    "fecha",
]


# ============================================================
# FUNCIONES AUXILIARES
# ============================================================

def ensure_file(path: Path, label: str) -> None:
    if not path.exists():
        raise FileNotFoundError(f"No existe {label}: {path}")


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


def normalize_id_columns(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    if "cve_ent" in df.columns:
        df["cve_ent"] = (
            df["cve_ent"]
            .astype(str)
            .str.replace(r"\.0$", "", regex=True)
            .str.zfill(2)
        )

    if "cve_mun" in df.columns:
        df["cve_mun"] = (
            df["cve_mun"]
            .astype(str)
            .str.replace(r"\.0$", "", regex=True)
            .str.zfill(3)
        )

    if "cvegeo" in df.columns:
        df["cvegeo"] = (
            df["cvegeo"]
            .astype(str)
            .str.replace(r"\.0$", "", regex=True)
            .str.zfill(5)
        )

    if "nom_ent" in df.columns:
        df["nom_ent"] = df["nom_ent"].astype(str).str.strip()

    if "nom_mun" in df.columns:
        df["nom_mun"] = df["nom_mun"].astype(str).str.strip()

    if "fecha" in df.columns:
        df["fecha"] = pd.to_datetime(df["fecha"], errors="coerce").dt.strftime("%Y-%m-%d")

    return df


def to_numeric_selected(df: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
    df = df.copy()

    for col in cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    return df


def classify_imputation_strategy(col: str) -> str:
    c = col.lower()

    if c.startswith("firms_"):
        return "zero_absence_signal"

    if c.startswith("smn_"):
        return "median_cve_ent_mes_then_cve_ent_then_global"

    if c.startswith("inegi_") or c.startswith("infys_") or c == "municipio_area_km2":
        return "median_cve_ent_then_global"

    if c in {
        "anio",
        "mes",
        "dia",
        "dia_del_anio",
        "semana_iso",
        "trimestre",
        "es_temporada_incendios",
    }:
        return "global_median"

    return "median_cve_ent_then_global"


def build_sample(input_path: Path, usecols: list[str]) -> pd.DataFrame:
    samples = []

    print("\nConstruyendo muestra para imputación...")

    for i, chunk in enumerate(
        pd.read_csv(
            input_path,
            encoding="utf-8-sig",
            usecols=usecols,
            chunksize=CHUNKSIZE,
            low_memory=False,
        ),
        start=1,
    ):
        chunk = normalize_id_columns(chunk)

        if "mes" in chunk.columns:
            chunk["mes"] = pd.to_numeric(chunk["mes"], errors="coerce")

        n_sample = min(SAMPLE_PER_CHUNK, len(chunk))

        sample = chunk.sample(
            n=n_sample,
            random_state=RANDOM_STATE + i,
        )

        samples.append(sample)

        print(f"- chunk {i:,}: muestra {n_sample:,} filas")

    sample_df = pd.concat(samples, ignore_index=True)

    print(f"Muestra total para imputación: {len(sample_df):,} filas")

    return sample_df


def build_imputation_maps(sample_df: pd.DataFrame, candidate_cols: list[str]) -> tuple[dict, pd.DataFrame]:
    sample_df = to_numeric_selected(sample_df, candidate_cols)

    imputation = {
        "flujo": FLUJO,
        "sample_rows": int(len(sample_df)),
        "strategies": {},
        "global_values": {},
        "entity_values": {},
        "entity_month_values": {},
    }

    report_rows = []

    for col in candidate_cols:
        strategy = classify_imputation_strategy(col)
        s = pd.to_numeric(sample_df[col], errors="coerce")

        global_value = s.median()

        used_zero_fallback = False
        if pd.isna(global_value):
            global_value = 0.0
            used_zero_fallback = True

        imputation["strategies"][col] = strategy
        imputation["global_values"][col] = float(global_value)

        if strategy in {
            "median_cve_ent_mes_then_cve_ent_then_global",
            "median_cve_ent_then_global",
        }:
            entity_median = (
                sample_df[["cve_ent", col]]
                .assign(**{col: pd.to_numeric(sample_df[col], errors="coerce")})
                .groupby("cve_ent")[col]
                .median()
                .dropna()
                .to_dict()
            )

            imputation["entity_values"][col] = {
                str(k): float(v) for k, v in entity_median.items()
            }

        if strategy == "median_cve_ent_mes_then_cve_ent_then_global":
            entity_month_df = sample_df[["cve_ent", "mes", col]].copy()
            entity_month_df[col] = pd.to_numeric(entity_month_df[col], errors="coerce")
            entity_month_df["mes"] = pd.to_numeric(entity_month_df["mes"], errors="coerce")

            entity_month_median = (
                entity_month_df
                .dropna(subset=["cve_ent", "mes"])
                .assign(mes=lambda x: x["mes"].astype(int))
                .groupby(["cve_ent", "mes"])[col]
                .median()
                .dropna()
            )

            imputation["entity_month_values"][col] = {
                f"{str(idx[0])}|{int(idx[1])}": float(value)
                for idx, value in entity_month_median.items()
            }

        report_rows.append({
            "columna": col,
            "estrategia": strategy,
            "global_imputation_value": float(global_value),
            "sample_nulls": int(s.isna().sum()),
            "sample_null_pct": float(s.isna().mean()),
            "sample_non_nulls": int(s.notna().sum()),
            "used_zero_fallback": used_zero_fallback,
        })

    report = pd.DataFrame(report_rows)

    return imputation, report


def impute_chunk(df: pd.DataFrame, candidate_cols: list[str], imputation: dict) -> pd.DataFrame:
    df = df.copy()
    df = normalize_id_columns(df)
    df = to_numeric_selected(df, candidate_cols)

    if "mes" in df.columns:
        df["mes"] = pd.to_numeric(df["mes"], errors="coerce")

    for col in candidate_cols:
        strategy = imputation["strategies"][col]
        global_value = imputation["global_values"][col]

        if strategy == "zero_absence_signal":
            df[col] = df[col].fillna(0)
            continue

        if strategy == "median_cve_ent_mes_then_cve_ent_then_global":
            entity_month_map = imputation.get("entity_month_values", {}).get(col, {})
            entity_map = imputation.get("entity_values", {}).get(col, {})

            key = df["cve_ent"].astype(str) + "|" + df["mes"].fillna(-1).astype(int).astype(str)

            fill_entity_month = key.map(entity_month_map)
            df[col] = df[col].fillna(fill_entity_month)

            fill_entity = df["cve_ent"].astype(str).map(entity_map)
            df[col] = df[col].fillna(fill_entity)

            df[col] = df[col].fillna(global_value)
            continue

        if strategy == "median_cve_ent_then_global":
            entity_map = imputation.get("entity_values", {}).get(col, {})
            fill_entity = df["cve_ent"].astype(str).map(entity_map)
            df[col] = df[col].fillna(fill_entity)
            df[col] = df[col].fillna(global_value)
            continue

        df[col] = df[col].fillna(global_value)

    remaining_nulls = int(df[candidate_cols].isna().sum().sum())

    if remaining_nulls > 0:
        raise ValueError(f"Después de imputar quedaron {remaining_nulls:,} nulos.")

    return df


def remove_output_if_exists(path: Path) -> None:
    if path.exists():
        path.unlink()


def save_json(data: dict, path: Path) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# ============================================================
# PIPELINE PRINCIPAL
# ============================================================

def main():
    print("\nModeling 03 | Preprocesamiento para modelado")
    print(f"Flujo: {FLUJO}")

    ensure_file(INPUT_BASE, "dataset base")
    ensure_file(INPUT_DIAG, "diagnóstico Modeling 01")

    print("\nLeyendo diagnóstico:")
    print(f"- {INPUT_DIAG}")

    df_diag = pd.read_csv(INPUT_DIAG, encoding="utf-8-sig")

    ensure_columns(df_diag, ["columna", "uso_sugerido"], "diagnóstico")

    candidate_cols = get_columns_from_diagnostic(df_diag, "candidata_modelado")
    profiling_cols = get_columns_from_diagnostic(df_diag, "perfilado")

    selected_cols = ID_COLS + candidate_cols + profiling_cols
    selected_cols = list(dict.fromkeys(selected_cols))

    print(f"\nColumnas ID: {len(ID_COLS):,}")
    print(f"Columnas candidatas: {len(candidate_cols):,}")
    print(f"Columnas perfilado/contraste: {len(profiling_cols):,}")

    print("\nLeyendo encabezado dataset base:")
    print(f"- {INPUT_BASE}")

    header = pd.read_csv(INPUT_BASE, encoding="utf-8-sig", nrows=0)
    ensure_columns(header, selected_cols, "dataset base")

    sample_usecols = list(dict.fromkeys(ID_COLS + ["mes"] + candidate_cols))
    sample_usecols = [c for c in sample_usecols if c in header.columns]

    sample_df = build_sample(INPUT_BASE, sample_usecols)

    imputation, imputation_report = build_imputation_maps(sample_df, candidate_cols)

    save_json(imputation, OUT_IMPUTATION_VALUES)
    imputation_report.to_csv(OUT_IMPUTATION_REPORT, index=False, encoding="utf-8-sig")

    print("\nAjustando StandardScaler por chunks...")

    scaler = StandardScaler()

    total_rows_fit = 0
    nulls_before_total = 0

    for i, chunk in enumerate(
        pd.read_csv(
            INPUT_BASE,
            encoding="utf-8-sig",
            usecols=selected_cols,
            chunksize=CHUNKSIZE,
            low_memory=False,
        ),
        start=1,
    ):
        nulls_before_total += int(chunk[candidate_cols].isna().sum().sum())

        chunk_imp = impute_chunk(chunk, candidate_cols, imputation)

        X = chunk_imp[candidate_cols].to_numpy(dtype=np.float64)

        scaler.partial_fit(X)

        total_rows_fit += len(chunk_imp)

        print(f"- scaler chunk {i:,}: filas acumuladas {total_rows_fit:,}")

    print("\nGenerando archivos escalados por chunks...")

    remove_output_if_exists(OUT_IDS)
    remove_output_if_exists(OUT_SCALED)

    total_rows_transform = 0

    for i, chunk in enumerate(
        pd.read_csv(
            INPUT_BASE,
            encoding="utf-8-sig",
            usecols=selected_cols,
            chunksize=CHUNKSIZE,
            low_memory=False,
        ),
        start=1,
    ):
        chunk_imp = impute_chunk(chunk, candidate_cols, imputation)

        ids_out = chunk_imp[ID_COLS + profiling_cols].copy()

        X = chunk_imp[candidate_cols].to_numpy(dtype=np.float64)
        X_scaled = scaler.transform(X)

        scaled_out = pd.DataFrame(
            X_scaled,
            columns=candidate_cols,
            index=chunk_imp.index,
        )

        ids_out.to_csv(
            OUT_IDS,
            index=False,
            encoding="utf-8-sig",
            mode="a",
            header=not OUT_IDS.exists(),
        )

        scaled_out.to_csv(
            OUT_SCALED,
            index=False,
            encoding="utf-8-sig",
            mode="a",
            header=not OUT_SCALED.exists(),
            float_format="%.6f",
        )

        total_rows_transform += len(chunk_imp)

        print(f"- transform chunk {i:,}: filas acumuladas {total_rows_transform:,}")

    features_report = pd.DataFrame({
        "feature": candidate_cols,
        "mean_scaler": scaler.mean_,
        "var_scaler": scaler.var_,
        "scale_scaler": scaler.scale_,
        "imputation_strategy": [
            imputation["strategies"][col] for col in candidate_cols
        ],
        "global_imputation_value": [
            imputation["global_values"][col] for col in candidate_cols
        ],
    })

    features_report.to_csv(OUT_FEATURES_REPORT, index=False, encoding="utf-8-sig")

    joblib.dump(scaler, OUT_SCALER)

    print(f"\nNulos antes de imputación en candidatas: {nulls_before_total:,}")
    print("Nulos después de imputación: 0")

    print("\nArchivos generados:")
    print(f"- {OUT_IDS}")
    print(f"- {OUT_SCALED}")
    print(f"- {OUT_IMPUTATION_REPORT}")
    print(f"- {OUT_FEATURES_REPORT}")
    print(f"- {OUT_SCALER}")
    print(f"- {OUT_IMPUTATION_VALUES}")

    print(f"\nFilas matriz escalada: {total_rows_transform:,}")
    print(f"Columnas matriz escalada: {len(candidate_cols):,}")

    print("\nProceso terminado.")


if __name__ == "__main__":
    main()