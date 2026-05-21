# -*- coding: utf-8 -*-
"""
INFyS | Data Preparation - Suelos

Fase CRISP-DM:
- Data Preparation

Objetivo:
Preparar estructuralmente productos tabulares de suelos INFyS, normalizando
columnas, textos, nulos, identificadores, campos numéricos, metadatos de origen
y validaciones básicas de calidad.

Entradas esperadas:
- 01_raw-data/infys/6_Suelos.xlsx
- 01_raw-data/infys/Suelos_INFyS-2015-2020_Tablas.xlsx

Salidas:
- 03_data-preparation/infys/datasets/infys_suelos_agregados_base_limpio.csv
- 03_data-preparation/infys/datasets/infys_suelos_2015_2020_base_limpio.csv
- 03_data-preparation/infys/datasets/infys_suelos_2015_2020_agregados_limpio.csv
- 03_data-preparation/infys/reports/infys_dp_suelos_validacion.csv
"""

from __future__ import annotations

import re
import unicodedata
from pathlib import Path
from typing import Dict, List, Optional, Tuple

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

ARCHIVO_SUELOS_BASE = "6_Suelos.xlsx"
ARCHIVO_SUELOS_2015_2020 = "Suelos_INFyS-2015-2020_Tablas.xlsx"

OUT_SUELOS_AGREGADOS_BASE = DATASETS_DIR / "infys_suelos_agregados_base_limpio.csv"
OUT_SUELOS_2015_2020_BASE = DATASETS_DIR / "infys_suelos_2015_2020_base_limpio.csv"
OUT_SUELOS_2015_2020_AGREGADOS = DATASETS_DIR / "infys_suelos_2015_2020_agregados_limpio.csv"

OUT_VALIDACION = REPORTS_DIR / "infys_dp_suelos_validacion.csv"

HOJA_BASE_2015_2020 = "BaseDatos_Suelo"

HOJAS_AGREGADAS_2015_2020 = [
    "Profundidad_Pendiente",
    "Categ_profundidad",
    "Categ_pendiente",
    "Uso_suelo",
    "Erosión",
    "Erosión Hídrica",
    "Erosón eólica",
]

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


def normalizar_columnas_unicas(columnas: List[object]) -> List[str]:
    columnas_norm = []
    contador = {}

    for col in columnas:
        base = normalizar_columna(col)

        if base == "":
            base = "columna_sin_nombre"

        if base not in contador:
            contador[base] = 0
            columnas_norm.append(base)
        else:
            contador[base] += 1
            columnas_norm.append(f"{base}_{contador[base]}")

    return columnas_norm


def buscar_archivo(nombre_archivo: str) -> Optional[Path]:
    coincidencias = sorted(RAW_DIR.rglob(nombre_archivo))

    if not coincidencias:
        return None

    if len(coincidencias) > 1:
        print(f"Advertencia: múltiples coincidencias para {nombre_archivo}. Se usará: {coincidencias[0]}")

    return coincidencias[0]


