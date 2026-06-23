# -*- coding: utf-8 -*-
"""
INFyS | Data Preparation - Superficie forestal

Fase CRISP-DM:
- Data Preparation

Qué hace:
1) Prepara estructuralmente productos tabulares de superficie forestal INFyS.
2) Normaliza nombres de columnas.
3) Estandariza claves y nombres de entidad.
4) Homologa tipos de datos básicos.
5) Genera datasets limpios y un reporte de validación.

Entradas esperadas:
- 01_raw-data/infys/1_Superficie.xlsx
- 01_raw-data/infys/Superficie_forestal_INFyS-2015-2020_Tablas_v4_27042023.xlsx

Salidas:
- 03_data-preparation/infys/datasets/infys_superficie_base_limpio.csv
- 03_data-preparation/infys/datasets/infys_superficie_2015_2020_estatal_limpio.csv
- 03_data-preparation/infys/datasets/infys_superficie_2015_2020_detalle_limpio.csv
- 03_data-preparation/infys/reports/infys_dp_superficie_validacion.csv
"""

from __future__ import annotations

import re
import unicodedata
from pathlib import Path
from typing import Optional, List, Dict, Tuple

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

ARCHIVO_SUPERFICIE_BASE = "1_Superficie.xlsx"
HOJA_SUPERFICIE_BASE = "Superficie"

ARCHIVO_SUPERFICIE_2015_2020 = "Superficie_forestal_INFyS-2015-2020_Tablas_v4_27042023.xlsx"
HOJA_SUPERFICIE_2015_2020_ESTATAL = "Sup-ftal_estatal"
HOJA_SUPERFICIE_2015_2020_DETALLE = "BaseDatos_Superficie-SVII-MGM21"

OUT_SUPERFICIE_BASE = DATASETS_DIR / "infys_superficie_base_limpio.csv"
OUT_SUPERFICIE_2015_2020_ESTATAL = DATASETS_DIR / "infys_superficie_2015_2020_estatal_limpio.csv"
OUT_SUPERFICIE_2015_2020_DETALLE = DATASETS_DIR / "infys_superficie_2015_2020_detalle_limpio.csv"

OUT_VALIDACION = REPORTS_DIR / "infys_dp_superficie_validacion.csv"


CATALOGO_ENTIDADES = {
    "01": "AGUASCALIENTES",
    "02": "BAJA CALIFORNIA",
    "03": "BAJA CALIFORNIA SUR",
    "04": "CAMPECHE",
    "05": "COAHUILA DE ZARAGOZA",
    "06": "COLIMA",
    "07": "CHIAPAS",
    "08": "CHIHUAHUA",
    "09": "CIUDAD DE MEXICO",
    "10": "DURANGO",
    "11": "GUANAJUATO",
    "12": "GUERRERO",
    "13": "HIDALGO",
    "14": "JALISCO",
    "15": "ESTADO DE MEXICO",
    "16": "MICHOACAN DE OCAMPO",
    "17": "MORELOS",
    "18": "NAYARIT",
    "19": "NUEVO LEON",
    "20": "OAXACA",
    "21": "PUEBLA",
    "22": "QUERETARO",
    "23": "QUINTANA ROO",
    "24": "SAN LUIS POTOSI",
    "25": "SINALOA",
    "26": "SONORA",
    "27": "TABASCO",
    "28": "TAMAULIPAS",
    "29": "TLAXCALA",
    "30": "VERACRUZ DE IGNACIO DE LA LLAVE",
    "31": "YUCATAN",
    "32": "ZACATECAS",
}

ALIAS_ENTIDADES = {
    "MEXICO": "ESTADO DE MEXICO",
    "EDO DE MEXICO": "ESTADO DE MEXICO",
    "EDO. DE MEXICO": "ESTADO DE MEXICO",
    "ESTADO DE MÉXICO": "ESTADO DE MEXICO",
    "MICHOACAN": "MICHOACAN DE OCAMPO",
    "MICHOACÁN": "MICHOACAN DE OCAMPO",
    "COAHUILA": "COAHUILA DE ZARAGOZA",
    "VERACRUZ": "VERACRUZ DE IGNACIO DE LA LLAVE",
    "DISTRITO FEDERAL": "CIUDAD DE MEXICO",
    "CDMX": "CIUDAD DE MEXICO",
    "CIUDAD DE MÉXICO": "CIUDAD DE MEXICO",
    "QUERÉTARO": "QUERETARO",
    "SAN LUIS POTOSÍ": "SAN LUIS POTOSI",
    "NUEVO LEÓN": "NUEVO LEON",
    "YUCATÁN": "YUCATAN",
}


