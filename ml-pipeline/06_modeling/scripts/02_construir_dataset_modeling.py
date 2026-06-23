# -*- coding: utf-8 -*-
"""
Modeling 02 | Construcción del dataset base de modelado

Este script construye el dataset base para Modeling a partir de la matriz
final de Feature Engineering y del diagnóstico generado en Modeling 01.

Hace lo siguiente:
- Lee la matriz FE del flujo seleccionado.
- Lee el diagnóstico de columnas de Modeling 01.
- Selecciona columnas ID.
- Selecciona columnas candidatas para modelado.
- Conserva columnas de perfilado/contraste, como CONAFOR.
- Valida llave, columnas faltantes, duplicados y fechas.
- Convierte columnas numéricas seleccionadas a tipo numérico.
- Genera el dataset base de modelado en 06_modeling/datasets.
"""

from pathlib import Path
import pandas as pd


# ============================================================
# CONFIGURACIÓN
# ============================================================

BASE_DIR = Path(r"C:\Users\Hp\OneDrive\Documentos\PT_Analisis")

# FLUJO = "entidad_dia"
FLUJO = "municipio_dia"

INPUTS_FE = {
    "entidad_dia": BASE_DIR / "05_feature_engineering" / "datasets" / "fe_entidad_dia_matriz.csv",
    "municipio_dia": BASE_DIR / "05_feature_engineering" / "datasets" / "fe_municipio_dia_matriz.csv",
}

INPUTS_DIAG = {
    "entidad_dia": BASE_DIR / "06_modeling" / "reports" / "modeling_01_diagnostico_entidad_dia.csv",
    "municipio_dia": BASE_DIR / "06_modeling" / "reports" / "modeling_01_diagnostico_municipio_dia.csv",
}

OUT_DATASETS = BASE_DIR / "06_modeling" / "datasets" / FLUJO
OUT_DATASETS.mkdir(parents=True, exist_ok=True)

OUT_BASE = OUT_DATASETS / f"modeling_{FLUJO}_base.csv"


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

KEY_COLS_BY_FLOW = {
    "entidad_dia": [
        "cve_ent",
        "fecha",
    ],
    "municipio_dia": [
        "cvegeo",
        "fecha",
    ],
}

CHUNKSIZE = 300_000


# ============================================================
# FUNCIONES AUXILIARES
# ============================================================

def normalize_cve_ent(series: pd.Series) -> pd.Series:
    s = series.astype(str).str.strip()
    s_num = pd.to_numeric(s, errors="coerce")

    out = s.copy()
    mask = s_num.notna()
    out.loc[mask] = s_num.loc[mask].astype(int).astype(str)

    return out.str.zfill(2)


def normalize_cve_mun(series: pd.Series) -> pd.Series:
    s = series.astype(str).str.strip()
    s_num = pd.to_numeric(s, errors="coerce")

    out = s.copy()
    mask = s_num.notna()
    out.loc[mask] = s_num.loc[mask].astype(int).astype(str)

    return out.str.zfill(3)


def normalize_cvegeo(series: pd.Series) -> pd.Series:
    s = series.astype(str).str.strip()
    s_num = pd.to_numeric(s, errors="coerce")

    out = s.copy()
    mask = s_num.notna()
    out.loc[mask] = s_num.loc[mask].astype(int).astype(str)

    return out.str.zfill(5)


def ensure_columns(df: pd.DataFrame, required_cols: list[str], context: str) -> None:
    missing = [c for c in required_cols if c not in df.columns]
    if missing:
        raise ValueError(f"Faltan columnas en {context}: {missing}")


def validate_key(df: pd.DataFrame, key_cols: list[str]) -> None:
    null_key_rows = df[key_cols].isna().any(axis=1).sum()

    if null_key_rows > 0:
        raise ValueError(
            f"La llave {key_cols} contiene {null_key_rows:,} filas con valores nulos."
        )

    duplicated_rows = df.duplicated(subset=key_cols).sum()

    if duplicated_rows > 0:
        raise ValueError(
            f"La llave {key_cols} contiene {duplicated_rows:,} filas duplicadas."
        )


def get_columns_from_diagnostic(df_diag: pd.DataFrame, uso: str) -> list[str]:
    cols = (
        df_diag.loc[df_diag["uso_sugerido"] == uso, "columna"]
        .dropna()
        .astype(str)
        .tolist()
    )
    return cols


