# -*- coding: utf-8 -*-
"""
Modeling 01 | Diagnóstico de matriz de modelado

Este script revisa la matriz final de Feature Engineering para iniciar
la fase de Modeling bajo CRISP-DM.

Hace lo siguiente:
- Lee la matriz entidad-día o municipio-día.
- Clasifica columnas por familia de datos.
- Identifica columnas ID, temporales, FIRMS, SMN, CONAFOR, INEGI, INFyS.
- Detecta nulos, constantes, tipos de dato y posibles columnas de leakage.
- Sugiere si cada columna puede usarse como candidata de modelado,
  perfilado posterior o debe excluirse.
- Genera un archivo CSV de diagnóstico en 06_modeling/reports.
"""

from pathlib import Path
import pandas as pd
import numpy as np


# ============================================================
# CONFIGURACIÓN
# ============================================================

BASE_DIR = Path(r"C:\Users\Hp\OneDrive\Documentos\PT_Analisis")

FLUJO = "municipio_dia"

INPUTS = {
    "entidad_dia": BASE_DIR / "05_feature_engineering" / "datasets" / "fe_entidad_dia_matriz.csv",
    "municipio_dia": BASE_DIR / "05_feature_engineering" / "datasets" / "fe_municipio_dia_matriz.csv",
}

OUT_REPORTS = BASE_DIR / "06_modeling" / "reports"
OUT_REPORTS.mkdir(parents=True, exist_ok=True)

OUT_DIAGNOSTICO = OUT_REPORTS / f"modeling_01_diagnostico_{FLUJO}.csv"


# ============================================================
# COLUMNAS BASE
# ============================================================

ID_COLS_ENTIDAD = {
    "cve_ent",
    "nom_ent",
    "fecha",
}

ID_COLS_MUNICIPIO = {
    "cvegeo",
    "cve_ent",
    "cve_mun",
    "nom_ent",
    "nom_mun",
    "fecha",
}

TEMPORAL_COLS = {
    "anio",
    "mes",
    "dia",
    "dia_del_anio",
    "semana_iso",
    "trimestre",
    "es_temporada_incendios",
}

FLAGS_DISPONIBILIDAD = {
    "has_conafor",
    "has_firms",
    "has_smn",
    "conafor_disponible",
}

CONAFOR_LEAKAGE_COLS = {
    "has_conafor",
    "conafor_event_count",
    "conafor_event_count_log1p",
    "conafor_disponible",
    "n_municipios_con_conafor",
}

COLUMNAS_EXCLUIR_POR_NOMBRE = {
    # IDs y textos
    "nom_ent",
    "nom_mun",
    "fecha",

    # Flags de disponibilidad: útiles para diagnóstico, no como variables principales
    "has_conafor",
    "has_firms",
    "has_smn",
    "conafor_disponible",

    # Conteos de cobertura municipal: útiles para control/calidad, no necesariamente predictores
    "n_municipios_base",
    "n_municipios_con_conafor",
    "n_municipios_con_firms",
    "n_municipios_con_smn",
    "n_municipios_contexto",

    # Leakage CONAFOR para modelo principal
    "conafor_event_count",
    "conafor_event_count_log1p",
}

PATRONES_EXCLUIR = [
    "_valid_count",
    "_n_registros",
    "filaencabezadodetectada",

    # Coordenadas o derivados espaciales internos de INFyS
    "coordx",
    "coordy",
    "_x_",
    "_y_",
    "_x_mean",
    "_y_mean",
    "xc3",
    "yc3",

    # Códigos, consecutivos, identificadores técnicos o campos operativos
    "conglomerado",
    "consecutivo",
    "norama",
    "cvearbolado",
    "cveestado",
    "cveestadoc3",
    "cveeco",
    "cvefor",
    "cve_",
    "cvesitio",

    # Sitios/parcelas auxiliares
    "sitio_mean",
    "sitio_valid_count",
    "sitioc3",
    "cvesitioc3",
    "numsitio",
    "consitio",

    # Campos técnicos de levantamiento
    "datum",
    "distancia",
    "errorprecision",
    "consenial",
    "muestreado",
]


