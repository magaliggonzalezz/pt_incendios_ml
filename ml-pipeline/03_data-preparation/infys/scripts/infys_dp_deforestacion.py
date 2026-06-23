# -*- coding: utf-8 -*-
"""
INFyS | Data Preparation - Deforestación nacional

Fase CRISP-DM:
- Data Preparation

Objetivo:
Preparar estructuralmente el producto tabular de deforestación nacional INFyS/CONAFOR,
normalizando columnas, tipos de datos, categorías, años y validaciones internas.

Entradas esperadas:
- 01_raw-data/infys/DeforestacionNacional_2024.xlsx

Salidas:
- 03_data-preparation/infys/datasets/infys_deforestacion_superficie_nacional_limpio.csv
- 03_data-preparation/infys/datasets/infys_deforestacion_incertidumbre_nacional_limpio.csv
- 03_data-preparation/infys/reports/infys_dp_deforestacion_validacion.csv
"""

from __future__ import annotations

import re
import unicodedata
from pathlib import Path
from typing import Dict, Optional, Tuple

import pandas as pd


# =========================================================
# 1) CONFIGURACIÓN
# =========================================================

BASE_DIR = Path(r"C:\Users\Hp\OneDrive\Documentos\PT_Analisis")

RAW_DIR = BASE_DIR / "01_raw-data" / "infys"
DATASETS_DIR = BASE_DIR / "03_data-preparation" / "infys" / "datasets"
REPORTS_DIR = BASE_DIR / "03_data-preparation" / "infys" / "reports"

DATASETS_DIR.mkdir(parents=True, exist_ok=True)
REPORTS_DIR.mkdir(parents=True, exist_ok=True)

ARCHIVO_DEFORESTACION = "DeforestacionNacional_2024.xlsx"

HOJA_SUPERFICIE = "SuperficieDeforestadaNacional"
HOJA_INCERTIDUMBRE = "IncertidumbreNacional"

OUT_SUPERFICIE = DATASETS_DIR / "infys_deforestacion_superficie_nacional_limpio.csv"
OUT_INCERTIDUMBRE = DATASETS_DIR / "infys_deforestacion_incertidumbre_nacional_limpio.csv"
OUT_VALIDACION = REPORTS_DIR / "infys_dp_deforestacion_validacion.csv"

ANIO_MIN = 2001
ANIO_MAX = 2024

TOKENS_NULOS = {
    "",
    " ",
    "NA",
    "N/A",
    "NAN",
    "NULL",
    "NULO",
    "S/D",
    "SD",
    "SIN DATO",
    "SIN DATOS",
    "NO APLICA",
    "N.D.",
    "ND",
    "-",
    "--",
}


# =========================================================
# 2) UTILIDADES
# =========================================================

def quitar_acentos(valor: object) -> str:
    texto = "" if pd.isna(valor) else str(valor)
    texto = unicodedata.normalize("NFKD", texto)
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    return texto


def normalizar_texto(valor: object) -> object:
    if pd.isna(valor):
        return pd.NA

    texto = quitar_acentos(valor)
    texto = texto.strip().upper()
    texto = re.sub(r"\s+", " ", texto)

    if texto in TOKENS_NULOS:
        return pd.NA

    return texto


def normalizar_columna(nombre: object) -> str:
    texto = quitar_acentos(nombre)
    texto = texto.strip().lower()
    texto = re.sub(r"[^a-z0-9]+", "_", texto)
    texto = re.sub(r"_+", "_", texto)
    return texto.strip("_")


def buscar_archivo(nombre_archivo: str) -> Optional[Path]:
    coincidencias = sorted(RAW_DIR.rglob(nombre_archivo))

    if not coincidencias:
        return None

    if len(coincidencias) > 1:
        print(f"Advertencia: múltiples coincidencias para {nombre_archivo}. Se usará: {coincidencias[0]}")

    return coincidencias[0]


def convertir_numero(serie: pd.Series) -> pd.Series:
    s = serie.astype("string")
    s = s.str.replace(",", "", regex=False)
    s = s.str.replace(" ", "", regex=False)
    s = s.str.strip()
    s = s.mask(s.str.upper().isin(TOKENS_NULOS), pd.NA)
    return pd.to_numeric(s, errors="coerce")


def convertir_anio(serie: pd.Series) -> pd.Series:
    n = convertir_numero(serie)
    return n.round(0).astype("Int64")


