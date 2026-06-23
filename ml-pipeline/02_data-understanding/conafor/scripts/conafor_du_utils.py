from __future__ import annotations

import csv
import re
from pathlib import Path
from typing import Any, Optional

import pandas as pd

# ============================================================
# UTILIDADES GENERALES
# ============================================================

def normalizar_texto(texto: Any) -> str:
    """Normaliza texto para comparación de columnas y nombres."""
    if texto is None:
        return ""
    s = str(texto).strip().lower()
    reemplazos = {
        "á": "a", "é": "e", "í": "i", "ó": "o", "ú": "u",
        "ä": "a", "ë": "e", "ï": "i", "ö": "o", "ü": "u",
        "ñ": "n",
    }
    for k, v in reemplazos.items():
        s = s.replace(k, v)
    s = re.sub(r"[^a-z0-9]+", "_", s)
    s = re.sub(r"_+", "_", s).strip("_")
    return s


def bool_si_no(valor: bool) -> str:
    return "si" if bool(valor) else "no"


def extraer_rango_nominal_desde_nombre(nombre: str) -> tuple[Optional[str], Optional[str]]:
    """
    Extrae cobertura nominal desde el nombre del archivo.

    Soporta:
      - YYYY-MM-DD_YYYY-MM-DD
      - YYYY-MM-DD-YYYY-MM-DD
      - YYYY_YYYY
      - YYYY-YYYY
      - un solo año YYYY
    """
    nombre = str(nombre)

    # 1) Rango con fechas completas: 2001-01-01_2025-12-31
    m_fechas = re.search(
        r"(19\d{2}|20\d{2})[-_](\d{2})[-_](\d{2})\D+"
        r"(19\d{2}|20\d{2})[-_](\d{2})[-_](\d{2})",
        nombre
    )
    if m_fechas:
        y1, m1, d1, y2, m2, d2 = m_fechas.groups()
        return f"{y1}-{m1}-{d1}", f"{y2}-{m2}-{d2}"

    # 2) Rango simple de años: 2015-2024 o 2015_2024
    m_rango = re.search(r"(19\d{2}|20\d{2})\s*[-_]\s*(19\d{2}|20\d{2})", nombre)
    if m_rango:
        y1, y2 = m_rango.group(1), m_rango.group(2)
        return f"{y1}-01-01", f"{y2}-12-31"

    # 3) Año único: incendios_2023
    m_unico = re.search(r"(19\d{2}|20\d{2})", nombre)
    if m_unico:
        y = m_unico.group(1)
        return f"{y}-01-01", f"{y}-12-31"

    return None, None


def serializar_valores(valores: list[Any], max_chars: int = 140) -> str:
    limpios = []
    for v in valores:
        if pd.isna(v):
            continue
        txt = str(v).strip()
        if not txt:
            continue
        limpios.append(txt)

    unicos: list[str] = []
    vistos: set[str] = set()
    for x in limpios:
        if x not in vistos:
            unicos.append(x)
            vistos.add(x)

    texto = " | ".join(unicos[:5])
    if len(texto) > max_chars:
        texto = texto[: max_chars - 3] + "..."
    return texto


# ============================================================
# LIMPIEZA DE VALORES FALTANTES
# ============================================================

def limpiar_valores_faltantes(serie: pd.Series) -> pd.Series:
    s = serie.copy()
    if pd.api.types.is_string_dtype(s) or s.dtype == "object":
        s = s.astype("string").str.strip()
        s = s.replace({
            "": pd.NA,
            "nan": pd.NA,
            "nat": pd.NA,
            "none": pd.NA,
            "null": pd.NA,
            "n/a": pd.NA,
            "na": pd.NA,
            "s/d": pd.NA,
            "sin dato": pd.NA,
            "sin_dato": pd.NA,
        })
    return s


# ============================================================
# PARSEO DE FECHAS
# ============================================================