# =========================================================
# 2) UTILIDADES GENERALES
# =========================================================

def quitar_acentos(valor: object) -> str:
    texto = "" if pd.isna(valor) else str(valor)
    texto = unicodedata.normalize("NFKD", texto)
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    return texto


def normalizar_texto(valor: object) -> str:
    texto = quitar_acentos(valor)
    texto = texto.strip().upper()
    texto = re.sub(r"\s+", " ", texto)
    return texto


def normalizar_columna(nombre: object) -> str:
    texto = quitar_acentos(nombre)
    texto = texto.strip().lower()
    texto = re.sub(r"[^a-z0-9]+", "_", texto)
    texto = re.sub(r"_+", "_", texto)
    return texto.strip("_")


def normalizar_columnas(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out.columns = [normalizar_columna(c) for c in out.columns]
    return out


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


def convertir_numero(serie: pd.Series) -> pd.Series:
    s = serie.astype(str)
    s = s.str.replace(",", "", regex=False)
    s = s.str.replace(" ", "", regex=False)
    s = s.str.strip()
    s = s.replace(
        {
            "": pd.NA,
            "nan": pd.NA,
            "NaN": pd.NA,
            "None": pd.NA,
            "NAN": pd.NA,
            "NULL": pd.NA,
            "NULO": pd.NA,
            "-": pd.NA,
            "S/D": pd.NA,
            "SD": pd.NA,
        }
    )
    return pd.to_numeric(s, errors="coerce")


def normalizar_cve_ent(serie: pd.Series) -> pd.Series:
    s = serie.astype(str).str.extract(r"(\d+)")[0]
    s = s.where(s.notna(), pd.NA)
    s = s.str.zfill(2)

    validas = set(CATALOGO_ENTIDADES.keys())
    s = s.where(s.isin(validas), pd.NA)

    return s


def normalizar_nom_ent(serie: pd.Series) -> pd.Series:
    s = serie.map(normalizar_texto)
    s = s.replace(ALIAS_ENTIDADES)
    s = s.replace({"": pd.NA, "NAN": pd.NA, "NONE": pd.NA})
    return s


def nombre_entidad_desde_cve(cve_ent: object) -> Optional[str]:
    if pd.isna(cve_ent):
        return None

    clave = str(cve_ent).zfill(2)
    return CATALOGO_ENTIDADES.get(clave)


def cve_ent_desde_nombre(nom_ent: object) -> Optional[str]:
    if pd.isna(nom_ent):
        return None

    nombre = normalizar_texto(nom_ent)
    nombre = ALIAS_ENTIDADES.get(nombre, nombre)

    invertido = {v: k for k, v in CATALOGO_ENTIDADES.items()}
    return invertido.get(nombre)


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


def columna_requerida(df: pd.DataFrame, candidatos: List[str], etiqueta: str) -> str:
    col = detectar_columna(list(df.columns), candidatos)

    if col is None:
        raise ValueError(
            f"No se detectó columna requerida para '{etiqueta}'. "
            f"Candidatos: {candidatos}. Columnas disponibles: {list(df.columns)}"
        )

    return col


def leer_excel(ruta: Path, hoja: str) -> Tuple[pd.DataFrame, pd.DataFrame]:
    xls = pd.ExcelFile(ruta)

    if hoja not in xls.sheet_names:
        raise ValueError(
            f"No se encontró la hoja '{hoja}' en {ruta.name}. "
            f"Hojas disponibles: {xls.sheet_names}"
        )

    df_raw_original = pd.read_excel(ruta, sheet_name=hoja)
    df_raw = limpiar_filas_columnas_vacias(df_raw_original)
    df_raw = normalizar_columnas(df_raw)

    return df_raw_original, df_raw


def limpiar_categoria(serie: pd.Series) -> pd.Series:
    s = serie.map(normalizar_texto)
    s = s.replace({"": pd.NA, "NAN": pd.NA, "NONE": pd.NA})
    return s


def agregar_metadatos_origen(
    df: pd.DataFrame,
    archivo_origen: str,
    hoja_origen: str,
    ciclo_infys: str,
) -> pd.DataFrame:
    out = df.copy()
    out["ciclo_infys"] = ciclo_infys
    out["archivo_origen"] = archivo_origen
    out["hoja_origen"] = hoja_origen
    return out


# =========================================================
# 3) VALIDACIÓN
# =========================================================

def crear_registro_validacion(
    nombre_dataset: str,
    archivo_origen: str,
    hoja_origen: str,
    filas_leidas: int,
    columnas_leidas: int,
    df_limpio: pd.DataFrame,
    columna_superficie: Optional[str],
    columnas_clave: List[str],
) -> Dict[str, object]:

    registro = {
        "dataset": nombre_dataset,
        "archivo_origen": archivo_origen,
        "hoja_origen": hoja_origen,
        "filas_leidas": filas_leidas,
        "columnas_leidas": columnas_leidas,
        "filas_finales": len(df_limpio),
        "columnas_finales": len(df_limpio.columns),
        "filas_eliminadas": filas_leidas - len(df_limpio),
        "duplicados_exactos_finales": int(df_limpio.duplicated().sum()),
        "cve_ent_nulos": int(df_limpio["cve_ent"].isna().sum()) if "cve_ent" in df_limpio.columns else None,
        "nom_ent_nulos": int(df_limpio["nom_ent"].isna().sum()) if "nom_ent" in df_limpio.columns else None,
        "cve_ent_distintas": int(df_limpio["cve_ent"].nunique(dropna=True)) if "cve_ent" in df_limpio.columns else None,
        "claves_fuera_catalogo": None,
        "superficie_nula": None,
        "superficie_menor_igual_cero": None,
        "superficie_total_ha": None,
        "duplicados_por_clave": None,
        "estado_validacion": "ok",
        "observaciones": "",
    }

    observaciones = []

    if "cve_ent" in df_limpio.columns:
        validas = set(CATALOGO_ENTIDADES.keys())
        fuera = df_limpio.loc[
            df_limpio["cve_ent"].notna() & ~df_limpio["cve_ent"].isin(validas),
            "cve_ent",
        ]
        registro["claves_fuera_catalogo"] = int(len(fuera))

        if len(fuera) > 0:
            observaciones.append("existen_claves_entidad_fuera_catalogo")

    if columna_superficie and columna_superficie in df_limpio.columns:
        registro["superficie_nula"] = int(df_limpio[columna_superficie].isna().sum())
        registro["superficie_menor_igual_cero"] = int((df_limpio[columna_superficie] <= 0).sum())
        registro["superficie_total_ha"] = float(df_limpio[columna_superficie].sum())

        if registro["superficie_nula"] > 0:
            observaciones.append("existen_superficies_nulas")

        if registro["superficie_menor_igual_cero"] > 0:
            observaciones.append("existen_superficies_menor_igual_cero")

    if columnas_clave:
        columnas_existentes = [c for c in columnas_clave if c in df_limpio.columns]

        if columnas_existentes:
            registro["duplicados_por_clave"] = int(df_limpio.duplicated(subset=columnas_existentes).sum())

            if registro["duplicados_por_clave"] > 0:
                observaciones.append("existen_duplicados_por_clave")

    if registro["duplicados_exactos_finales"] > 0:
        observaciones.append("existen_duplicados_exactos_finales")

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
        "filas_leidas": 0,
        "columnas_leidas": 0,
        "filas_finales": 0,
        "columnas_finales": 0,
        "filas_eliminadas": 0,
        "duplicados_exactos_finales": None,
        "cve_ent_nulos": None,
        "nom_ent_nulos": None,
        "cve_ent_distintas": None,
        "claves_fuera_catalogo": None,
        "superficie_nula": None,
        "superficie_menor_igual_cero": None,
        "superficie_total_ha": None,
        "duplicados_por_clave": None,
        "estado_validacion": "error",
        "observaciones": mensaje,
    }