def leer_metadato_archivo(ruta: Path, hoja: str) -> str:
    try:
        df_meta = pd.read_excel(ruta, sheet_name=hoja, header=None, nrows=1)
        valor = df_meta.iloc[0, 0]
        return "" if pd.isna(valor) else str(valor).strip()
    except Exception:
        return ""


def leer_hoja_con_encabezado_real(ruta: Path, hoja: str) -> Tuple[pd.DataFrame, pd.DataFrame, str]:
    metadato = leer_metadato_archivo(ruta, hoja)

    df_original = pd.read_excel(ruta, sheet_name=hoja, header=1)
    df = df_original.copy()
    df.columns = [normalizar_columna(c) for c in df.columns]

    df = df.dropna(axis=0, how="all")
    df = df.dropna(axis=1, how="all")
    df = df.reset_index(drop=True)

    return df_original, df, metadato


def guardar_dataset(df: Optional[pd.DataFrame], ruta_salida: Path, nombre_dataset: str) -> None:
    if df is None:
        print(f"No se generó {nombre_dataset}.")
        return

    df.to_csv(ruta_salida, index=False, encoding="utf-8-sig")
    print(f"Dataset generado: {ruta_salida}")


def registro_error(nombre_dataset: str, archivo_origen: str, hoja_origen: str, mensaje: str) -> Dict[str, object]:
    return {
        "dataset": nombre_dataset,
        "archivo_origen": archivo_origen,
        "hoja_origen": hoja_origen,
        "filas_leidas": 0,
        "columnas_leidas": 0,
        "filas_finales": 0,
        "columnas_finales": 0,
        "filas_eliminadas": 0,
        "anio_min": None,
        "anio_max": None,
        "anios_distintos": None,
        "anios_fuera_periodo": None,
        "nulos_clave": None,
        "valores_numericos_nulos": None,
        "valores_numericos_negativos": None,
        "duplicados_exactos_finales": None,
        "duplicados_por_clave": None,
        "superficie_total_ha": None,
        "estado_validacion": "error",
        "observaciones": mensaje,
    }


# =========================================================
# 3) PREPARACIÓN - SUPERFICIE DEFORESTADA
# =========================================================

def preparar_superficie_deforestada() -> Tuple[Optional[pd.DataFrame], Dict[str, object]]:
    nombre_dataset = "infys_deforestacion_superficie_nacional_limpio"

    ruta = buscar_archivo(ARCHIVO_DEFORESTACION)

    if ruta is None:
        return None, registro_error(
            nombre_dataset,
            ARCHIVO_DEFORESTACION,
            HOJA_SUPERFICIE,
            "archivo_no_encontrado",
        )

    print(f"Procesando: {ruta.name} | hoja: {HOJA_SUPERFICIE}")

    df_original, df_raw, metadato = leer_hoja_con_encabezado_real(ruta, HOJA_SUPERFICIE)

    columnas_esperadas = {
        "ano": "anio",
        "anio": "anio",
        "año": "anio",
        "ecoregion": "ecorregion",
        "superficie_deforestada_ha": "superficie_deforestada_ha",
        "superficie_deforestada": "superficie_deforestada_ha",
        "transicion": "transicion",
    }

    df = df_raw.rename(columns={c: columnas_esperadas.get(c, c) for c in df_raw.columns})

    columnas_requeridas = [
        "anio",
        "ecorregion",
        "superficie_deforestada_ha",
        "transicion",
    ]

    faltantes = [c for c in columnas_requeridas if c not in df.columns]

    if faltantes:
        raise ValueError(
            f"Faltan columnas requeridas en {HOJA_SUPERFICIE}: {faltantes}. "
            f"Columnas disponibles: {list(df.columns)}"
        )

    out = pd.DataFrame()
    out["anio"] = convertir_anio(df["anio"])
    out["ecorregion"] = df["ecorregion"].map(normalizar_texto)
    out["transicion"] = df["transicion"].map(normalizar_texto)
    out["superficie_deforestada_ha"] = convertir_numero(df["superficie_deforestada_ha"])

    out["archivo_origen"] = ARCHIVO_DEFORESTACION
    out["hoja_origen"] = HOJA_SUPERFICIE
    out["metadato_origen"] = metadato

    out = out.dropna(subset=["anio", "ecorregion", "transicion", "superficie_deforestada_ha"]).copy()
    out = out[out["anio"].between(ANIO_MIN, ANIO_MAX)].copy()
    out = out[out["superficie_deforestada_ha"] >= 0].copy()
    out = out.drop_duplicates().copy()

    out = out[
        [
            "anio",
            "ecorregion",
            "transicion",
            "superficie_deforestada_ha",
            "archivo_origen",
            "hoja_origen",
            "metadato_origen",
        ]
    ].sort_values(
        ["anio", "ecorregion", "transicion"]
    ).reset_index(drop=True)

    validacion = crear_validacion_superficie(
        nombre_dataset=nombre_dataset,
        filas_leidas=len(df_original),
        columnas_leidas=len(df_original.columns),
        df_limpio=out,
    )

    return out, validacion