def parsear_fechas_serie(serie: pd.Series) -> pd.Series:
    """
    Parsea fechas de forma conservadora y sin warnings.
    Formatos soportados:
      - YYYY-MM-DD
      - YYYY-MM-DD HH:MM:SS
      - DD/MM/YYYY
      - DD-MM-YYYY
      - YYYY/MM/DD
      - datetime nativo
    """
    s = limpiar_valores_faltantes(serie)

    if pd.api.types.is_datetime64_any_dtype(s):
        return pd.to_datetime(s, errors="coerce")

    s = s.astype("string").str.strip()
    fechas = pd.Series(pd.NaT, index=s.index, dtype="datetime64[ns]")

    mask_iso = s.str.match(r"^\d{4}-\d{2}-\d{2}$", na=False)
    if mask_iso.any():
        fechas.loc[mask_iso] = pd.to_datetime(
            s.loc[mask_iso], errors="coerce", format="%Y-%m-%d"
        )

    mask_iso_dt = s.str.match(r"^\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}$", na=False)
    if mask_iso_dt.any():
        fechas.loc[mask_iso_dt] = pd.to_datetime(
            s.loc[mask_iso_dt], errors="coerce", format="%Y-%m-%d %H:%M:%S"
        )

    mask_dmy_slash = s.str.match(r"^\d{1,2}/\d{1,2}/\d{4}$", na=False)
    if mask_dmy_slash.any():
        fechas.loc[mask_dmy_slash] = pd.to_datetime(
            s.loc[mask_dmy_slash], errors="coerce", format="%d/%m/%Y"
        )

    mask_dmy_dash = s.str.match(r"^\d{1,2}-\d{1,2}-\d{4}$", na=False)
    if mask_dmy_dash.any():
        fechas.loc[mask_dmy_dash] = pd.to_datetime(
            s.loc[mask_dmy_dash], errors="coerce", format="%d-%m-%Y"
        )

    mask_ymd_slash = s.str.match(r"^\d{4}/\d{1,2}/\d{1,2}$", na=False)
    if mask_ymd_slash.any():
        fechas.loc[mask_ymd_slash] = pd.to_datetime(
            s.loc[mask_ymd_slash], errors="coerce", format="%Y/%m/%d"
        )

    return fechas


# ============================================================
# LECTURA DE ARCHIVOS
# ============================================================

def detectar_hoja_principal_excel(xls: pd.ExcelFile) -> str:
    """Selecciona la hoja más probable para análisis."""
    prioridades = ["incend", "estad", "dato", "histor", "reporte", "base", "sheet1", "hoja1"]
    hojas = xls.sheet_names
    hojas_norm = [(h, normalizar_texto(h)) for h in hojas]

    for prioridad in prioridades:
        for original, norm in hojas_norm:
            if prioridad in norm:
                return original

    return hojas[0]


def detectar_encabezado_excel(path_excel: Path, hoja: str, max_filas: int = 15) -> int:
    """Detecta la fila de encabezado con heurística de tokens relevantes."""
    muestra = pd.read_excel(path_excel, sheet_name=hoja, header=None, nrows=max_filas)

    mejor_fila = 0
    mejor_puntaje = -1

    tokens_utiles = {
        "fecha", "ano", "año", "anio", "estado", "municipio", "latitud", "longitud",
        "superficie", "incendio", "causa", "region", "predio", "termino", "inicio",
    }

    for idx in range(len(muestra)):
        fila = muestra.iloc[idx].tolist()
        fila_txt = [normalizar_texto(x) for x in fila if pd.notna(x)]

        if not fila_txt:
            continue

        no_vacios = len(fila_txt)
        puntaje_tokens = sum(
            1 for x in fila_txt if x in tokens_utiles or any(t in x for t in tokens_utiles)
        )
        puntaje = no_vacios + 3 * puntaje_tokens

        if puntaje > mejor_puntaje:
            mejor_puntaje = puntaje
            mejor_fila = idx

    return mejor_fila


def leer_excel_limpio(path_excel: Path) -> tuple[pd.DataFrame, dict]:
    """Lee un Excel y devuelve DataFrame con columnas normalizadas y metadatos."""
    xls = pd.ExcelFile(path_excel)
    hoja = detectar_hoja_principal_excel(xls)
    header_row = detectar_encabezado_excel(path_excel, hoja)

    df = pd.read_excel(path_excel, sheet_name=hoja, header=header_row)
    df.columns = [normalizar_texto(c) for c in df.columns]
    df = df.dropna(axis=1, how="all")

    meta = {
        "hojas_detectadas": xls.sheet_names,
        "hoja_usada": hoja,
        "fila_encabezado": header_row,
        "encoding_usado": None,
        "separador_usado": None,
    }
    return df, meta


