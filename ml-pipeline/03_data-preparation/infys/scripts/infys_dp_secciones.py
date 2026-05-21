# -*- coding: utf-8 -*-
"""
INFyS | Data Preparation - Secciones de muestreo

Fase CRISP-DM:
- Data Preparation

Objetivo:
Preparar estructuralmente las hojas de conglomerados y sitios de los workbooks
INFyS_Secciones, conservando limpieza, normalización sintáctica,
homologación básica de claves/campos y validación de calidad.

Entradas esperadas:
- 01_raw-data/infys/INFyS_Secciones_2004_2009.xlsx
- 01_raw-data/infys/INFyS_Secciones_2009_2014.xlsx
- 01_raw-data/infys/INFyS_Secciones_2015-2020.xlsx

Salidas:
- 03_data-preparation/infys/datasets/infys_secciones_conglomerados_2004_2009_limpio.csv
- 03_data-preparation/infys/datasets/infys_secciones_sitios_2004_2009_limpio.csv
- 03_data-preparation/infys/datasets/infys_secciones_conglomerados_2009_2014_limpio.csv
- 03_data-preparation/infys/datasets/infys_secciones_sitios_2009_2014_limpio.csv
- 03_data-preparation/infys/datasets/infys_secciones_conglomerados_2015_2020_limpio.csv
- 03_data-preparation/infys/datasets/infys_secciones_sitios_2015_2020_limpio.csv
- 03_data-preparation/infys/reports/infys_dp_secciones_validacion.csv
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

OUT_VALIDACION = REPORTS_DIR / "infys_dp_secciones_validacion.csv"

CONFIG_BLOQUES = [
    {
        "archivo": "INFyS_Secciones_2004_2009.xlsx",
        "ciclo_infys": "2004-2009",
        "tipo_seccion": "conglomerados",
        "hoja": "Conglomerados",
        "salida": "infys_secciones_conglomerados_2004_2009_limpio.csv",
    },
    {
        "archivo": "INFyS_Secciones_2004_2009.xlsx",
        "ciclo_infys": "2004-2009",
        "tipo_seccion": "sitios",
        "hoja": "Sitios",
        "salida": "infys_secciones_sitios_2004_2009_limpio.csv",
    },
    {
        "archivo": "INFyS_Secciones_2009_2014.xlsx",
        "ciclo_infys": "2009-2014",
        "tipo_seccion": "conglomerados",
        "hoja": "Conglomerados",
        "salida": "infys_secciones_conglomerados_2009_2014_limpio.csv",
    },
    {
        "archivo": "INFyS_Secciones_2009_2014.xlsx",
        "ciclo_infys": "2009-2014",
        "tipo_seccion": "sitios",
        "hoja": "Sitios",
        "salida": "infys_secciones_sitios_2009_2014_limpio.csv",
    },
    {
        "archivo": "INFyS_Secciones_2015-2020.xlsx",
        "ciclo_infys": "2015-2020",
        "tipo_seccion": "conglomerados",
        "hoja": "estatus_conglomerado_universal",
        "salida": "infys_secciones_conglomerados_2015_2020_limpio.csv",
    },
    {
        "archivo": "INFyS_Secciones_2015-2020.xlsx",
        "ciclo_infys": "2015-2020",
        "tipo_seccion": "sitios",
        "hoja": "estatus_sitios_universal",
        "salida": "infys_secciones_sitios_2015_2020_limpio.csv",
    },
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


def convertir_numero(serie: pd.Series) -> pd.Series:
    s = serie.astype("string")
    s = s.str.replace(",", "", regex=False)
    s = s.str.replace(" ", "", regex=False)
    s = s.str.strip()
    s = s.mask(s.str.upper().isin(TOKENS_NULOS), pd.NA)
    return pd.to_numeric(s, errors="coerce")


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


def normalizar_entero(serie: pd.Series) -> pd.Series:
    n = convertir_numero(serie)
    return n.round(0).astype("Int64")


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


def detectar_columna_exacta(columnas: List[str], candidatos: List[str]) -> Optional[str]:
    columnas_norm = {normalizar_columna(c): c for c in columnas}

    for candidato in candidatos:
        candidato_norm = normalizar_columna(candidato)

        if candidato_norm in columnas_norm:
            return columnas_norm[candidato_norm]

    return None


def leer_hoja_excel(ruta: Path, hoja: str) -> Tuple[pd.DataFrame, pd.DataFrame]:
    xls = pd.ExcelFile(ruta)

    if hoja not in xls.sheet_names:
        raise ValueError(
            f"No se encontró la hoja '{hoja}' en {ruta.name}. "
            f"Hojas disponibles: {xls.sheet_names}"
        )

    df_original = pd.read_excel(ruta, sheet_name=hoja)
    df = limpiar_filas_columnas_vacias(df_original)
    df.columns = normalizar_columnas_unicas(list(df.columns))
    df = estandarizar_nulos(df)

    return df_original, df


def limpiar_textos_objeto(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()

    for col in out.columns:
        if pd.api.types.is_object_dtype(out[col]) or pd.api.types.is_string_dtype(out[col]):
            out[col] = out[col].map(
                lambda x: normalizar_texto(x) if not pd.isna(x) else pd.NA
            )

    return out


def ordenar_columnas(df: pd.DataFrame, columnas_prioritarias: List[str]) -> pd.DataFrame:
    existentes = [c for c in columnas_prioritarias if c in df.columns]
    restantes = [c for c in df.columns if c not in existentes]
    return df[existentes + restantes]


# =========================================================
# 3) COORDENADAS
# =========================================================

def validar_rango_lat_lon(lat: pd.Series, lon: pd.Series) -> pd.Series:
    return (
        lat.notna()
        & lon.notna()
        & lat.between(14.0, 33.5)
        & lon.between(-119.0, -86.0)
    )


def seleccionar_par_coordenadas(df: pd.DataFrame) -> Tuple[pd.Series, pd.Series, pd.Series, pd.Series, str]:
    columnas = list(df.columns)
    n = len(df)

    candidatos = [
        {
            "fuente": "latitud_longitud",
            "lat": detectar_columna_exacta(columnas, ["latitud", "lat", "latitude"]),
            "lon": detectar_columna_exacta(columnas, ["longitud", "lon", "long", "longitude"]),
            "x": None,
            "y": None,
        },
        {
            "fuente": "x_y",
            "lat": detectar_columna_exacta(columnas, ["y"]),
            "lon": detectar_columna_exacta(columnas, ["x"]),
            "x": detectar_columna_exacta(columnas, ["x"]),
            "y": detectar_columna_exacta(columnas, ["y"]),
        },
        {
            "fuente": "x_c3_y_c3",
            "lat": detectar_columna_exacta(columnas, ["y_c3"]),
            "lon": detectar_columna_exacta(columnas, ["x_c3"]),
            "x": detectar_columna_exacta(columnas, ["x_c3"]),
            "y": detectar_columna_exacta(columnas, ["y_c3"]),
        },
        {
            "fuente": "auxiliar",
            "lat": detectar_columna_exacta(columnas, ["latitud_aux", "y_aux"]),
            "lon": detectar_columna_exacta(columnas, ["longitud_aux", "x_aux"]),
            "x": detectar_columna_exacta(columnas, ["x_aux"]),
            "y": detectar_columna_exacta(columnas, ["y_aux"]),
        },
    ]

    mejor = {
        "fuente": "sin_coordenadas",
        "validas": -1,
        "lat": pd.Series([pd.NA] * n, index=df.index, dtype="Float64"),
        "lon": pd.Series([pd.NA] * n, index=df.index, dtype="Float64"),
        "x": pd.Series([pd.NA] * n, index=df.index, dtype="Float64"),
        "y": pd.Series([pd.NA] * n, index=df.index, dtype="Float64"),
    }

    for candidato in candidatos:
        if candidato["lat"] is None or candidato["lon"] is None:
            continue

        lat = convertir_numero(df[candidato["lat"]])
        lon = convertir_numero(df[candidato["lon"]])
        validas = int(validar_rango_lat_lon(lat, lon).sum())

        if candidato["x"] is not None:
            coord_x = convertir_numero(df[candidato["x"]])
        else:
            coord_x = lon.copy()

        if candidato["y"] is not None:
            coord_y = convertir_numero(df[candidato["y"]])
        else:
            coord_y = lat.copy()

        if validas > mejor["validas"]:
            mejor = {
                "fuente": candidato["fuente"],
                "validas": validas,
                "lat": lat,
                "lon": lon,
                "x": coord_x,
                "y": coord_y,
            }

    if mejor["validas"] <= 0:
        return (
            pd.Series([pd.NA] * n, index=df.index, dtype="Float64"),
            pd.Series([pd.NA] * n, index=df.index, dtype="Float64"),
            pd.Series([pd.NA] * n, index=df.index, dtype="Float64"),
            pd.Series([pd.NA] * n, index=df.index, dtype="Float64"),
            "sin_coordenadas_validas",
        )

    return mejor["lat"], mejor["lon"], mejor["x"], mejor["y"], mejor["fuente"]


def validar_coordenadas_mexico(df: pd.DataFrame) -> Tuple[int, int, int]:
    if "latitud" not in df.columns or "longitud" not in df.columns:
        return 0, 0, 0

    con_coords = df["latitud"].notna() & df["longitud"].notna()

    lat_fuera = con_coords & ~df["latitud"].between(14.0, 33.5)
    lon_fuera = con_coords & ~df["longitud"].between(-119.0, -86.0)

    return int(con_coords.sum()), int(lat_fuera.sum()), int(lon_fuera.sum())


# =========================================================
# 4) CAMPOS CANÓNICOS
# =========================================================

def agregar_campos_canonicos(df: pd.DataFrame, ciclo_infys: str, tipo_seccion: str) -> pd.DataFrame:
    out = df.copy()
    columnas = list(out.columns)

    col_conglomerado = detectar_columna(
        columnas,
        [
            "id_conglomerado",
            "idconglomerado",
            "conglomerado",
            "upmid",
            "upm_id",
            "id_upm",
            "upm",
        ],
    )

    col_upmid = detectar_columna(
        columnas,
        [
            "upmid",
            "upm_id",
            "id_upm",
            "upm",
        ],
    )

    col_sitio = detectar_columna(
        columnas,
        [
            "id_sitio",
            "idsitio",
            "num_sitio",
            "numsitio",
            "sitio_c3",
            "sitio",
            "cvesitio_c3",
            "cve_sitio",
            "no_sitio",
            "numero_sitio",
        ],
    )

    col_anio = detectar_columna(
        columnas,
        [
            "anio",
            "ano",
            "año",
            "anio_c3",
            "year",
        ],
    )

    col_cve_estado = detectar_columna(
        columnas,
        [
            "cve_estado",
            "cve_ent",
            "cve_estado_c3",
        ],
    )

    col_estado = detectar_columna(
        columnas,
        [
            "estado",
            "estado_c3",
            "nom_ent",
            "entidad",
            "entidad_federativa",
            "nombre_estado",
        ],
    )

    col_cve_municipio = detectar_columna(
        columnas,
        [
            "cve_municipio",
            "cve_mun",
            "cve_municipio_c3",
        ],
    )

    col_municipio = detectar_columna(
        columnas,
        [
            "municipio",
            "municipio_c3",
            "nom_mun",
            "nombre_municipio",
        ],
    )

    if col_conglomerado is not None:
        out["id_conglomerado"] = normalizar_identificador(out[col_conglomerado])
    else:
        out["id_conglomerado"] = pd.NA

    if col_upmid is not None:
        out["upmid"] = normalizar_identificador(out[col_upmid])
    else:
        out["upmid"] = pd.NA

    if col_sitio is not None:
        out["id_sitio"] = normalizar_identificador(out[col_sitio])
    else:
        out["id_sitio"] = pd.NA

    if col_anio is not None:
        out["anio"] = normalizar_entero(out[col_anio])
    else:
        out["anio"] = pd.NA

    if col_cve_estado is not None:
        out["cve_ent"] = normalizar_entero(out[col_cve_estado]).astype("string").str.zfill(2)
        out["cve_ent"] = out["cve_ent"].mask(out["cve_ent"] == "<NA>", pd.NA)
    else:
        out["cve_ent"] = pd.NA

    if col_estado is not None:
        out["estado"] = out[col_estado].map(normalizar_texto)
    else:
        out["estado"] = pd.NA

    if col_cve_municipio is not None:
        out["cve_mun"] = normalizar_entero(out[col_cve_municipio]).astype("string").str.zfill(3)
        out["cve_mun"] = out["cve_mun"].mask(out["cve_mun"] == "<NA>", pd.NA)
    else:
        out["cve_mun"] = pd.NA

    if col_municipio is not None:
        out["municipio"] = out[col_municipio].map(normalizar_texto)
    else:
        out["municipio"] = pd.NA

    latitud, longitud, coord_x, coord_y, fuente_coord = seleccionar_par_coordenadas(out)

    out["latitud"] = latitud
    out["longitud"] = longitud
    out["coord_x"] = coord_x
    out["coord_y"] = coord_y
    out["fuente_coordenadas"] = fuente_coord

    out["ciclo_infys"] = ciclo_infys
    out["tipo_seccion"] = tipo_seccion

    return out


# =========================================================
# 5) VALIDACIÓN
# =========================================================

def crear_registro_validacion(
    nombre_dataset: str,
    archivo_origen: str,
    hoja_origen: str,
    ciclo_infys: str,
    tipo_seccion: str,
    filas_leidas: int,
    columnas_leidas: int,
    df_limpio: pd.DataFrame,
    ruta_salida: Path,
) -> Dict[str, object]:

    con_coords, lat_fuera, lon_fuera = validar_coordenadas_mexico(df_limpio)

    if tipo_seccion == "sitios":
        columnas_clave = ["id_conglomerado", "id_sitio"]
    else:
        columnas_clave = ["id_conglomerado"]

    columnas_clave_existentes = [
        c for c in columnas_clave
        if c in df_limpio.columns and df_limpio[c].notna().any()
    ]

    if columnas_clave_existentes:
        duplicados_clave = int(df_limpio.duplicated(subset=columnas_clave_existentes).sum())
    else:
        duplicados_clave = None

    registro = {
        "dataset": nombre_dataset,
        "archivo_origen": archivo_origen,
        "hoja_origen": hoja_origen,
        "ciclo_infys": ciclo_infys,
        "tipo_seccion": tipo_seccion,
        "ruta_salida": str(ruta_salida),
        "filas_leidas": filas_leidas,
        "columnas_leidas": columnas_leidas,
        "filas_finales": len(df_limpio),
        "columnas_finales": len(df_limpio.columns),
        "filas_eliminadas": filas_leidas - len(df_limpio),
        "duplicados_exactos_finales": int(df_limpio.duplicated().sum()),
        "duplicados_por_clave": duplicados_clave,
        "id_conglomerado_nulos": int(df_limpio["id_conglomerado"].isna().sum()) if "id_conglomerado" in df_limpio.columns else None,
        "id_sitio_nulos": int(df_limpio["id_sitio"].isna().sum()) if "id_sitio" in df_limpio.columns else None,
        "anio_nulos": int(df_limpio["anio"].isna().sum()) if "anio" in df_limpio.columns else None,
        "cve_ent_nulos": int(df_limpio["cve_ent"].isna().sum()) if "cve_ent" in df_limpio.columns else None,
        "estado_nulos": int(df_limpio["estado"].isna().sum()) if "estado" in df_limpio.columns else None,
        "cve_mun_nulos": int(df_limpio["cve_mun"].isna().sum()) if "cve_mun" in df_limpio.columns else None,
        "municipio_nulos": int(df_limpio["municipio"].isna().sum()) if "municipio" in df_limpio.columns else None,
        "registros_con_coordenadas": con_coords,
        "latitud_fuera_mexico": lat_fuera,
        "longitud_fuera_mexico": lon_fuera,
        "fuente_coordenadas": df_limpio["fuente_coordenadas"].dropna().iloc[0] if "fuente_coordenadas" in df_limpio.columns and len(df_limpio) > 0 else None,
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

    if tipo_seccion == "sitios" and "id_sitio" in df_limpio.columns and df_limpio["id_sitio"].isna().all():
        observaciones.append("no_se_detecto_id_sitio")

    if con_coords > 0 and (lat_fuera > 0 or lon_fuera > 0):
        observaciones.append("existen_coordenadas_fuera_rango_mexico")

    if observaciones:
        registro["estado_validacion"] = "revisar"
        registro["observaciones"] = "; ".join(observaciones)

    return registro


def registro_error(config: Dict[str, str], mensaje: str) -> Dict[str, object]:
    nombre_dataset = Path(config["salida"]).stem

    return {
        "dataset": nombre_dataset,
        "archivo_origen": config["archivo"],
        "hoja_origen": config["hoja"],
        "ciclo_infys": config["ciclo_infys"],
        "tipo_seccion": config["tipo_seccion"],
        "ruta_salida": str(DATASETS_DIR / config["salida"]),
        "filas_leidas": 0,
        "columnas_leidas": 0,
        "filas_finales": 0,
        "columnas_finales": 0,
        "filas_eliminadas": 0,
        "duplicados_exactos_finales": None,
        "duplicados_por_clave": None,
        "id_conglomerado_nulos": None,
        "id_sitio_nulos": None,
        "anio_nulos": None,
        "cve_ent_nulos": None,
        "estado_nulos": None,
        "cve_mun_nulos": None,
        "municipio_nulos": None,
        "registros_con_coordenadas": None,
        "latitud_fuera_mexico": None,
        "longitud_fuera_mexico": None,
        "fuente_coordenadas": None,
        "estado_validacion": "error",
        "observaciones": mensaje,
    }


# =========================================================
# 6) PREPARACIÓN DE BLOQUES
# =========================================================

def preparar_bloque(config: Dict[str, str]) -> Tuple[Optional[pd.DataFrame], Dict[str, object]]:
    archivo = config["archivo"]
    hoja = config["hoja"]
    ciclo_infys = config["ciclo_infys"]
    tipo_seccion = config["tipo_seccion"]
    nombre_dataset = Path(config["salida"]).stem
    ruta_salida = DATASETS_DIR / config["salida"]

    ruta = buscar_archivo(archivo)

    if ruta is None:
        return None, registro_error(config, "archivo_no_encontrado")

    print(f"Procesando: {archivo} | hoja: {hoja}")

    df_original, df_raw = leer_hoja_excel(ruta, hoja)

    df_limpio = df_raw.copy()
    df_limpio = limpiar_textos_objeto(df_limpio)
    df_limpio = agregar_campos_canonicos(df_limpio, ciclo_infys, tipo_seccion)

    df_limpio["archivo_origen"] = archivo
    df_limpio["hoja_origen"] = hoja

    df_limpio = df_limpio.drop_duplicates().copy()

    columnas_prioritarias = [
        "ciclo_infys",
        "tipo_seccion",
        "id_conglomerado",
        "upmid",
        "id_sitio",
        "anio",
        "cve_ent",
        "estado",
        "cve_mun",
        "municipio",
        "latitud",
        "longitud",
        "coord_x",
        "coord_y",
        "fuente_coordenadas",
        "archivo_origen",
        "hoja_origen",
    ]

    df_limpio = ordenar_columnas(df_limpio, columnas_prioritarias)
    df_limpio = df_limpio.reset_index(drop=True)

    validacion = crear_registro_validacion(
        nombre_dataset=nombre_dataset,
        archivo_origen=archivo,
        hoja_origen=hoja,
        ciclo_infys=ciclo_infys,
        tipo_seccion=tipo_seccion,
        filas_leidas=len(df_original),
        columnas_leidas=len(df_original.columns),
        df_limpio=df_limpio,
        ruta_salida=ruta_salida,
    )

    return df_limpio, validacion


def guardar_dataset(df: Optional[pd.DataFrame], ruta_salida: Path, nombre_dataset: str) -> None:
    if df is None:
        print(f"No se generó {nombre_dataset}.")
        return

    df.to_csv(ruta_salida, index=False, encoding="utf-8-sig")
    print(f"Dataset generado: {ruta_salida}")


# =========================================================
# 7) PIPELINE PRINCIPAL
# =========================================================

def main() -> None:
    print("\nINFyS | Data Preparation - Secciones de muestreo")
    print(f"Directorio raw: {RAW_DIR}")
    print(f"Directorio datasets: {DATASETS_DIR}")
    print(f"Directorio reports: {REPORTS_DIR}")

    if not RAW_DIR.exists():
        raise FileNotFoundError(f"No existe RAW_DIR: {RAW_DIR}")

    validaciones = []

    for config in CONFIG_BLOQUES:
        nombre_dataset = Path(config["salida"]).stem
        ruta_salida = DATASETS_DIR / config["salida"]

        try:
            df_limpio, validacion = preparar_bloque(config)
            guardar_dataset(df_limpio, ruta_salida, nombre_dataset)
            validaciones.append(validacion)

        except Exception as e:
            print(f"ERROR en {nombre_dataset}: {e}")
            validaciones.append(registro_error(config, str(e)))

    df_validacion = pd.DataFrame(validaciones)
    df_validacion.to_csv(OUT_VALIDACION, index=False, encoding="utf-8-sig")

    print(f"\nReporte de validación generado: {OUT_VALIDACION}")

    print("\n=== RESUMEN DP SECCIONES INFyS ===")
    for registro in validaciones:
        print(
            f"- {registro['dataset']}: "
            f"{registro['filas_finales']} filas finales | "
            f"estado={registro['estado_validacion']}"
        )

    print("\nProceso terminado.")


if __name__ == "__main__":
    main()