def crear_validacion_superficie(
    nombre_dataset: str,
    filas_leidas: int,
    columnas_leidas: int,
    df_limpio: pd.DataFrame,
) -> Dict[str, object]:

    columnas_clave = ["anio", "ecorregion", "transicion"]

    duplicados_por_clave = int(df_limpio.duplicated(subset=columnas_clave).sum())

    anios_fuera_periodo = int(
        (~df_limpio["anio"].between(ANIO_MIN, ANIO_MAX)).sum()
    )

    valores_numericos_nulos = int(df_limpio["superficie_deforestada_ha"].isna().sum())
    valores_numericos_negativos = int((df_limpio["superficie_deforestada_ha"] < 0).sum())

    nulos_clave = int(
        df_limpio[["anio", "ecorregion", "transicion"]].isna().any(axis=1).sum()
    )

    registro = {
        "dataset": nombre_dataset,
        "archivo_origen": ARCHIVO_DEFORESTACION,
        "hoja_origen": HOJA_SUPERFICIE,
        "filas_leidas": filas_leidas,
        "columnas_leidas": columnas_leidas,
        "filas_finales": len(df_limpio),
        "columnas_finales": len(df_limpio.columns),
        "filas_eliminadas": filas_leidas - len(df_limpio),
        "anio_min": int(df_limpio["anio"].min()) if len(df_limpio) > 0 else None,
        "anio_max": int(df_limpio["anio"].max()) if len(df_limpio) > 0 else None,
        "anios_distintos": int(df_limpio["anio"].nunique(dropna=True)),
        "anios_fuera_periodo": anios_fuera_periodo,
        "nulos_clave": nulos_clave,
        "valores_numericos_nulos": valores_numericos_nulos,
        "valores_numericos_negativos": valores_numericos_negativos,
        "duplicados_exactos_finales": int(df_limpio.duplicated().sum()),
        "duplicados_por_clave": duplicados_por_clave,
        "superficie_total_ha": float(df_limpio["superficie_deforestada_ha"].sum()),
        "estado_validacion": "ok",
        "observaciones": "",
    }

    observaciones = []

    if len(df_limpio) == 0:
        observaciones.append("dataset_sin_filas_finales")

    if registro["anio_min"] != ANIO_MIN or registro["anio_max"] != ANIO_MAX:
        observaciones.append("periodo_final_distinto_al_esperado")

    if registro["anios_distintos"] != (ANIO_MAX - ANIO_MIN + 1):
        observaciones.append("numero_de_anios_distinto_al_esperado")

    if nulos_clave > 0:
        observaciones.append("existen_nulos_en_clave")

    if valores_numericos_nulos > 0:
        observaciones.append("existen_valores_numericos_nulos")

    if valores_numericos_negativos > 0:
        observaciones.append("existen_valores_numericos_negativos")

    if registro["duplicados_exactos_finales"] > 0:
        observaciones.append("existen_duplicados_exactos_finales")

    if duplicados_por_clave > 0:
        observaciones.append("existen_duplicados_por_clave")

    if observaciones:
        registro["estado_validacion"] = "revisar"
        registro["observaciones"] = "; ".join(observaciones)

    return registro


# =========================================================
# 4) PREPARACIÓN - INCERTIDUMBRE
# =========================================================