def detectar_separador_csv(path_csv: Path, encoding: str) -> str:
    """
    Intenta detectar el separador usando csv.Sniffer.
    Si falla, usa coma como valor por defecto.
    """
    try:
        with open(path_csv, "r", encoding=encoding, newline="") as f:
            muestra = f.read(8192)
        dialect = csv.Sniffer().sniff(muestra, delimiters=",;|\t")
        return dialect.delimiter
    except Exception:
        return ","


def leer_csv_limpio(path_csv: Path) -> tuple[pd.DataFrame, dict]:
    """
    Lee un CSV probando encodings comunes y detectando separador.
    Orden de encodings pensado para evitar que latin-1 capture archivos UTF-8 válidos.
    """
    encodings = ["utf-8-sig", "utf-8", "cp1252", "latin-1"]
    ultimo_error: Optional[Exception] = None

    for enc in encodings:
        try:
            sep = detectar_separador_csv(path_csv, enc)
            df = pd.read_csv(
                path_csv,
                encoding=enc,
                sep=sep,
                low_memory=False,
            )

            df.columns = [normalizar_texto(c) for c in df.columns]
            df = df.dropna(axis=1, how="all")

            meta = {
                "encoding_usado": enc,
                "separador_usado": sep,
                "hoja_usada": None,
            }
            return df, meta

        except UnicodeDecodeError as e:
            ultimo_error = e
            continue
        except pd.errors.ParserError as e:
            ultimo_error = e
            continue
        except Exception as e:
            ultimo_error = e
            continue

    raise ValueError(
        f"No se pudo leer el CSV: {path_csv}. "
        f"Último error observado: {ultimo_error}"
    )


# ============================================================
# DESCUBRIMIENTO DE FUENTES
# ============================================================

def _inferir_grupo_fuente(nombre: str, tipo: str) -> str:
    n = normalizar_texto(nombre)

    if "1970" in n and "2024" in n:
        return "historico_agregado_1970_2024"

    if tipo == "shp":
        if "historico" in n and "incendios" in n and "activos" in n:
            return "historico_shp_evento_multianual"

        rango_ini, rango_fin = extraer_rango_nominal_desde_nombre(nombre)
        if rango_ini and rango_fin:
            y1 = int(rango_ini[:4])
            y2 = int(rango_fin[:4])
            if y2 - y1 > 1:
                return "historico_shp_evento_multianual"

        return "serie_anual_shp_evento"

    if tipo == "xlsx":
        return "excel_evento"

    if tipo == "csv":
        return "csv_evento"

    return "desconocido"


def descubrir_fuentes_conafor(raw_dir: Path) -> list[dict]:
    """
    Escanea raw_dir buscando archivos .shp, .xlsx y .csv.
    Usa rglob para permitir subcarpetas.
    """
    fuentes = []

    for path_shp in sorted(raw_dir.rglob("*.shp")):
        fuentes.append({
            "tipo": "shp",
            "path": path_shp,
            "nombre_fuente": path_shp.stem,
            "grupo_fuente": _inferir_grupo_fuente(path_shp.stem, "shp"),
        })

    for path_xlsx in sorted(raw_dir.rglob("*.xlsx")):
        fuentes.append({
            "tipo": "xlsx",
            "path": path_xlsx,
            "nombre_fuente": path_xlsx.stem,
            "grupo_fuente": _inferir_grupo_fuente(path_xlsx.stem, "xlsx"),
        })

    for path_csv in sorted(raw_dir.rglob("*.csv")):
        fuentes.append({
            "tipo": "csv",
            "path": path_csv,
            "nombre_fuente": path_csv.stem,
            "grupo_fuente": _inferir_grupo_fuente(path_csv.stem, "csv"),
        })

    unicas: dict[str, dict] = {}
    for f in fuentes:
        unicas[str(f["path"].resolve())] = f

    return list(unicas.values())