# =========================================================
# 4) DP - 1_SUPERFICIE.XLSX
# =========================================================

def preparar_superficie_base() -> Tuple[Optional[pd.DataFrame], Dict[str, object]]:
    nombre_dataset = "infys_superficie_base_limpio"

    ruta = buscar_archivo(ARCHIVO_SUPERFICIE_BASE)

    if ruta is None:
        return None, registro_error(
            nombre_dataset,
            ARCHIVO_SUPERFICIE_BASE,
            HOJA_SUPERFICIE_BASE,
            "archivo_no_encontrado",
        )

    print(f"Procesando: {ruta.name} | hoja: {HOJA_SUPERFICIE_BASE}")

    df_original, df_raw = leer_excel(ruta, HOJA_SUPERFICIE_BASE)

    columnas_requeridas = {
        "cve_ent": ["cve_ent"],
        "nom_ent": ["nom_ent"],
        "cve_eco": ["cve_eco"],
        "ecosistema": ["ecosistema"],
        "cve_for": ["cve_for"],
        "formacion": ["formacion"],
        "descripcion_s6": ["descrip_s6", "descripcion_s6"],
        "desveg_s6": ["desveg_s6"],
        "fase_vs_s6": ["fase_vs_s6"],
        "superficie_ha": ["ha", "superficie_ha", "superficie"],
    }

    mapa = {
        salida: columna_requerida(df_raw, candidatos, salida)
        for salida, candidatos in columnas_requeridas.items()
    }

    out = pd.DataFrame()
    out["cve_ent"] = normalizar_cve_ent(df_raw[mapa["cve_ent"]])
    out["nom_ent"] = normalizar_nom_ent(df_raw[mapa["nom_ent"]])
    out["nom_ent_catalogo"] = out["cve_ent"].map(nombre_entidad_desde_cve)

    out["cve_eco"] = convertir_numero(df_raw[mapa["cve_eco"]]).astype("Int64")
    out["ecosistema"] = limpiar_categoria(df_raw[mapa["ecosistema"]])
    out["cve_for"] = convertir_numero(df_raw[mapa["cve_for"]]).astype("Int64")
    out["formacion"] = limpiar_categoria(df_raw[mapa["formacion"]])
    out["descripcion_s6"] = limpiar_categoria(df_raw[mapa["descripcion_s6"]])
    out["desveg_s6"] = limpiar_categoria(df_raw[mapa["desveg_s6"]])
    out["fase_vs_s6"] = limpiar_categoria(df_raw[mapa["fase_vs_s6"]])
    out["superficie_ha"] = convertir_numero(df_raw[mapa["superficie_ha"]])

    out = agregar_metadatos_origen(
        out,
        archivo_origen=ARCHIVO_SUPERFICIE_BASE,
        hoja_origen=HOJA_SUPERFICIE_BASE,
        ciclo_infys="no_especificado",
    )

    out = out.dropna(subset=["cve_ent", "nom_ent", "superficie_ha"]).copy()
    out = out[out["superficie_ha"] > 0].copy()
    out = out.drop_duplicates().copy()

    out = out[
        [
            "cve_ent",
            "nom_ent",
            "nom_ent_catalogo",
            "cve_eco",
            "ecosistema",
            "cve_for",
            "formacion",
            "descripcion_s6",
            "desveg_s6",
            "fase_vs_s6",
            "superficie_ha",
            "ciclo_infys",
            "archivo_origen",
            "hoja_origen",
        ]
    ].sort_values(
        ["cve_ent", "cve_eco", "cve_for", "descripcion_s6", "desveg_s6", "fase_vs_s6"]
    ).reset_index(drop=True)

    validacion = crear_registro_validacion(
        nombre_dataset=nombre_dataset,
        archivo_origen=ARCHIVO_SUPERFICIE_BASE,
        hoja_origen=HOJA_SUPERFICIE_BASE,
        filas_leidas=len(df_original),
        columnas_leidas=len(df_original.columns),
        df_limpio=out,
        columna_superficie="superficie_ha",
        columnas_clave=[
            "cve_ent",
            "cve_eco",
            "cve_for",
            "descripcion_s6",
            "desveg_s6",
            "fase_vs_s6",
        ],
    )

    return out, validacion


