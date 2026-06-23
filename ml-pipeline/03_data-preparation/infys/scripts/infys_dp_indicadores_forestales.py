# -*- coding: utf-8 -*-
"""
INFyS | Data Preparation - Indicadores forestales

Fase CRISP-DM:
- Data Preparation

Objetivo:
Preparar estructuralmente productos tabulares de indicadores forestales INFyS,
normalizando encabezados, columnas, nulos, textos, tipos básicos, campos
canónicos, coordenadas geográficas cuando existan y metadatos de origen.

Entradas esperadas:
- 01_raw-data/infys/2_Dasometricos.xlsx
- 01_raw-data/infys/4_Estructura.xlsx
- 01_raw-data/infys/5_Salud_arbolado.xlsx
- 01_raw-data/infys/Composicion_INFyS-2015-2020_Tablas_23062023.xlsx
- 01_raw-data/infys/Estructura_INFyS-2015-2020_Tablas.xlsx
- 01_raw-data/infys/IVI_e_IVF_INFyS-2015-2020_Tablas.xlsx
- 01_raw-data/infys/Distribucion_AT-DN_INFyS-2015-2020_Tablas.xlsx
- 01_raw-data/infys/Existencias_INFyS-2015-2020_Tablas.xlsx
- 01_raw-data/infys/Incremento_Medio_Anual_INFyS-2015-2020_Tablas.xlsx
- 01_raw-data/infys/Indicadores_Dasometricos_INFyS_2015_2020.xlsx
- 01_raw-data/infys/SaludFtal_INFyS-2015-2020_Tablas.xlsx
- 01_raw-data/infys/Tipo-propiedad_INFyS-2015-2020_Tablas.xlsx

Salidas:
- 03_data-preparation/infys/datasets/infys_indicadores_dasometricos_limpio.csv
- 03_data-preparation/infys/datasets/infys_indicadores_estructura_limpio.csv
- 03_data-preparation/infys/datasets/infys_indicadores_salud_forestal_limpio.csv
- 03_data-preparation/infys/datasets/infys_indicadores_composicion_limpio.csv
- 03_data-preparation/infys/datasets/infys_indicadores_ivi_ivf_limpio.csv
- 03_data-preparation/infys/datasets/infys_indicadores_distribucion_at_dn_limpio.csv
- 03_data-preparation/infys/datasets/infys_indicadores_existencias_limpio.csv
- 03_data-preparation/infys/datasets/infys_indicadores_incremento_medio_anual_limpio.csv
- 03_data-preparation/infys/datasets/infys_indicadores_tipo_propiedad_limpio.csv
- 03_data-preparation/infys/reports/infys_dp_indicadores_forestales_validacion.csv
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

OUT_VALIDACION = REPORTS_DIR / "infys_dp_indicadores_forestales_validacion.csv"

CONFIG_FAMILIAS = {
    "dasometricos": {
        "salida": DATASETS_DIR / "infys_indicadores_dasometricos_limpio.csv",
        "archivos": [
            "2_Dasometricos.xlsx",
            "Indicadores_Dasometricos_INFyS_2015_2020.xlsx",
        ],
    },
    "estructura": {
        "salida": DATASETS_DIR / "infys_indicadores_estructura_limpio.csv",
        "archivos": [
            "4_Estructura.xlsx",
            "Estructura_INFyS-2015-2020_Tablas.xlsx",
        ],
    },
    "salud_forestal": {
        "salida": DATASETS_DIR / "infys_indicadores_salud_forestal_limpio.csv",
        "archivos": [
            "5_Salud_arbolado.xlsx",
            "SaludFtal_INFyS-2015-2020_Tablas.xlsx",
        ],
    },
    "composicion": {
        "salida": DATASETS_DIR / "infys_indicadores_composicion_limpio.csv",
        "archivos": [
            "Composicion_INFyS-2015-2020_Tablas_23062023.xlsx",
        ],
    },
    "ivi_ivf": {
        "salida": DATASETS_DIR / "infys_indicadores_ivi_ivf_limpio.csv",
        "archivos": [
            "IVI_e_IVF_INFyS-2015-2020_Tablas.xlsx",
        ],
    },
    "distribucion_at_dn": {
        "salida": DATASETS_DIR / "infys_indicadores_distribucion_at_dn_limpio.csv",
        "archivos": [
            "Distribucion_AT-DN_INFyS-2015-2020_Tablas.xlsx",
        ],
    },
    "existencias": {
        "salida": DATASETS_DIR / "infys_indicadores_existencias_limpio.csv",
        "archivos": [
            "Existencias_INFyS-2015-2020_Tablas.xlsx",
        ],
    },
    "incremento_medio_anual": {
        "salida": DATASETS_DIR / "infys_indicadores_incremento_medio_anual_limpio.csv",
        "archivos": [
            "Incremento_Medio_Anual_INFyS-2015-2020_Tablas.xlsx",
        ],
    },
    "tipo_propiedad": {
        "salida": DATASETS_DIR / "infys_indicadores_tipo_propiedad_limpio.csv",
        "archivos": [
            "Tipo-propiedad_INFyS-2015-2020_Tablas.xlsx",
        ],
    },
}

HOJAS_OMITIR = {
    "diccionario",
    "tabla_de_correspondencia",
    "tabla_correspondencia",
}

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
# 2) UTILIDADES GENERALES
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
    texto = texto.strip("_")

    return texto if texto else "columna_sin_nombre"


def normalizar_columnas_unicas(columnas: List[object]) -> List[str]:
    columnas_norm = []
    contador = {}

    for col in columnas:
        base = normalizar_columna(col)

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


def limpiar_filas_columnas_vacias(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out = out.dropna(axis=0, how="all")
    out = out.dropna(axis=1, how="all")
    return out.reset_index(drop=True)


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
        return texto if texto else pd.NA

    return s.map(limpiar)


def detectar_columna(columnas: List[str], candidatos: List[str]) -> Optional[str]:
    columnas_norm = {normalizar_columna(c): c for c in columnas}

    for candidato in candidatos:
        candidato_norm = normalizar_columna(candidato)

        if candidato_norm in columnas_norm:
            return columnas_norm[candidato_norm]

    for candidato in candidatos:
        candidato_norm = normalizar_columna(candidato)

        for col_norm, col_original in columnas_norm.items():
            if candidato_norm in col_norm:
                return col_original

    return None


def ordenar_columnas(df: pd.DataFrame, columnas_prioritarias: List[str]) -> pd.DataFrame:
    existentes = [c for c in columnas_prioritarias if c in df.columns]
    restantes = [c for c in df.columns if c not in existentes]
    return df[existentes + restantes]


def contar_no_nulos(fila: pd.Series) -> int:
    return int(fila.notna().sum())


def contar_textos(fila: pd.Series) -> int:
    total = 0

    for valor in fila:
        if pd.notna(valor) and not isinstance(valor, (int, float)):
            total += 1

    return total


# =========================================================
# 3) LECTURA ROBUSTA DE HOJAS
# =========================================================

def inferir_encabezado(raw: pd.DataFrame) -> Tuple[pd.DataFrame, int, bool]:
    raw_limpio = limpiar_filas_columnas_vacias(raw)

    if raw_limpio.empty:
        return raw_limpio, 0, False

    limite = min(6, len(raw_limpio))
    perfiles = []

    for i in range(limite):
        fila = raw_limpio.iloc[i]
        perfiles.append(
            {
                "indice": i,
                "no_nulos": contar_no_nulos(fila),
                "textos": contar_textos(fila),
            }
        )

    if limite >= 2 and perfiles[0]["no_nulos"] <= 2 and perfiles[1]["no_nulos"] >= 2:
        fila_encabezado = 1
    else:
        fila_encabezado = sorted(
            perfiles,
            key=lambda x: (x["textos"], x["no_nulos"]),
            reverse=True,
        )[0]["indice"]

    usa_dos_filas = False

    if fila_encabezado + 1 < len(raw_limpio):
        fila_1 = raw_limpio.iloc[fila_encabezado]
        fila_2 = raw_limpio.iloc[fila_encabezado + 1]

        matriz = pd.concat([fila_1, fila_2], axis=1)
        columnas_utiles = matriz.notna().any(axis=1)

        if columnas_utiles.any():
            ultima_col = max([i for i, valor in enumerate(columnas_utiles) if valor])
            f1 = fila_1.iloc[: ultima_col + 1]
            f2 = fila_2.iloc[: ultima_col + 1]

            blancos_f1 = int(f1.isna().sum())
            textos_f2 = contar_textos(f2)
            no_nulos_f2 = contar_no_nulos(f2)

            if blancos_f1 > 0 and textos_f2 >= 2 and no_nulos_f2 >= 2:
                usa_dos_filas = True

    return raw_limpio, fila_encabezado, usa_dos_filas


def construir_encabezados(raw_limpio: pd.DataFrame, fila_encabezado: int, usa_dos_filas: bool) -> Tuple[List[str], int]:
    if raw_limpio.empty:
        return [], 0

    if not usa_dos_filas:
        encabezados = normalizar_columnas_unicas(list(raw_limpio.iloc[fila_encabezado]))
        return encabezados, fila_encabezado + 1

    fila_1 = list(raw_limpio.iloc[fila_encabezado])
    fila_2 = list(raw_limpio.iloc[fila_encabezado + 1])

    encabezados = []
    grupo_actual = ""

    for valor_1, valor_2 in zip(fila_1, fila_2):
        if pd.notna(valor_1):
            grupo_actual = str(valor_1)

        if pd.notna(valor_2):
            if grupo_actual and str(valor_2).strip() != grupo_actual.strip():
                nombre = f"{grupo_actual}_{valor_2}"
            else:
                nombre = str(valor_2)
        elif pd.notna(valor_1):
            nombre = str(valor_1)
        elif grupo_actual:
            nombre = grupo_actual
        else:
            nombre = "columna_sin_nombre"

        encabezados.append(nombre)

    encabezados = normalizar_columnas_unicas(encabezados)
    return encabezados, fila_encabezado + 2


def leer_hoja_generica(ruta: Path, hoja: str) -> Tuple[pd.DataFrame, Dict[str, object]]:
    raw = pd.read_excel(ruta, sheet_name=hoja, header=None)
    raw_limpio, fila_encabezado, usa_dos_filas = inferir_encabezado(raw)
    encabezados, fila_inicio_datos = construir_encabezados(raw_limpio, fila_encabezado, usa_dos_filas)

    if raw_limpio.empty:
        return pd.DataFrame(), {
            "filas_leidas": len(raw),
            "columnas_leidas": len(raw.columns),
            "fila_encabezado_detectada": None,
            "encabezado_dos_filas": False,
        }

    df = raw_limpio.iloc[fila_inicio_datos:, :].copy()
    df.columns = encabezados[: df.shape[1]]

    df = limpiar_filas_columnas_vacias(df)
    df = estandarizar_nulos(df)
    df = limpiar_textos_objeto(df)

    return df, {
        "filas_leidas": len(raw),
        "columnas_leidas": len(raw.columns),
        "fila_encabezado_detectada": fila_encabezado,
        "encabezado_dos_filas": usa_dos_filas,
    }


# =========================================================
# 4) CAMPOS CANÓNICOS Y TIPOS
# =========================================================

def validar_rango_lat_lon(lat: pd.Series, lon: pd.Series) -> pd.Series:
    return (
        lat.notna()
        & lon.notna()
        & lat.between(14.0, 33.5)
        & lon.between(-119.0, -86.0)
    )


def seleccionar_par_coordenadas(df: pd.DataFrame) -> Tuple[pd.Series, pd.Series, str]:
    columnas = list(df.columns)
    n = len(df)

    candidatos = [
        {
            "fuente": "latitud_longitud",
            "lat": detectar_columna(columnas, ["latitud", "lat", "latitude"]),
            "lon": detectar_columna(columnas, ["longitud", "lon", "long", "longitude"]),
        },
        {
            "fuente": "x_y",
            "lat": detectar_columna(columnas, ["y"]),
            "lon": detectar_columna(columnas, ["x"]),
        },
        {
            "fuente": "x_c3_y_c3",
            "lat": detectar_columna(columnas, ["y_c3"]),
            "lon": detectar_columna(columnas, ["x_c3"]),
        },
    ]

    serie_vacia_lat = pd.Series([pd.NA] * n, index=df.index, dtype="Float64")
    serie_vacia_lon = pd.Series([pd.NA] * n, index=df.index, dtype="Float64")

    mejor = {
        "fuente": "sin_coordenadas_validas",
        "validas": 0,
        "lat": serie_vacia_lat,
        "lon": serie_vacia_lon,
    }

    for candidato in candidatos:
        if candidato["lat"] is None or candidato["lon"] is None:
            continue

        lat = convertir_numero(df[candidato["lat"]])
        lon = convertir_numero(df[candidato["lon"]])

        con_coords = lat.notna() & lon.notna()

        if int(con_coords.sum()) == 0:
            continue

        validas = int(validar_rango_lat_lon(lat, lon).sum())

        if validas > mejor["validas"]:
            mejor = {
                "fuente": candidato["fuente"],
                "validas": validas,
                "lat": lat,
                "lon": lon,
            }

    if mejor["validas"] == 0:
        return serie_vacia_lat, serie_vacia_lon, "sin_coordenadas_validas"

    return mejor["lat"], mejor["lon"], mejor["fuente"]


def agregar_campos_canonicos(df: pd.DataFrame, familia: str, archivo: str, hoja: str) -> pd.DataFrame:
    out = df.copy()
    columnas = list(out.columns)

    col_upmid = detectar_columna(columnas, ["upmid", "upm_id", "id_upm", "upm"])
    col_conglomerado = detectar_columna(columnas, ["idconglomerado", "id_conglomerado", "conglomerado"])
    col_sitio = detectar_columna(columnas, ["id_sitio", "idsitio", "sitio", "num_sitio", "sitio_c3"])
    col_anio = detectar_columna(columnas, ["anio", "ano", "año", "anio_c3", "year"])
    col_estado = detectar_columna(columnas, ["estado_c3", "estado", "entidad", "nom_ent", "entidad_federativa"])
    col_ecosistema = detectar_columna(columnas, ["ecosistema"])
    col_formacion = detectar_columna(columnas, ["formacion", "formacion_forestal", "form_s7", "formacion_ff", "formacion_ftal"])
    col_especie = detectar_columna(columnas, ["especie", "nombre_cientifico", "nombre_cientifico_1"])
    col_genero = detectar_columna(columnas, ["genero"])
    col_familia = detectar_columna(columnas, ["familia"])

    if col_upmid is not None:
        out["upmid"] = normalizar_identificador(out[col_upmid])
    else:
        out["upmid"] = pd.NA

    if col_conglomerado is not None:
        out["id_conglomerado"] = normalizar_identificador(out[col_conglomerado])
    else:
        out["id_conglomerado"] = pd.NA

    if col_sitio is not None:
        out["id_sitio"] = normalizar_identificador(out[col_sitio])
    else:
        out["id_sitio"] = pd.NA

    if col_anio is not None:
        out["anio"] = normalizar_entero(out[col_anio])
    else:
        out["anio"] = pd.NA

    if col_estado is not None:
        out["estado"] = out[col_estado].map(normalizar_texto)
    else:
        out["estado"] = pd.NA

    if col_ecosistema is not None:
        out["ecosistema"] = out[col_ecosistema].map(normalizar_texto)
    else:
        out["ecosistema"] = pd.NA

    if col_formacion is not None:
        out["formacion_forestal"] = out[col_formacion].map(normalizar_texto)
    else:
        out["formacion_forestal"] = pd.NA

    if col_especie is not None:
        out["especie"] = out[col_especie].map(normalizar_texto)
    else:
        out["especie"] = pd.NA

    if col_genero is not None:
        out["genero"] = out[col_genero].map(normalizar_texto)
    else:
        out["genero"] = pd.NA

    if col_familia is not None:
        out["familia_taxonomica"] = out[col_familia].map(normalizar_texto)
    else:
        out["familia_taxonomica"] = pd.NA

    latitud, longitud, fuente_coord = seleccionar_par_coordenadas(out)
    out["latitud"] = latitud
    out["longitud"] = longitud
    out["fuente_coordenadas"] = fuente_coord

    out["familia_indicador"] = familia
    out["tipo_tabla"] = normalizar_columna(hoja)
    out["archivo_origen"] = archivo
    out["hoja_origen"] = hoja

    if "2015" in archivo or "2020" in archivo:
        out["ciclo_infys"] = "2015-2020"
    else:
        out["ciclo_infys"] = "no_especificado"

    return out


def normalizar_tipos_basicos(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()

    for col in out.columns:
        col_norm = normalizar_columna(col)

        if col_norm in {
            "upmid",
            "idconglomerado",
            "id_conglomerado",
            "id_sitio",
            "sitio",
            "sitio_c3",
        }:
            out[col] = normalizar_identificador(out[col])

        elif (
            col_norm in {"anio", "ano", "año", "cve_eco", "cve_for", "cve_estado", "cve_municipio"}
            or col_norm.startswith("cve_")
            or col_norm.endswith("_n")
            or col_norm == "n"
            or col_norm == "ump"
            or "frecuencia" in col_norm
            or "numero" in col_norm
            or "registros" in col_norm
            or "taxones" in col_norm
        ):
            out[col] = normalizar_entero(out[col])

        elif (
            col_norm in {"ha", "er", "li", "ls"}
            or "media" in col_norm
            or "mediana" in col_norm
            or "min" in col_norm
            or "max" in col_norm
            or "promedio" in col_norm
            or "proporcion" in col_norm
            or "porcentaje" in col_norm
            or "volumen" in col_norm
            or "biomasa" in col_norm
            or "carbono" in col_norm
            or "area_basal" in col_norm
            or "diametro" in col_norm
            or "altura" in col_norm
            or "cobertura" in col_norm
            or "densidad" in col_norm
            or "abundancia" in col_norm
            or "dominancia" in col_norm
            or "incremento" in col_norm
            or col_norm.endswith("_pct")
        ):
            out[col] = convertir_numero(out[col])

    return out


# =========================================================
# 5) VALIDACIÓN
# =========================================================

def validar_coordenadas_mexico(df: pd.DataFrame) -> Tuple[int, int, int]:
    if "latitud" not in df.columns or "longitud" not in df.columns:
        return 0, 0, 0

    con_coords = df["latitud"].notna() & df["longitud"].notna()
    lat_fuera = con_coords & ~df["latitud"].between(14.0, 33.5)
    lon_fuera = con_coords & ~df["longitud"].between(-119.0, -86.0)

    return int(con_coords.sum()), int(lat_fuera.sum()), int(lon_fuera.sum())


def crear_registro_validacion(
    familia: str,
    ruta_salida: Path,
    archivos_procesados: int,
    hojas_procesadas: int,
    hojas_omitidas: int,
    filas_leidas: int,
    columnas_leidas_max: int,
    df_limpio: pd.DataFrame,
    errores: List[str],
) -> Dict[str, object]:

    columnas_numericas = df_limpio.select_dtypes(include=["number"]).columns.tolist()
    con_coords, lat_fuera, lon_fuera = validar_coordenadas_mexico(df_limpio)

    registro = {
        "familia_indicador": familia,
        "ruta_salida": str(ruta_salida),
        "archivos_procesados": archivos_procesados,
        "hojas_procesadas": hojas_procesadas,
        "hojas_omitidas": hojas_omitidas,
        "filas_leidas": filas_leidas,
        "columnas_leidas_max": columnas_leidas_max,
        "filas_finales": len(df_limpio),
        "columnas_finales": len(df_limpio.columns),
        "duplicados_exactos_finales": int(df_limpio.duplicated().sum()) if len(df_limpio) > 0 else 0,
        "columnas_numericas": len(columnas_numericas),
        "registros_con_coordenadas": con_coords,
        "latitud_fuera_mexico": lat_fuera,
        "longitud_fuera_mexico": lon_fuera,
        "tablas_distintas": int(df_limpio["tipo_tabla"].nunique(dropna=True)) if "tipo_tabla" in df_limpio.columns else 0,
        "archivos_origen_distintos": int(df_limpio["archivo_origen"].nunique(dropna=True)) if "archivo_origen" in df_limpio.columns else 0,
        "estado_validacion": "ok",
        "observaciones": "",
    }

    observaciones = []

    if errores:
        observaciones.append("existen_errores_de_lectura")

    if len(df_limpio) == 0:
        observaciones.append("dataset_sin_filas_finales")

    if registro["duplicados_exactos_finales"] > 0:
        observaciones.append("existen_duplicados_exactos_finales")

    if con_coords > 0 and (lat_fuera > 0 or lon_fuera > 0):
        observaciones.append("existen_coordenadas_fuera_rango_mexico")

    if observaciones:
        registro["estado_validacion"] = "revisar"
        registro["observaciones"] = "; ".join(observaciones)

    if errores:
        registro["detalle_errores"] = " | ".join(errores[:10])
    else:
        registro["detalle_errores"] = ""

    return registro


def registro_error_familia(familia: str, ruta_salida: Path, mensaje: str) -> Dict[str, object]:
    return {
        "familia_indicador": familia,
        "ruta_salida": str(ruta_salida),
        "archivos_procesados": 0,
        "hojas_procesadas": 0,
        "hojas_omitidas": 0,
        "filas_leidas": 0,
        "columnas_leidas_max": 0,
        "filas_finales": 0,
        "columnas_finales": 0,
        "duplicados_exactos_finales": None,
        "columnas_numericas": None,
        "registros_con_coordenadas": None,
        "latitud_fuera_mexico": None,
        "longitud_fuera_mexico": None,
        "tablas_distintas": None,
        "archivos_origen_distintos": None,
        "estado_validacion": "error",
        "observaciones": mensaje,
        "detalle_errores": mensaje,
    }


# =========================================================
# 6) PREPARACIÓN POR FAMILIA
# =========================================================

def hoja_debe_omitirse(nombre_hoja: str) -> bool:
    hoja_norm = normalizar_columna(nombre_hoja)
    return hoja_norm in HOJAS_OMITIR


def preparar_familia(familia: str, config: Dict[str, object]) -> Tuple[pd.DataFrame, Dict[str, object]]:
    datasets = []
    errores = []

    archivos_procesados = 0
    hojas_procesadas = 0
    hojas_omitidas = 0
    filas_leidas = 0
    columnas_leidas_max = 0

    for archivo in config["archivos"]:
        ruta = buscar_archivo(archivo)

        if ruta is None:
            errores.append(f"{archivo}: archivo_no_encontrado")
            continue

        print(f"Archivo: {archivo}")
        archivos_procesados += 1

        try:
            xls = pd.ExcelFile(ruta)
        except Exception as e:
            errores.append(f"{archivo}: error_abriendo_excel: {e}")
            continue

        for hoja in xls.sheet_names:
            if hoja_debe_omitirse(hoja):
                hojas_omitidas += 1
                continue

            print(f"  Hoja: {hoja}")

            try:
                df, meta = leer_hoja_generica(ruta, hoja)

                filas_leidas += int(meta["filas_leidas"])
                columnas_leidas_max = max(columnas_leidas_max, int(meta["columnas_leidas"]))

                if df.empty:
                    hojas_omitidas += 1
                    continue

                df = normalizar_tipos_basicos(df)
                df = agregar_campos_canonicos(df, familia, archivo, hoja)

                df["fila_encabezado_detectada"] = meta["fila_encabezado_detectada"]
                df["encabezado_dos_filas"] = meta["encabezado_dos_filas"]

                df = df.drop_duplicates().reset_index(drop=True)

                columnas_prioritarias = [
                    "ciclo_infys",
                    "familia_indicador",
                    "tipo_tabla",
                    "upmid",
                    "id_conglomerado",
                    "id_sitio",
                    "anio",
                    "estado",
                    "ecosistema",
                    "formacion_forestal",
                    "familia_taxonomica",
                    "genero",
                    "especie",
                    "latitud",
                    "longitud",
                    "fuente_coordenadas",
                    "archivo_origen",
                    "hoja_origen",
                    "fila_encabezado_detectada",
                    "encabezado_dos_filas",
                ]

                df = ordenar_columnas(df, columnas_prioritarias)

                datasets.append(df)
                hojas_procesadas += 1

            except Exception as e:
                errores.append(f"{archivo} | {hoja}: {e}")

    datasets_validos = [
        d.dropna(axis=1, how="all")
        for d in datasets
        if d is not None and not d.empty
    ]

    if datasets_validos:
        out = pd.concat(datasets_validos, ignore_index=True, sort=False)
        out = out.drop_duplicates().reset_index(drop=True)
    else:
        out = pd.DataFrame()

    validacion = crear_registro_validacion(
        familia=familia,
        ruta_salida=config["salida"],
        archivos_procesados=archivos_procesados,
        hojas_procesadas=hojas_procesadas,
        hojas_omitidas=hojas_omitidas,
        filas_leidas=filas_leidas,
        columnas_leidas_max=columnas_leidas_max,
        df_limpio=out,
        errores=errores,
    )

    return out, validacion


def guardar_dataset(df: pd.DataFrame, ruta_salida: Path, familia: str) -> None:
    if df.empty:
        print(f"No se generó dataset para {familia}.")
        return

    df.to_csv(ruta_salida, index=False, encoding="utf-8-sig")
    print(f"Dataset generado: {ruta_salida}")


# =========================================================
# 7) PIPELINE PRINCIPAL
# =========================================================

def main() -> None:
    print("\nINFyS | Data Preparation - Indicadores forestales")
    print(f"Directorio raw: {RAW_DIR}")
    print(f"Directorio datasets: {DATASETS_DIR}")
    print(f"Directorio reports: {REPORTS_DIR}")

    if not RAW_DIR.exists():
        raise FileNotFoundError(f"No existe RAW_DIR: {RAW_DIR}")

    validaciones = []

    for familia, config in CONFIG_FAMILIAS.items():
        print(f"\nProcesando familia: {familia}")

        try:
            df_limpio, validacion = preparar_familia(familia, config)
            guardar_dataset(df_limpio, config["salida"], familia)
            validaciones.append(validacion)

        except Exception as e:
            print(f"ERROR en familia {familia}: {e}")
            validaciones.append(
                registro_error_familia(
                    familia=familia,
                    ruta_salida=config["salida"],
                    mensaje=str(e),
                )
            )

    df_validacion = pd.DataFrame(validaciones)
    df_validacion.to_csv(OUT_VALIDACION, index=False, encoding="utf-8-sig")

    print(f"\nReporte de validación generado: {OUT_VALIDACION}")

    print("\n=== RESUMEN DP INDICADORES FORESTALES INFyS ===")
    for registro in validaciones:
        print(
            f"- {registro['familia_indicador']}: "
            f"{registro['filas_finales']} filas finales | "
            f"estado={registro['estado_validacion']}"
        )

    print("\nProceso terminado.")


if __name__ == "__main__":
    main()