def preparar_incertidumbre() -> Tuple[Optional[pd.DataFrame], Dict[str, object]]:
    nombre_dataset = "infys_deforestacion_incertidumbre_nacional_limpio"

    ruta = buscar_archivo(ARCHIVO_DEFORESTACION)

    if ruta is None:
        return None, registro_error(
            nombre_dataset,
            ARCHIVO_DEFORESTACION,
            HOJA_INCERTIDUMBRE,
            "archivo_no_encontrado",
        )

    print(f"Procesando: {ruta.name} | hoja: {HOJA_INCERTIDUMBRE}")

    df_original, df_raw, metadato = leer_hoja_con_encabezado_real(ruta, HOJA_INCERTIDUMBRE)

    columnas_esperadas = {
        "ano": "anio",
        "anio": "anio",
        "año": "anio",
        "deforestacion": "deforestacion_ha",
        "incertidumbres": "incertidumbre_pct",
        "incertidumbres_pct": "incertidumbre_pct",
        "incertidumbres_%": "incertidumbre_pct",
        "z_alfa_2_sigma": "z_alfa_2_sigma_ha",
        "limite_inferior": "limite_inferior_ha",
        "limite_superior": "limite_superior_ha",
    }

    df = df_raw.rename(columns={c: columnas_esperadas.get(c, c) for c in df_raw.columns})

    columnas_requeridas = [
        "anio",
        "deforestacion_ha",
        "incertidumbre_pct",
        "z_alfa_2_sigma_ha",
        "limite_inferior_ha",
        "limite_superior_ha",
    ]

    faltantes = [c for c in columnas_requeridas if c not in df.columns]

    if faltantes:
        raise ValueError(
            f"Faltan columnas requeridas en {HOJA_INCERTIDUMBRE}: {faltantes}. "
            f"Columnas disponibles: {list(df.columns)}"
        )

    out = pd.DataFrame()
    out["anio"] = convertir_anio(df["anio"])
    out["deforestacion_ha"] = convertir_numero(df["deforestacion_ha"])
    out["incertidumbre_pct"] = convertir_numero(df["incertidumbre_pct"])
    out["z_alfa_2_sigma_ha"] = convertir_numero(df["z_alfa_2_sigma_ha"])
    out["limite_inferior_ha"] = convertir_numero(df["limite_inferior_ha"])
    out["limite_superior_ha"] = convertir_numero(df["limite_superior_ha"])

    out["archivo_origen"] = ARCHIVO_DEFORESTACION
    out["hoja_origen"] = HOJA_INCERTIDUMBRE
    out["metadato_origen"] = metadato

    out = out.dropna(
        subset=[
            "anio",
            "deforestacion_ha",
            "incertidumbre_pct",
            "z_alfa_2_sigma_ha",
            "limite_inferior_ha",
            "limite_superior_ha",
        ]
    ).copy()

    out = out[out["anio"].between(ANIO_MIN, ANIO_MAX)].copy()

    columnas_no_negativas = [
        "deforestacion_ha",
        "incertidumbre_pct",
        "z_alfa_2_sigma_ha",
        "limite_inferior_ha",
        "limite_superior_ha",
    ]

    for col in columnas_no_negativas:
        out = out[out[col] >= 0].copy()

    out = out.drop_duplicates().copy()

    out = out[
        [
            "anio",
            "deforestacion_ha",
            "incertidumbre_pct",
            "z_alfa_2_sigma_ha",
            "limite_inferior_ha",
            "limite_superior_ha",
            "archivo_origen",
            "hoja_origen",
            "metadato_origen",
        ]
    ].sort_values("anio").reset_index(drop=True)

    validacion = crear_validacion_incertidumbre(
        nombre_dataset=nombre_dataset,
        filas_leidas=len(df_original),
        columnas_leidas=len(df_original.columns),
        df_limpio=out,
    )

    return out, validacion