# =========================================================
# 5) DP - SUPERFICIE 2015-2020 ESTATAL
# =========================================================

def preparar_superficie_2015_2020_estatal() -> Tuple[Optional[pd.DataFrame], Dict[str, object]]:
    nombre_dataset = "infys_superficie_2015_2020_estatal_limpio"

    ruta = buscar_archivo(ARCHIVO_SUPERFICIE_2015_2020)

    if ruta is None:
        return None, registro_error(
            nombre_dataset,
            ARCHIVO_SUPERFICIE_2015_2020,
            HOJA_SUPERFICIE_2015_2020_ESTATAL,
            "archivo_no_encontrado",
        )

    print(f"Procesando: {ruta.name} | hoja: {HOJA_SUPERFICIE_2015_2020_ESTATAL}")

    df_original, df_raw = leer_excel(ruta, HOJA_SUPERFICIE_2015_2020_ESTATAL)

    col_cve = detectar_columna(
        list(df_raw.columns),
        ["cve_ent", "cve_estado", "clave_estado", "entidad"],
    )

    col_nom = detectar_columna(
        list(df_raw.columns),
        ["nom_ent", "estado", "nombre_estado", "entidad_federativa", "nomgeo"],
    )

    col_superficie = columna_requerida(
        df_raw,
        [
            "superficie_forestal_total",
            "superficie_total_estatal",
            "superfice_total_estatal",
            "superficie_forestal",
            "superficie",
        ],
        "superficie_forestal_total_ha",
    )

    if col_cve is None and col_nom is None:
        raise ValueError(
            f"No se detectó columna de entidad en {HOJA_SUPERFICIE_2015_2020_ESTATAL}. "
            f"Columnas disponibles: {list(df_raw.columns)}"
        )

    out = pd.DataFrame()

    if col_cve is not None:
        out["cve_ent"] = normalizar_cve_ent(df_raw[col_cve])
    else:
        out["cve_ent"] = pd.NA

    if col_nom is not None:
        out["nom_ent"] = normalizar_nom_ent(df_raw[col_nom])
    else:
        out["nom_ent"] = pd.NA

    if out["cve_ent"].isna().any() and out["nom_ent"].notna().any():
        out.loc[out["cve_ent"].isna(), "cve_ent"] = out.loc[
            out["cve_ent"].isna(), "nom_ent"
        ].map(cve_ent_desde_nombre)

    if out["nom_ent"].isna().any() and out["cve_ent"].notna().any():
        out.loc[out["nom_ent"].isna(), "nom_ent"] = out.loc[
            out["nom_ent"].isna(), "cve_ent"
        ].map(nombre_entidad_desde_cve)

    out["nom_ent_catalogo"] = out["cve_ent"].map(nombre_entidad_desde_cve)
    out["superficie_forestal_total_ha"] = convertir_numero(df_raw[col_superficie])

    out = agregar_metadatos_origen(
        out,
        archivo_origen=ARCHIVO_SUPERFICIE_2015_2020,
        hoja_origen=HOJA_SUPERFICIE_2015_2020_ESTATAL,
        ciclo_infys="2015-2020",
    )

    nombres_invalidos = {
        "TOTAL",
        "NACIONAL",
        "MEXICO",
        "ESTADOS UNIDOS MEXICANOS",
        "SUPERFICIE FORESTAL TOTAL",
    }

    out = out[~out["nom_ent"].isin(nombres_invalidos)].copy()
    out = out.dropna(subset=["cve_ent", "nom_ent", "superficie_forestal_total_ha"]).copy()
    out = out[out["superficie_forestal_total_ha"] > 0].copy()
    out = out.drop_duplicates().copy()

    out = (
        out.groupby(
            [
                "cve_ent",
                "nom_ent",
                "nom_ent_catalogo",
                "ciclo_infys",
                "archivo_origen",
                "hoja_origen",
            ],
            as_index=False,
            dropna=False,
        )["superficie_forestal_total_ha"]
        .sum()
    )

    out = out[
        [
            "cve_ent",
            "nom_ent",
            "nom_ent_catalogo",
            "superficie_forestal_total_ha",
            "ciclo_infys",
            "archivo_origen",
            "hoja_origen",
        ]
    ].sort_values("cve_ent").reset_index(drop=True)

    validacion = crear_registro_validacion(
        nombre_dataset=nombre_dataset,
        archivo_origen=ARCHIVO_SUPERFICIE_2015_2020,
        hoja_origen=HOJA_SUPERFICIE_2015_2020_ESTATAL,
        filas_leidas=len(df_original),
        columnas_leidas=len(df_original.columns),
        df_limpio=out,
        columna_superficie="superficie_forestal_total_ha",
        columnas_clave=["cve_ent"],
    )

    return out, validacion