def estandarizar_nulos(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()

    for col in out.columns:
        if pd.api.types.is_object_dtype(out[col]) or pd.api.types.is_string_dtype(out[col]):
            s = out[col].astype("string")
            s = s.str.strip()
            s = s.mask(s.str.upper().isin(TOKENS_NULOS), pd.NA)
            out[col] = s

    return out


def limpiar_textos_objeto(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()

    for col in out.columns:
        if pd.api.types.is_object_dtype(out[col]) or pd.api.types.is_string_dtype(out[col]):
            out[col] = out[col].map(lambda x: normalizar_texto(x) if not pd.isna(x) else pd.NA)

    return out


def convertir_numero(serie: pd.Series) -> pd.Series:
    s = serie.astype("string")
    s = s.str.replace(",", "", regex=False)
    s = s.str.replace(" ", "", regex=False)
    s = s.str.strip()
    s = s.mask(s.str.upper().isin(TOKENS_NULOS), pd.NA)
    return pd.to_numeric(s, errors="coerce")


def normalizar_entero(serie: pd.Series) -> pd.Series:
    n = convertir_numero(serie)
    return n.round(0).astype("Int64")


def normalizar_identificador(serie: pd.Series) -> pd.Series:
    s = serie.astype("string")
    s = s.str.strip()
    s = s.mask(s.str.upper().isin(TOKENS_NULOS), pd.NA)

    def limpiar(valor):
        if pd.isna(valor):
            return pd.NA

        texto = str(valor).strip()

        if re.fullmatch(r"\d+\.0", texto):
            texto = texto[:-2]

        texto = re.sub(r"\s+", "", texto)
        return texto if texto != "" else pd.NA

    return s.map(limpiar)


def limpiar_filas_columnas_vacias(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out = out.dropna(axis=0, how="all")
    out = out.dropna(axis=1, how="all")
    return out.reset_index(drop=True)


def detectar_columna(columnas: List[str], candidatos: List[str]) -> Optional[str]:
    columnas_norm = {normalizar_columna(c): c for c in columnas}

    for candidato in candidatos:
        candidato_norm = normalizar_columna(candidato)

        for col_norm, col_original in columnas_norm.items():
            if candidato_norm == col_norm:
                return col_original

    for candidato in candidatos:
        candidato_norm = normalizar_columna(candidato)

        for col_norm, col_original in columnas_norm.items():
            if candidato_norm in col_norm:
                return col_original

    return None


def normalizar_tipos_basicos(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()

    for col in out.columns:
        col_norm = normalizar_columna(col)

        if col_norm in {
            "upmid",
            "idconglomerado",
            "id_conglomerado",
            "sitio",
            "id_sitio",
        }:
            out[col] = normalizar_identificador(out[col])

        elif (
            col_norm.startswith("cve")
            or col_norm in {"anio", "ano", "ump", "frecuencia"}
            or "numero" in col_norm
            or "conglomerados" in col_norm
        ):
            out[col] = normalizar_entero(out[col])

        elif (
            col_norm in {"ha", "er", "li", "ls"}
            or "superficie" in col_norm
            or "profundidad" in col_norm
            or "pendiente" in col_norm
            or "proporcion" in col_norm
            or "porcentaje" in col_norm
            or col_norm.endswith("_pct")
        ):
            out[col] = convertir_numero(out[col])

    return out


def ordenar_columnas(df: pd.DataFrame, columnas_prioritarias: List[str]) -> pd.DataFrame:
    existentes = [c for c in columnas_prioritarias if c in df.columns]
    restantes = [c for c in df.columns if c not in existentes]
    return df[existentes + restantes]


# =========================================================
# 3) LECTURA ESPECIAL DE TABLAS AGREGADAS 2015-2020
# =========================================================

def construir_encabezados_dos_filas(raw: pd.DataFrame) -> Tuple[List[str], int]:
    fila_1 = raw.iloc[1, :].copy()
    fila_2 = raw.iloc[2, :].copy() if len(raw) > 2 else pd.Series([pd.NA] * raw.shape[1])

    usa_dos_filas = False

    if len(raw) > 2:
        primera_col_fila_2_vacia = pd.isna(fila_2.iloc[0])
        subencabezados = fila_2.notna().sum()

        if primera_col_fila_2_vacia and subencabezados > 0:
            usa_dos_filas = True

    if not usa_dos_filas:
        encabezados = normalizar_columnas_unicas(list(fila_1))
        return encabezados, 2

    encabezados = []
    grupo_actual = ""

    for valor_1, valor_2 in zip(fila_1, fila_2):
        if pd.notna(valor_1):
            grupo_actual = str(valor_1)

        if pd.notna(valor_2):
            nombre = f"{grupo_actual}_{valor_2}" if grupo_actual else str(valor_2)
        else:
            nombre = str(valor_1) if pd.notna(valor_1) else grupo_actual

        encabezados.append(nombre)

    encabezados = normalizar_columnas_unicas(encabezados)
    return encabezados, 3


def leer_tabla_agregada_2015_2020(ruta: Path, hoja: str) -> Tuple[pd.DataFrame, pd.DataFrame]:
    raw = pd.read_excel(ruta, sheet_name=hoja, header=None)
    raw = limpiar_filas_columnas_vacias(raw)

    encabezados, fila_inicio = construir_encabezados_dos_filas(raw)

    df = raw.iloc[fila_inicio:, :].copy()
    df.columns = encabezados
    df = limpiar_filas_columnas_vacias(df)
    df = estandarizar_nulos(df)
    df = limpiar_textos_objeto(df)

    if "ecosistema" in df.columns:
        df["ecosistema"] = df["ecosistema"].ffill()

    if "formacion_forestal" in df.columns:
        df["formacion_forestal"] = df["formacion_forestal"].ffill()

    df = normalizar_tipos_basicos(df)
    df = df.drop_duplicates().reset_index(drop=True)

    return raw, df


# =========================================================
# 4) PREPARACIÓN - 6_SUELOS.XLSX
# =========================================================

def preparar_suelos_agregados_base() -> Tuple[Optional[pd.DataFrame], Dict[str, object]]:
    nombre_dataset = "infys_suelos_agregados_base_limpio"

    ruta = buscar_archivo(ARCHIVO_SUELOS_BASE)

    if ruta is None:
        return None, registro_error(
            nombre_dataset,
            ARCHIVO_SUELOS_BASE,
            "varias",
            "archivo_no_encontrado",
        )

    print(f"Procesando: {ruta.name} | hojas agregadas")

    xls = pd.ExcelFile(ruta)
    datasets = []

    for hoja in xls.sheet_names:
        df_original = pd.read_excel(ruta, sheet_name=hoja)
        df = df_original.copy()

        df.columns = normalizar_columnas_unicas(list(df.columns))
        df = limpiar_filas_columnas_vacias(df)
        df = estandarizar_nulos(df)
        df = limpiar_textos_objeto(df)
        df = normalizar_tipos_basicos(df)

        df["archivo_origen"] = ARCHIVO_SUELOS_BASE
        df["hoja_origen"] = hoja
        df["ciclo_infys"] = "no_especificado"
        df["tipo_producto_suelo"] = normalizar_columna(hoja)

        df = df.drop_duplicates().reset_index(drop=True)
        datasets.append(df)

    if not datasets:
        out = pd.DataFrame()
    else:
        out = pd.concat(datasets, ignore_index=True, sort=False)

    columnas_prioritarias = [
        "ciclo_infys",
        "tipo_producto_suelo",
        "cve_eco",
        "ecosistema",
        "cve_for",
        "formacion",
        "grupo_de_suelo",
        "uso_de_suelo",
        "afectacion",
        "clase",
        "tipo",
        "formas_afectacion",
        "indicador",
        "unidad",
        "ha",
        "ump",
        "frecuencia",
        "er",
        "li",
        "ls",
        "archivo_origen",
        "hoja_origen",
    ]

    out = ordenar_columnas(out, columnas_prioritarias)

    validacion = crear_validacion_general(
        nombre_dataset=nombre_dataset,
        archivo_origen=ARCHIVO_SUELOS_BASE,
        hoja_origen="varias",
        filas_leidas=sum(len(pd.read_excel(ruta, sheet_name=h)) for h in xls.sheet_names),
        columnas_leidas=None,
        df_limpio=out,
        ruta_salida=OUT_SUELOS_AGREGADOS_BASE,
    )

    return out, validacion


# =========================================================
# 5) PREPARACIÓN - BASEDATOS_SUELO 2015-2020
# =========================================================

def preparar_suelos_2015_2020_base() -> Tuple[Optional[pd.DataFrame], Dict[str, object]]:
    nombre_dataset = "infys_suelos_2015_2020_base_limpio"

    ruta = buscar_archivo(ARCHIVO_SUELOS_2015_2020)

    if ruta is None:
        return None, registro_error(
            nombre_dataset,
            ARCHIVO_SUELOS_2015_2020,
            HOJA_BASE_2015_2020,
            "archivo_no_encontrado",
        )

    print(f"Procesando: {ruta.name} | hoja: {HOJA_BASE_2015_2020}")

    df_original = pd.read_excel(ruta, sheet_name=HOJA_BASE_2015_2020)
    df = df_original.copy()

    df.columns = normalizar_columnas_unicas(list(df.columns))
    df = limpiar_filas_columnas_vacias(df)
    df = estandarizar_nulos(df)
    df = limpiar_textos_objeto(df)
    df = normalizar_tipos_basicos(df)

    col_upmid = detectar_columna(list(df.columns), ["upmid", "upm_id", "id_upm"])
    col_conglomerado = detectar_columna(list(df.columns), ["idconglomerado", "id_conglomerado", "conglomerado"])
    col_sitio = detectar_columna(list(df.columns), ["sitio", "id_sitio", "num_sitio"])
    col_estado = detectar_columna(list(df.columns), ["estado_c3", "estado", "entidad"])
    col_formacion = detectar_columna(list(df.columns), ["form_s7", "formacion", "formacion_forestal"])
    col_anio = detectar_columna(list(df.columns), ["anio_c3", "anio", "ano"])

    if col_upmid is not None:
        df["upmid"] = normalizar_identificador(df[col_upmid])
    else:
        df["upmid"] = pd.NA

    if col_conglomerado is not None:
        df["id_conglomerado"] = normalizar_identificador(df[col_conglomerado])
    else:
        df["id_conglomerado"] = pd.NA

    if col_sitio is not None:
        df["id_sitio"] = normalizar_identificador(df[col_sitio])
    else:
        df["id_sitio"] = pd.NA

    if col_estado is not None:
        df["estado"] = df[col_estado].map(normalizar_texto)
    else:
        df["estado"] = pd.NA

    if col_formacion is not None:
        df["formacion_forestal"] = df[col_formacion].map(normalizar_texto)
    else:
        df["formacion_forestal"] = pd.NA

    if col_anio is not None:
        df["anio"] = normalizar_entero(df[col_anio])
    else:
        df["anio"] = pd.NA

    df["archivo_origen"] = ARCHIVO_SUELOS_2015_2020
    df["hoja_origen"] = HOJA_BASE_2015_2020
    df["ciclo_infys"] = "2015-2020"

    df = df.drop_duplicates().reset_index(drop=True)

    columnas_prioritarias = [
        "ciclo_infys",
        "upmid",
        "id_conglomerado",
        "id_sitio",
        "anio",
        "estado",
        "formacion_forestal",
        "profundidadsuelo_cm",
        "clase_profundidad",
        "profundidad_descripcion",
        "pendiente",
        "clase_pendiente",
        "pendiente_descripcion",
        "uso_de_suelo",
        "archivo_origen",
        "hoja_origen",
    ]

    out = ordenar_columnas(df, columnas_prioritarias)

    validacion = crear_validacion_base_suelos(
        nombre_dataset=nombre_dataset,
        archivo_origen=ARCHIVO_SUELOS_2015_2020,
        hoja_origen=HOJA_BASE_2015_2020,
        filas_leidas=len(df_original),
        columnas_leidas=len(df_original.columns),
        df_limpio=out,
        ruta_salida=OUT_SUELOS_2015_2020_BASE,
    )

    return out, validacion


# =========================================================
# 6) PREPARACIÓN - AGREGADOS 2015-2020
# =========================================================

def preparar_suelos_2015_2020_agregados() -> Tuple[Optional[pd.DataFrame], Dict[str, object]]:
    nombre_dataset = "infys_suelos_2015_2020_agregados_limpio"

    ruta = buscar_archivo(ARCHIVO_SUELOS_2015_2020)

    if ruta is None:
        return None, registro_error(
            nombre_dataset,
            ARCHIVO_SUELOS_2015_2020,
            "varias",
            "archivo_no_encontrado",
        )

    print(f"Procesando: {ruta.name} | hojas agregadas")

    datasets = []
    filas_leidas = 0

    for hoja in HOJAS_AGREGADAS_2015_2020:
        raw, df = leer_tabla_agregada_2015_2020(ruta, hoja)

        filas_leidas += len(raw)

        df["archivo_origen"] = ARCHIVO_SUELOS_2015_2020
        df["hoja_origen"] = hoja
        df["ciclo_infys"] = "2015-2020"
        df["tipo_producto_suelo"] = normalizar_columna(hoja)

        df = df.drop_duplicates().reset_index(drop=True)
        datasets.append(df)

    if not datasets:
        out = pd.DataFrame()
    else:
        out = pd.concat(datasets, ignore_index=True, sort=False)

    columnas_prioritarias = [
        "ciclo_infys",
        "tipo_producto_suelo",
        "ecosistema",
        "formacion_forestal",
        "superficie",
        "ump",
        "archivo_origen",
        "hoja_origen",
    ]

    out = ordenar_columnas(out, columnas_prioritarias)

    validacion = crear_validacion_general(
        nombre_dataset=nombre_dataset,
        archivo_origen=ARCHIVO_SUELOS_2015_2020,
        hoja_origen="varias",
        filas_leidas=filas_leidas,
        columnas_leidas=None,
        df_limpio=out,
        ruta_salida=OUT_SUELOS_2015_2020_AGREGADOS,
    )

    return out, validacion


# =========================================================
# 7) VALIDACIONES
# =========================================================

def crear_validacion_general(
    nombre_dataset: str,
    archivo_origen: str,
    hoja_origen: str,
    filas_leidas: int,
    columnas_leidas: Optional[int],
    df_limpio: pd.DataFrame,
    ruta_salida: Path,
) -> Dict[str, object]:

    columnas_clave = [
        c for c in ["ciclo_infys", "tipo_producto_suelo", "ecosistema", "formacion", "formacion_forestal"]
        if c in df_limpio.columns
    ]

    duplicados_clave = None
    if columnas_clave:
        duplicados_clave = int(df_limpio.duplicated(subset=columnas_clave).sum())

    columnas_numericas = df_limpio.select_dtypes(include=["number"]).columns.tolist()

    valores_numericos_nulos = int(df_limpio[columnas_numericas].isna().any(axis=1).sum()) if columnas_numericas else 0
    valores_numericos_negativos = int((df_limpio[columnas_numericas] < 0).any(axis=1).sum()) if columnas_numericas else 0

    registro = {
        "dataset": nombre_dataset,
        "archivo_origen": archivo_origen,
        "hoja_origen": hoja_origen,
        "ruta_salida": str(ruta_salida),
        "filas_leidas": filas_leidas,
        "columnas_leidas": columnas_leidas,
        "filas_finales": len(df_limpio),
        "columnas_finales": len(df_limpio.columns),
        "filas_eliminadas": filas_leidas - len(df_limpio),
        "duplicados_exactos_finales": int(df_limpio.duplicated().sum()),
        "duplicados_por_clave": duplicados_clave,
        "columnas_numericas": len(columnas_numericas),
        "valores_numericos_nulos": valores_numericos_nulos,
        "valores_numericos_negativos": valores_numericos_negativos,
        "id_conglomerado_nulos": int(df_limpio["id_conglomerado"].isna().sum()) if "id_conglomerado" in df_limpio.columns else None,
        "id_sitio_nulos": int(df_limpio["id_sitio"].isna().sum()) if "id_sitio" in df_limpio.columns else None,
        "anio_min": int(df_limpio["anio"].min()) if "anio" in df_limpio.columns and df_limpio["anio"].notna().any() else None,
        "anio_max": int(df_limpio["anio"].max()) if "anio" in df_limpio.columns and df_limpio["anio"].notna().any() else None,
        "estado_validacion": "ok",
        "observaciones": "",
    }

    observaciones = []

    if len(df_limpio) == 0:
        observaciones.append("dataset_sin_filas_finales")

    if registro["duplicados_exactos_finales"] > 0:
        observaciones.append("existen_duplicados_exactos_finales")

    if valores_numericos_negativos > 0:
        observaciones.append("existen_valores_numericos_negativos")

    if observaciones:
        registro["estado_validacion"] = "revisar"
        registro["observaciones"] = "; ".join(observaciones)

    return registro


def crear_validacion_base_suelos(
    nombre_dataset: str,
    archivo_origen: str,
    hoja_origen: str,
    filas_leidas: int,
    columnas_leidas: int,
    df_limpio: pd.DataFrame,
    ruta_salida: Path,
) -> Dict[str, object]:

    columnas_clave = ["upmid", "id_conglomerado", "id_sitio"]

    columnas_clave_existentes = [
        c for c in columnas_clave
        if c in df_limpio.columns and df_limpio[c].notna().any()
    ]

    duplicados_clave = None
    if columnas_clave_existentes:
        duplicados_clave = int(df_limpio.duplicated(subset=columnas_clave_existentes).sum())

    columnas_numericas = df_limpio.select_dtypes(include=["number"]).columns.tolist()
    valores_numericos_nulos = int(df_limpio[columnas_numericas].isna().any(axis=1).sum()) if columnas_numericas else 0
    valores_numericos_negativos = int((df_limpio[columnas_numericas] < 0).any(axis=1).sum()) if columnas_numericas else 0

    registro = {
        "dataset": nombre_dataset,
        "archivo_origen": archivo_origen,
        "hoja_origen": hoja_origen,
        "ruta_salida": str(ruta_salida),
        "filas_leidas": filas_leidas,
        "columnas_leidas": columnas_leidas,
        "filas_finales": len(df_limpio),
        "columnas_finales": len(df_limpio.columns),
        "filas_eliminadas": filas_leidas - len(df_limpio),
        "duplicados_exactos_finales": int(df_limpio.duplicated().sum()),
        "duplicados_por_clave": duplicados_clave,
        "columnas_numericas": len(columnas_numericas),
        "valores_numericos_nulos": valores_numericos_nulos,
        "valores_numericos_negativos": valores_numericos_negativos,
        "id_conglomerado_nulos": int(df_limpio["id_conglomerado"].isna().sum()) if "id_conglomerado" in df_limpio.columns else None,
        "id_sitio_nulos": int(df_limpio["id_sitio"].isna().sum()) if "id_sitio" in df_limpio.columns else None,
        "anio_min": int(df_limpio["anio"].min()) if "anio" in df_limpio.columns and df_limpio["anio"].notna().any() else None,
        "anio_max": int(df_limpio["anio"].max()) if "anio" in df_limpio.columns and df_limpio["anio"].notna().any() else None,
        "estado_validacion": "ok",
        "observaciones": "",
    }

    observaciones = []

    if len(df_limpio) == 0:
        observaciones.append("dataset_sin_filas_finales")

    if registro["duplicados_exactos_finales"] > 0:
        observaciones.append("existen_duplicados_exactos_finales")

    if duplicados_clave is not None and duplicados_clave > 0:
        observaciones.append("existen_duplicados_por_clave")

    if "id_conglomerado" in df_limpio.columns and df_limpio["id_conglomerado"].isna().all():
        observaciones.append("no_se_detecto_id_conglomerado")

    if "id_sitio" in df_limpio.columns and df_limpio["id_sitio"].isna().all():
        observaciones.append("no_se_detecto_id_sitio")

    if valores_numericos_negativos > 0:
        observaciones.append("existen_valores_numericos_negativos")

    if observaciones:
        registro["estado_validacion"] = "revisar"
        registro["observaciones"] = "; ".join(observaciones)

    return registro


def registro_error(
    nombre_dataset: str,
    archivo_origen: str,
    hoja_origen: str,
    mensaje: str,
) -> Dict[str, object]:

    return {
        "dataset": nombre_dataset,
        "archivo_origen": archivo_origen,
        "hoja_origen": hoja_origen,
        "ruta_salida": "",
        "filas_leidas": 0,
        "columnas_leidas": 0,
        "filas_finales": 0,
        "columnas_finales": 0,
        "filas_eliminadas": 0,
        "duplicados_exactos_finales": None,
        "duplicados_por_clave": None,
        "columnas_numericas": None,
        "valores_numericos_nulos": None,
        "valores_numericos_negativos": None,
        "id_conglomerado_nulos": None,
        "id_sitio_nulos": None,
        "anio_min": None,
        "anio_max": None,
        "estado_validacion": "error",
        "observaciones": mensaje,
    }


# =========================================================
# 8) GUARDADO Y PIPELINE PRINCIPAL
# =========================================================

def guardar_dataset(df: Optional[pd.DataFrame], ruta_salida: Path, nombre_dataset: str) -> None:
    if df is None:
        print(f"No se generó {nombre_dataset}.")
        return

    df.to_csv(ruta_salida, index=False, encoding="utf-8-sig")
    print(f"Dataset generado: {ruta_salida}")


def ejecutar_bloque(nombre_dataset: str, funcion):
    try:
        df, validacion = funcion()
        return df, validacion
    except Exception as e:
        print(f"ERROR en {nombre_dataset}: {e}")
        return None, registro_error(nombre_dataset, "", "", str(e))


def main() -> None:
    print("\nINFyS | Data Preparation - Suelos")
    print(f"Directorio raw: {RAW_DIR}")
    print(f"Directorio datasets: {DATASETS_DIR}")
    print(f"Directorio reports: {REPORTS_DIR}")

    if not RAW_DIR.exists():
        raise FileNotFoundError(f"No existe RAW_DIR: {RAW_DIR}")

    validaciones = []

    suelos_agregados_base, val_agregados_base = ejecutar_bloque(
        "infys_suelos_agregados_base_limpio",
        preparar_suelos_agregados_base,
    )
    guardar_dataset(
        suelos_agregados_base,
        OUT_SUELOS_AGREGADOS_BASE,
        "infys_suelos_agregados_base_limpio",
    )
    validaciones.append(val_agregados_base)

    suelos_2015_base, val_2015_base = ejecutar_bloque(
        "infys_suelos_2015_2020_base_limpio",
        preparar_suelos_2015_2020_base,
    )
    guardar_dataset(
        suelos_2015_base,
        OUT_SUELOS_2015_2020_BASE,
        "infys_suelos_2015_2020_base_limpio",
    )
    validaciones.append(val_2015_base)

    suelos_2015_agregados, val_2015_agregados = ejecutar_bloque(
        "infys_suelos_2015_2020_agregados_limpio",
        preparar_suelos_2015_2020_agregados,
    )
    guardar_dataset(
        suelos_2015_agregados,
        OUT_SUELOS_2015_2020_AGREGADOS,
        "infys_suelos_2015_2020_agregados_limpio",
    )
    validaciones.append(val_2015_agregados)

    df_validacion = pd.DataFrame(validaciones)
    df_validacion.to_csv(OUT_VALIDACION, index=False, encoding="utf-8-sig")

    print(f"\nReporte de validación generado: {OUT_VALIDACION}")

    print("\n=== RESUMEN DP SUELOS INFyS ===")
    for registro in validaciones:
        print(
            f"- {registro['dataset']}: "
            f"{registro['filas_finales']} filas finales | "
            f"estado={registro['estado_validacion']}"
        )

    print("\nProceso terminado.")


if __name__ == "__main__":
    main()