def crear_validacion_incertidumbre(
    nombre_dataset: str,
    filas_leidas: int,
    columnas_leidas: int,
    df_limpio: pd.DataFrame,
) -> Dict[str, object]:

    columnas_numericas = [
        "deforestacion_ha",
        "incertidumbre_pct",
        "z_alfa_2_sigma_ha",
        "limite_inferior_ha",
        "limite_superior_ha",
    ]

    valores_numericos_nulos = int(df_limpio[columnas_numericas].isna().any(axis=1).sum())
    valores_numericos_negativos = int((df_limpio[columnas_numericas] < 0).any(axis=1).sum())

    anios_fuera_periodo = int(
        (~df_limpio["anio"].between(ANIO_MIN, ANIO_MAX)).sum()
    )

    limites_inconsistentes = int(
        (
            (df_limpio["limite_inferior_ha"] > df_limpio["deforestacion_ha"])
            | (df_limpio["deforestacion_ha"] > df_limpio["limite_superior_ha"])
        ).sum()
    )

    registro = {
        "dataset": nombre_dataset,
        "archivo_origen": ARCHIVO_DEFORESTACION,
        "hoja_origen": HOJA_INCERTIDUMBRE,
        "filas_leidas": filas_leidas,
        "columnas_leidas": columnas_leidas,
        "filas_finales": len(df_limpio),
        "columnas_finales": len(df_limpio.columns),
        "filas_eliminadas": filas_leidas - len(df_limpio),
        "anio_min": int(df_limpio["anio"].min()) if len(df_limpio) > 0 else None,
        "anio_max": int(df_limpio["anio"].max()) if len(df_limpio) > 0 else None,
        "anios_distintos": int(df_limpio["anio"].nunique(dropna=True)),
        "anios_fuera_periodo": anios_fuera_periodo,
        "nulos_clave": int(df_limpio["anio"].isna().sum()),
        "valores_numericos_nulos": valores_numericos_nulos,
        "valores_numericos_negativos": valores_numericos_negativos,
        "duplicados_exactos_finales": int(df_limpio.duplicated().sum()),
        "duplicados_por_clave": int(df_limpio.duplicated(subset=["anio"]).sum()),
        "superficie_total_ha": float(df_limpio["deforestacion_ha"].sum()),
        "estado_validacion": "ok",
        "observaciones": "",
    }

    observaciones = []

    if len(df_limpio) == 0:
        observaciones.append("dataset_sin_filas_finales")

    if registro["anio_min"] != ANIO_MIN or registro["anio_max"] != ANIO_MAX:
        observaciones.append("periodo_final_distinto_al_esperado")

    if registro["anios_distintos"] != (ANIO_MAX - ANIO_MIN + 1):
        observaciones.append("numero_de_anios_distinto_al_esperado")

    if registro["nulos_clave"] > 0:
        observaciones.append("existen_nulos_en_clave")

    if valores_numericos_nulos > 0:
        observaciones.append("existen_valores_numericos_nulos")

    if valores_numericos_negativos > 0:
        observaciones.append("existen_valores_numericos_negativos")

    if registro["duplicados_exactos_finales"] > 0:
        observaciones.append("existen_duplicados_exactos_finales")

    if registro["duplicados_por_clave"] > 0:
        observaciones.append("existen_duplicados_por_clave")

    if limites_inconsistentes > 0:
        observaciones.append("existen_limites_inconsistentes")

    if observaciones:
        registro["estado_validacion"] = "revisar"
        registro["observaciones"] = "; ".join(observaciones)

    return registro


# =========================================================
# 5) VALIDACIÓN CRUZADA INTERNA
# =========================================================

def crear_validacion_consistencia(
    superficie: Optional[pd.DataFrame],
    incertidumbre: Optional[pd.DataFrame],
) -> Dict[str, object]:

    nombre_dataset = "consistencia_superficie_vs_incertidumbre"

    if superficie is None or incertidumbre is None:
        return {
            "dataset": nombre_dataset,
            "archivo_origen": ARCHIVO_DEFORESTACION,
            "hoja_origen": f"{HOJA_SUPERFICIE} | {HOJA_INCERTIDUMBRE}",
            "filas_leidas": 0,
            "columnas_leidas": 0,
            "filas_finales": 0,
            "columnas_finales": 0,
            "filas_eliminadas": 0,
            "anio_min": None,
            "anio_max": None,
            "anios_distintos": None,
            "anios_fuera_periodo": None,
            "nulos_clave": None,
            "valores_numericos_nulos": None,
            "valores_numericos_negativos": None,
            "duplicados_exactos_finales": None,
            "duplicados_por_clave": None,
            "superficie_total_ha": None,
            "estado_validacion": "error",
            "observaciones": "no_se_pudo_validar_consistencia_por_dataset_faltante",
        }

    suma = (
        superficie.groupby("anio", as_index=False)["superficie_deforestada_ha"]
        .sum()
        .rename(columns={"superficie_deforestada_ha": "superficie_sumada_ha"})
    )

    comp = suma.merge(
        incertidumbre[["anio", "deforestacion_ha"]],
        on="anio",
        how="outer",
    )

    comp["diferencia_abs_ha"] = (
        comp["superficie_sumada_ha"] - comp["deforestacion_ha"]
    ).abs()

    max_diferencia = float(comp["diferencia_abs_ha"].max()) if len(comp) > 0 else None
    anios_con_diferencia = int((comp["diferencia_abs_ha"] > 0.01).sum()) if len(comp) > 0 else None

    estado = "ok"
    observaciones = ""

    if anios_con_diferencia and anios_con_diferencia > 0:
        estado = "revisar"
        observaciones = "la_suma_anual_de_superficie_no_coincide_con_deforestacion"

    return {
        "dataset": nombre_dataset,
        "archivo_origen": ARCHIVO_DEFORESTACION,
        "hoja_origen": f"{HOJA_SUPERFICIE} | {HOJA_INCERTIDUMBRE}",
        "filas_leidas": len(comp),
        "columnas_leidas": len(comp.columns),
        "filas_finales": len(comp),
        "columnas_finales": len(comp.columns),
        "filas_eliminadas": 0,
        "anio_min": int(comp["anio"].min()) if len(comp) > 0 else None,
        "anio_max": int(comp["anio"].max()) if len(comp) > 0 else None,
        "anios_distintos": int(comp["anio"].nunique(dropna=True)) if len(comp) > 0 else None,
        "anios_fuera_periodo": int((~comp["anio"].between(ANIO_MIN, ANIO_MAX)).sum()) if len(comp) > 0 else None,
        "nulos_clave": int(comp["anio"].isna().sum()) if len(comp) > 0 else None,
        "valores_numericos_nulos": int(comp[["superficie_sumada_ha", "deforestacion_ha"]].isna().any(axis=1).sum()) if len(comp) > 0 else None,
        "valores_numericos_negativos": int((comp[["superficie_sumada_ha", "deforestacion_ha"]] < 0).any(axis=1).sum()) if len(comp) > 0 else None,
        "duplicados_exactos_finales": int(comp.duplicated().sum()) if len(comp) > 0 else None,
        "duplicados_por_clave": int(comp.duplicated(subset=["anio"]).sum()) if len(comp) > 0 else None,
        "superficie_total_ha": float(comp["superficie_sumada_ha"].sum()) if len(comp) > 0 else None,
        "estado_validacion": estado,
        "observaciones": observaciones,
        "max_diferencia_abs_ha": max_diferencia,
        "anios_con_diferencia_mayor_0_01ha": anios_con_diferencia,
    }