# =========================================================
# 6) DP - SUPERFICIE 2015-2020 DETALLE
# =========================================================

def preparar_superficie_2015_2020_detalle() -> Tuple[Optional[pd.DataFrame], Dict[str, object]]:
    nombre_dataset = "infys_superficie_2015_2020_detalle_limpio"

    ruta = buscar_archivo(ARCHIVO_SUPERFICIE_2015_2020)

    if ruta is None:
        return None, registro_error(
            nombre_dataset,
            ARCHIVO_SUPERFICIE_2015_2020,
            HOJA_SUPERFICIE_2015_2020_DETALLE,
            "archivo_no_encontrado",
        )

    print(f"Procesando: {ruta.name} | hoja: {HOJA_SUPERFICIE_2015_2020_DETALLE}")

    df_original, df_raw = leer_excel(ruta, HOJA_SUPERFICIE_2015_2020_DETALLE)

    col_cve = detectar_columna(
        list(df_raw.columns),
        ["cve_ent", "cve_estado", "clave_estado", "entidad"],
    )

    col_nom = detectar_columna(
        list(df_raw.columns),
        ["nom_ent", "estado", "nombre_estado", "entidad_federativa", "nomgeo"],
    )

    col_superficie = columna_requerida(
        df_raw,
        ["superficie_ha", "sup_ha", "superficie", "ha", "hectareas"],
        "superficie_ha",
    )

    col_ecosistema = detectar_columna(
        list(df_raw.columns),
        ["ecosistema", "tipo_ecosistema"],
    )

    col_formacion = detectar_columna(
        list(df_raw.columns),
        ["formacion", "formacion_forestal"],
    )

    col_categoria = detectar_columna(
        list(df_raw.columns),
        [
            "tipo_de_vegetacion",
            "vegetacion",
            "cobertura",
            "clase",
            "descripcion",
            "desveg",
            "descrip",
            "fase",
        ],
    )

    if col_cve is None and col_nom is None:
        raise ValueError(
            f"No se detectó columna de entidad en {HOJA_SUPERFICIE_2015_2020_DETALLE}. "
            f"Columnas disponibles: {list(df_raw.columns)}"
        )

    out = pd.DataFrame()

    if col_cve is not None:
        out["cve_ent"] = normalizar_cve_ent(df_raw[col_cve])
    else:
        out["cve_ent"] = pd.NA

    if col_nom is not None:
        out["nom_ent"] = normalizar_nom_ent(df_raw[col_nom])
    else:
        out["nom_ent"] = pd.NA

    if out["cve_ent"].isna().any() and out["nom_ent"].notna().any():
        out.loc[out["cve_ent"].isna(), "cve_ent"] = out.loc[
            out["cve_ent"].isna(), "nom_ent"
        ].map(cve_ent_desde_nombre)

    if out["nom_ent"].isna().any() and out["cve_ent"].notna().any():
        out.loc[out["nom_ent"].isna(), "nom_ent"] = out.loc[
            out["nom_ent"].isna(), "cve_ent"
        ].map(nombre_entidad_desde_cve)

    out["nom_ent_catalogo"] = out["cve_ent"].map(nombre_entidad_desde_cve)

    if col_ecosistema is not None:
        out["ecosistema"] = limpiar_categoria(df_raw[col_ecosistema])
    else:
        out["ecosistema"] = pd.NA

    if col_formacion is not None:
        out["formacion"] = limpiar_categoria(df_raw[col_formacion])
    else:
        out["formacion"] = pd.NA

    if col_categoria is not None:
        out["categoria_superficie"] = limpiar_categoria(df_raw[col_categoria])
    else:
        out["categoria_superficie"] = pd.NA

    out["superficie_ha"] = convertir_numero(df_raw[col_superficie])

    out = agregar_metadatos_origen(
        out,
        archivo_origen=ARCHIVO_SUPERFICIE_2015_2020,
        hoja_origen=HOJA_SUPERFICIE_2015_2020_DETALLE,
        ciclo_infys="2015-2020",
    )

    out = out.dropna(subset=["cve_ent", "nom_ent", "superficie_ha"]).copy()
    out = out[out["superficie_ha"] > 0].copy()
    out = out.drop_duplicates().copy()

    out = out[
        [
            "cve_ent",
            "nom_ent",
            "nom_ent_catalogo",
            "ecosistema",
            "formacion",
            "categoria_superficie",
            "superficie_ha",
            "ciclo_infys",
            "archivo_origen",
            "hoja_origen",
        ]
    ].sort_values(
        ["cve_ent", "ecosistema", "formacion", "categoria_superficie"]
    ).reset_index(drop=True)

    validacion = crear_registro_validacion(
        nombre_dataset=nombre_dataset,
        archivo_origen=ARCHIVO_SUPERFICIE_2015_2020,
        hoja_origen=HOJA_SUPERFICIE_2015_2020_DETALLE,
        filas_leidas=len(df_original),
        columnas_leidas=len(df_original.columns),
        df_limpio=out,
        columna_superficie="superficie_ha",
        columnas_clave=[],
    )

    return out, validacion