# ============================================================
# FUNCIONES AUXILIARES
# ============================================================

def clasificar_familia(col: str) -> str:
    c = col.lower()

    if col in ID_COLS_ENTIDAD or col in ID_COLS_MUNICIPIO:
        return "id"
    if col in TEMPORAL_COLS:
        return "temporal"
    if c.startswith("firms_"):
        return "firms"
    if c.startswith("smn_"):
        return "smn"
    if c.startswith("conafor_") or c == "has_conafor":
        return "conafor"
    if c.startswith("inegi_") or c.startswith("entidad_area") or col == "municipio_area_km2":
        return "inegi"
    if c.startswith("infys_"):
        return "infys"
    if c.startswith("has_"):
        return "flag_disponibilidad"
    if c.startswith("n_municipios"):
        return "cobertura_agregacion"

    return "otra"


def contiene_patron_exclusion(col: str) -> bool:
    c = col.lower()
    return any(p.lower() in c for p in PATRONES_EXCLUIR)


def clasificar_uso_modeling(col: str, dtype: str, n_unique: int, null_pct: float) -> tuple[str, str]:
    familia = clasificar_familia(col)
    c = col.lower()

    if col == "municipio_area_km2":
        return "candidata_modelado", "área municipal como variable contextual geográfica"
    
    if col in {"has_firms", "has_smn"}:
        return "perfilado", "flag de disponibilidad de fuente reservado para perfilado"

    if familia == "id":
        return "excluir", "columna identificadora o textual"

    if col in CONAFOR_LEAKAGE_COLS or c.startswith("conafor_"):
        return "perfilado", "CONAFOR se reserva para contraste/perfilado; no predictor principal"

    if col in COLUMNAS_EXCLUIR_POR_NOMBRE:
        return "excluir", "columna excluida por decisión metodológica"

    if contiene_patron_exclusion(col):
        return "excluir", "columna auxiliar, trazabilidad, conteo de válidos o código técnico"

    if n_unique <= 1:
        return "excluir", "columna constante"

    if null_pct >= 0.80:
        return "excluir", "columna con 80% o más de nulos"

    if dtype == "object":
        return "excluir", "columna categórica/textual no codificada"

    if familia in {"firms", "smn", "inegi", "infys", "temporal"}:
        return "candidata_modelado", "variable numérica candidata para modelado"

    
    if familia in {"flag_disponibilidad", "cobertura_agregacion"}:
        return "diagnostico", "variable útil para control de cobertura, no modelo inicial"

    return "revisar", "requiere revisión manual"


def tipo_general_dtype(dtype) -> str:
    if pd.api.types.is_numeric_dtype(dtype):
        return "numeric"
    if pd.api.types.is_datetime64_any_dtype(dtype):
        return "datetime"
    return "object"


def resumen_valores_numericos(s: pd.Series) -> dict:
    s_num = pd.to_numeric(s, errors="coerce")

    if s_num.notna().sum() == 0:
        return {
            "min": np.nan,
            "p25": np.nan,
            "median": np.nan,
            "mean": np.nan,
            "p75": np.nan,
            "max": np.nan,
            "std": np.nan,
        }

    return {
        "min": s_num.min(),
        "p25": s_num.quantile(0.25),
        "median": s_num.median(),
        "mean": s_num.mean(),
        "p75": s_num.quantile(0.75),
        "max": s_num.max(),
        "std": s_num.std(),
    }


# ============================================================
# PIPELINE PRINCIPAL
# ============================================================