# =========================================================
# 6) PIPELINE PRINCIPAL
# =========================================================

def main() -> None:
    print("\nINFyS | Data Preparation - Deforestación nacional")
    print(f"Directorio raw: {RAW_DIR}")
    print(f"Directorio datasets: {DATASETS_DIR}")
    print(f"Directorio reports: {REPORTS_DIR}")

    if not RAW_DIR.exists():
        raise FileNotFoundError(f"No existe RAW_DIR: {RAW_DIR}")

    validaciones = []

    try:
        superficie, validacion_superficie = preparar_superficie_deforestada()
    except Exception as e:
        print(f"ERROR en infys_deforestacion_superficie_nacional_limpio: {e}")
        superficie = None
        validacion_superficie = registro_error(
            "infys_deforestacion_superficie_nacional_limpio",
            ARCHIVO_DEFORESTACION,
            HOJA_SUPERFICIE,
            str(e),
        )

    guardar_dataset(
        superficie,
        OUT_SUPERFICIE,
        "infys_deforestacion_superficie_nacional_limpio",
    )
    validaciones.append(validacion_superficie)

    try:
        incertidumbre, validacion_incertidumbre = preparar_incertidumbre()
    except Exception as e:
        print(f"ERROR en infys_deforestacion_incertidumbre_nacional_limpio: {e}")
        incertidumbre = None
        validacion_incertidumbre = registro_error(
            "infys_deforestacion_incertidumbre_nacional_limpio",
            ARCHIVO_DEFORESTACION,
            HOJA_INCERTIDUMBRE,
            str(e),
        )

    guardar_dataset(
        incertidumbre,
        OUT_INCERTIDUMBRE,
        "infys_deforestacion_incertidumbre_nacional_limpio",
    )
    validaciones.append(validacion_incertidumbre)

    validacion_consistencia = crear_validacion_consistencia(superficie, incertidumbre)
    validaciones.append(validacion_consistencia)

    df_validacion = pd.DataFrame(validaciones)
    df_validacion.to_csv(OUT_VALIDACION, index=False, encoding="utf-8-sig")

    print(f"\nReporte de validación generado: {OUT_VALIDACION}")

    print("\n=== RESUMEN DP DEFORESTACIÓN INFyS ===")
    for registro in validaciones:
        print(
            f"- {registro['dataset']}: "
            f"{registro['filas_finales']} filas finales | "
            f"estado={registro['estado_validacion']}"
        )

    print("\nProceso terminado.")


if __name__ == "__main__":
    main()