# =========================================================
# 7) GUARDADO Y PIPELINE PRINCIPAL
# =========================================================

def guardar_dataset(df: Optional[pd.DataFrame], ruta_salida: Path, nombre: str) -> None:
    if df is None:
        print(f"No se generó {nombre}.")
        return

    df.to_csv(ruta_salida, index=False, encoding="utf-8-sig")
    print(f"Dataset generado: {ruta_salida}")


def ejecutar_bloque(nombre: str, funcion):
    try:
        df, validacion = funcion()
        return df, validacion
    except Exception as e:
        print(f"ERROR en {nombre}: {e}")
        return None, registro_error(
            nombre_dataset=nombre,
            archivo_origen="",
            hoja_origen="",
            mensaje=str(e),
        )


def main() -> None:
    print("\nINFyS | Data Preparation - Superficie forestal")
    print(f"Directorio raw: {RAW_DIR}")
    print(f"Directorio datasets: {DATASETS_DIR}")
    print(f"Directorio reports: {REPORTS_DIR}")

    if not RAW_DIR.exists():
        raise FileNotFoundError(f"No existe RAW_DIR: {RAW_DIR}")

    validaciones = []

    superficie_base, val_base = ejecutar_bloque(
        "infys_superficie_base_limpio",
        preparar_superficie_base,
    )
    guardar_dataset(
        superficie_base,
        OUT_SUPERFICIE_BASE,
        "infys_superficie_base_limpio",
    )
    validaciones.append(val_base)

    superficie_estatal, val_estatal = ejecutar_bloque(
        "infys_superficie_2015_2020_estatal_limpio",
        preparar_superficie_2015_2020_estatal,
    )
    guardar_dataset(
        superficie_estatal,
        OUT_SUPERFICIE_2015_2020_ESTATAL,
        "infys_superficie_2015_2020_estatal_limpio",
    )
    validaciones.append(val_estatal)

    superficie_detalle, val_detalle = ejecutar_bloque(
        "infys_superficie_2015_2020_detalle_limpio",
        preparar_superficie_2015_2020_detalle,
    )
    guardar_dataset(
        superficie_detalle,
        OUT_SUPERFICIE_2015_2020_DETALLE,
        "infys_superficie_2015_2020_detalle_limpio",
    )
    validaciones.append(val_detalle)

    df_validacion = pd.DataFrame(validaciones)
    df_validacion.to_csv(OUT_VALIDACION, index=False, encoding="utf-8-sig")

    print(f"Reporte de validación generado: {OUT_VALIDACION}")

    print("\n=== RESUMEN DP SUPERFICIE INFyS ===")

    for registro in validaciones:
        print(
            f"- {registro['dataset']}: "
            f"{registro['filas_finales']} filas finales | "
            f"estado={registro['estado_validacion']}"
        )

    print("\nProceso terminado.")


if __name__ == "__main__":
    main()