def main():
    print("\nModeling 01 | Diagnóstico de matriz de modelado")
    print(f"Flujo: {FLUJO}")

    input_path = INPUTS[FLUJO]

    if not input_path.exists():
        raise FileNotFoundError(f"No existe el archivo de entrada: {input_path}")

    print(f"Leyendo matriz:\n- {input_path}")

    print("\nLeyendo encabezado de matriz...")
    df_header = pd.read_csv(input_path, encoding="utf-8-sig", nrows=0)

    print("Leyendo muestra para inferir tipos...")
    df_sample = pd.read_csv(input_path, encoding="utf-8-sig", nrows=50_000, low_memory=False)

    print("Contando filas sin cargar toda la matriz...")
    n_rows = 0
    for chunk in pd.read_csv(
        input_path,
        encoding="utf-8-sig",
        usecols=[0],
        chunksize=500_000,
        low_memory=False,
    ):
        n_rows += len(chunk)

    df = df_sample.copy()

    print(f"\nFilas: {n_rows:,}")
    print(f"Columnas: {len(df_header.columns):,}")

    # Validación básica de IDs esperados
    expected_ids = ID_COLS_ENTIDAD if FLUJO == "entidad_dia" else ID_COLS_MUNICIPIO
    missing_ids = sorted(expected_ids - set(df_header.columns))

    if missing_ids:
        raise ValueError(f"Faltan columnas ID esperadas para {FLUJO}: {missing_ids}")

    rows = []

    total_rows = len(df)

    for col in df_header.columns:
        s = df[col]
        dtype_raw = str(s.dtype)
        dtype_general = tipo_general_dtype(s.dtype)

        n_null = int(s.isna().sum())
        null_pct = n_null / total_rows if total_rows > 0 else np.nan

        n_unique = int(s.nunique(dropna=True))
        unique_pct = n_unique / total_rows if total_rows > 0 else np.nan

        familia = clasificar_familia(col)
        uso_sugerido, motivo = clasificar_uso_modeling(
            col=col,
            dtype=dtype_general,
            n_unique=n_unique,
            null_pct=null_pct,
        )

        numeric_stats = resumen_valores_numericos(s) if dtype_general == "numeric" else {
            "min": np.nan,
            "p25": np.nan,
            "median": np.nan,
            "mean": np.nan,
            "p75": np.nan,
            "max": np.nan,
            "std": np.nan,
        }

        rows.append({
            "columna": col,
            "familia": familia,
            "dtype": dtype_raw,
            "dtype_general": dtype_general,
            "n_null": n_null,
            "null_pct": round(null_pct, 6),
            "n_unique": n_unique,
            "unique_pct": round(unique_pct, 6),
            "es_constante": int(n_unique <= 1),
            "uso_sugerido": uso_sugerido,
            "motivo": motivo,
            **numeric_stats,
        })

    diagnostico = pd.DataFrame(rows)

    orden_uso = {
        "candidata_modelado": 1,
        "perfilado": 2,
        "diagnostico": 3,
        "revisar": 4,
        "excluir": 5,
    }

    diagnostico["orden_uso"] = diagnostico["uso_sugerido"].map(orden_uso).fillna(99)

    diagnostico = diagnostico.sort_values(
        by=["orden_uso", "familia", "columna"],
        ascending=[True, True, True],
    ).drop(columns=["orden_uso"])

    diagnostico.to_csv(OUT_DIAGNOSTICO, index=False, encoding="utf-8-sig")

    # Resumen en consola
    print("\nResumen por familia:")
    print(
        diagnostico.groupby("familia")
        .size()
        .reset_index(name="n_columnas")
        .sort_values("n_columnas", ascending=False)
        .to_string(index=False)
    )

    print("\nResumen por uso sugerido:")
    print(
        diagnostico.groupby("uso_sugerido")
        .size()
        .reset_index(name="n_columnas")
        .sort_values("n_columnas", ascending=False)
        .to_string(index=False)
    )

    candidatas = diagnostico[diagnostico["uso_sugerido"] == "candidata_modelado"]
    perfilado = diagnostico[diagnostico["uso_sugerido"] == "perfilado"]
    revisar = diagnostico[diagnostico["uso_sugerido"] == "revisar"]

    print(f"\nColumnas candidatas para modelado inicial: {len(candidatas):,}")
    print(f"Columnas reservadas para perfilado/contraste: {len(perfilado):,}")
    print(f"Columnas por revisar manualmente: {len(revisar):,}")

    print(f"\nArchivo generado:")
    print(f"- {OUT_DIAGNOSTICO}")

    print("\nProceso terminado.")


if __name__ == "__main__":
    main()