def to_numeric_selected(df: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
    for col in cols:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


# ============================================================
# PIPELINE PRINCIPAL
# ============================================================

def main():
    print("\nModeling 02 | Construcción del dataset base")
    print(f"Flujo: {FLUJO}")

    input_fe = INPUTS_FE[FLUJO]
    input_diag = INPUTS_DIAG[FLUJO]

    if not input_fe.exists():
        raise FileNotFoundError(f"No existe matriz FE: {input_fe}")

    if not input_diag.exists():
        raise FileNotFoundError(f"No existe diagnóstico Modeling 01: {input_diag}")

    print(f"\nLeyendo diagnóstico:")
    print(f"- {input_diag}")

    df_diag = pd.read_csv(input_diag, encoding="utf-8-sig")

    required_diag_cols = ["columna", "uso_sugerido"]
    ensure_columns(df_diag, required_diag_cols, "diagnóstico Modeling 01")

    id_cols = ID_COLS_BY_FLOW[FLUJO]
    key_cols = KEY_COLS_BY_FLOW[FLUJO]

    candidate_cols = get_columns_from_diagnostic(df_diag, "candidata_modelado")
    profiling_cols = get_columns_from_diagnostic(df_diag, "perfilado")

    selected_cols = id_cols + candidate_cols + profiling_cols
    selected_cols = list(dict.fromkeys(selected_cols))

    print(f"\nColumnas ID: {len(id_cols):,}")
    print(f"Columnas candidatas modelado: {len(candidate_cols):,}")
    print(f"Columnas perfilado/contraste: {len(profiling_cols):,}")
    print(f"Columnas totales seleccionadas: {len(selected_cols):,}")

    print(f"\nLeyendo encabezado FE:")
    print(f"- {input_fe}")

    df_header = pd.read_csv(input_fe, encoding="utf-8-sig", nrows=0)
    ensure_columns(df_header, selected_cols, "matriz FE")

    if OUT_BASE.exists():
        OUT_BASE.unlink()

    total_rows = 0
    total_nulls_candidate = 0
    total_nulls_profile = 0
    duplicated_total = 0
    seen_keys = set()

    print("\nConstruyendo dataset base por chunks...")

    for i, chunk in enumerate(
        pd.read_csv(
            input_fe,
            encoding="utf-8-sig",
            usecols=selected_cols,
            chunksize=CHUNKSIZE,
            low_memory=False,
        ),
        start=1,
    ):
        print(f"Procesando chunk {i:,} | filas: {len(chunk):,}")

        model_base = chunk[selected_cols].copy()

        # Normalización de IDs
        if "cve_ent" in model_base.columns:
            model_base["cve_ent"] = normalize_cve_ent(model_base["cve_ent"])

        if "cve_mun" in model_base.columns:
            model_base["cve_mun"] = normalize_cve_mun(model_base["cve_mun"])

        if "cvegeo" in model_base.columns:
            model_base["cvegeo"] = normalize_cvegeo(model_base["cvegeo"])

        if "nom_ent" in model_base.columns:
            model_base["nom_ent"] = model_base["nom_ent"].astype(str).str.strip()

        if "nom_mun" in model_base.columns:
            model_base["nom_mun"] = model_base["nom_mun"].astype(str).str.strip()

        model_base["fecha"] = pd.to_datetime(
            model_base["fecha"],
            errors="coerce"
        ).dt.strftime("%Y-%m-%d")

        invalid_dates = model_base["fecha"].isna().sum()
        if invalid_dates > 0:
            raise ValueError(f"Chunk {i}: {invalid_dates:,} fechas inválidas.")

        null_key_rows = model_base[key_cols].isna().any(axis=1).sum()
        if null_key_rows > 0:
            raise ValueError(f"Chunk {i}: {null_key_rows:,} filas con llave nula.")

        # Validación de duplicados dentro del chunk
        duplicated_chunk = model_base.duplicated(subset=key_cols).sum()
        if duplicated_chunk > 0:
            raise ValueError(f"Chunk {i}: {duplicated_chunk:,} llaves duplicadas dentro del chunk.")

        # Validación básica de duplicados entre chunks
        key_tuples = list(map(tuple, model_base[key_cols].astype(str).to_numpy()))

        duplicated_cross = sum(1 for k in key_tuples if k in seen_keys)
        if duplicated_cross > 0:
            raise ValueError(f"Chunk {i}: {duplicated_cross:,} llaves duplicadas contra chunks previos.")

        seen_keys.update(key_tuples)

        # Conversión numérica
        numeric_cols = candidate_cols + profiling_cols
        model_base = to_numeric_selected(model_base, numeric_cols)

        total_nulls_candidate += int(model_base[candidate_cols].isna().sum().sum())
        total_nulls_profile += int(model_base[profiling_cols].isna().sum().sum()) if profiling_cols else 0
        total_rows += len(model_base)
        duplicated_total += int(duplicated_chunk)

        model_base.to_csv(
            OUT_BASE,
            index=False,
            encoding="utf-8-sig",
            mode="a",
            header=not OUT_BASE.exists(),
        )

    print(f"\nNulos en columnas candidatas: {total_nulls_candidate:,}")
    print(f"Nulos en columnas de perfilado: {total_nulls_profile:,}")

    print(f"\nDataset base generado:")
    print(f"- {OUT_BASE}")

    print(f"\nFilas finales: {total_rows:,}")
    print(f"Columnas finales: {len(selected_cols):,}")
    print(f"Duplicados detectados: {duplicated_total:,}")

    print("\nProceso terminado.")


if __name__ == "__main__":
    main()