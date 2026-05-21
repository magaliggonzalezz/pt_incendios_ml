from __future__ import annotations

from pathlib import Path
from typing import Any, Optional

import pandas as pd

try:
    import geopandas as gpd
except ImportError:
    gpd = None

from conafor_du_utils import (
    normalizar_texto,
    limpiar_valores_faltantes,
    serializar_valores,
    parsear_fechas_serie,
    leer_excel_limpio,
    leer_csv_limpio,
    descubrir_fuentes_conafor,
)


# ============================================================
# CONFIGURACIÓN
# ============================================================

BASE_DIR = Path(r"C:\Users\Hp\OneDrive\Documentos\PT_Analisis")
RAW_DIR = BASE_DIR / "01_raw-data" / "conafor"
OUT_DIR = BASE_DIR / "02_data-understanding" / "conafor" / "reports"

OUT_DIR.mkdir(parents=True, exist_ok=True)

CSV_RESUMEN = OUT_DIR / "conafor_du03_resumen_calidad.csv"
CSV_HALLAZGOS = OUT_DIR / "conafor_du03_hallazgos.csv"
CSV_CALIDAD_CAMPO = OUT_DIR / "conafor_du03_calidad_por_campo.csv"


# ============================================================
# DETECCIÓN DE CAMPOS RELEVANTES
# ============================================================

def buscar_columna(df: pd.DataFrame, candidatos: list[str]) -> Optional[str]:
    cols = list(df.columns)
    cols_norm = [normalizar_texto(c) for c in cols]
    candidatos_norm = [normalizar_texto(c) for c in candidatos]

    for cand in candidatos_norm:
        if cand in cols_norm:
            return cols[cols_norm.index(cand)]

    for cand in candidatos_norm:
        for c in cols:
            if cand in normalizar_texto(c):
                return c

    return None


def obtener_campos_clave(df: pd.DataFrame) -> dict:
    return {
        "id_incendio": buscar_columna(df, [
            "clave_del_incendio", "claveinc", "clave_ince", "id", "folio", "clave",
        ]),
        "fecha_inicio": buscar_columna(df, [
            "fecha_inicio", "fechainic", "inicio", "f_inicio",
        ]),
        "fecha_termino": buscar_columna(df, [
            "fecha_termino", "fechafin", "fechaliq", "termino", "f_fin",
        ]),
        "anio": buscar_columna(df, [
            "anio", "ano", "año", "year",
        ]),
        "estado": buscar_columna(df, [
            "estado", "entidad_federativa",
        ]),
        "municipio": buscar_columna(df, ["municipio"]),
        "latitud": buscar_columna(df, ["latitud", "lat"]),
        "longitud": buscar_columna(df, ["longitud", "lon", "long"]),
        "superficie": buscar_columna(df, [
            "sup", "superficie", "total_hectareas", "ha",
        ]),
        "duracion": buscar_columna(df, [
            "duracion", "duracion_dias", "dias",
        ]),
    }


def obtener_campos_criticos(campos: dict, grupo_fuente: str) -> list[str]:
    criticos: list[str] = []

    if campos.get("estado"):
        criticos.append(campos["estado"])

    if "evento" in grupo_fuente or "shp" in grupo_fuente:
        for k in ("fecha_inicio", "latitud", "longitud"):
            if campos.get(k):
                criticos.append(campos[k])

    if "agregado" in grupo_fuente and campos.get("anio"):
        criticos.append(campos["anio"])

    vistos: set[str] = set()
    salida: list[str] = []
    for c in criticos:
        if c and c not in vistos:
            salida.append(c)
            vistos.add(c)

    return salida


# ============================================================
# HALLAZGOS
# ============================================================

def agregar_hallazgo(
    hallazgos: list[dict],
    fuente: str,
    grupo_fuente: str,
    formato: str,
    ruta: str,
    tipo_hallazgo: str,
    severidad: str,
    campo: Optional[str],
    cantidad: Any,
    detalle: str,
) -> None:
    hallazgos.append({
        "fuente": fuente,
        "grupo_fuente": grupo_fuente,
        "formato": formato,
        "ruta": ruta,
        "tipo_hallazgo": tipo_hallazgo,
        "severidad": severidad,
        "campo": campo,
        "cantidad": cantidad,
        "detalle": detalle,
    })


# ============================================================
# CALIDAD POR CAMPO
# ============================================================

def construir_calidad_por_campo(
    df: pd.DataFrame,
    fuente: str,
    grupo_fuente: str,
    formato: str,
    ruta: str,
    campos_criticos: list[str],
) -> list[dict]:
    filas: list[dict] = []
    n = len(df)

    for col in df.columns:
        serie = limpiar_valores_faltantes(df[col])
        nulos = int(serie.isna().sum())
        pct_nulos = round((nulos / n) * 100, 4) if n else None
        cardinalidad = int(serie.nunique(dropna=True))
        ejemplos = serializar_valores(serie.dropna().astype(str).head(10).tolist())

        filas.append({
            "fuente": fuente,
            "grupo_fuente": grupo_fuente,
            "formato": formato,
            "ruta": ruta,
            "campo": col,
            "es_critico": "si" if col in campos_criticos else "no",
            "tipo_original": str(df[col].dtype),
            "n_registros_fuente": n,
            "nulos": nulos,
            "pct_nulos": pct_nulos,
            "cardinalidad": cardinalidad,
            "ejemplos": ejemplos,
        })

    return filas


# ============================================================
# VALIDACIONES AUXILIARES
# ============================================================

def contar_fuera_de_rango_numerico(
    serie: pd.Series,
    minimo: Optional[float] = None,
    maximo: Optional[float] = None,
) -> int:
    num = pd.to_numeric(serie, errors="coerce")
    mask = num.notna()

    if minimo is not None:
        mask &= num >= minimo
    if maximo is not None:
        mask &= num <= maximo

    fuera = num.notna() & (~mask)
    return int(fuera.sum())


# ============================================================
# VALIDACIONES AUXILIARES
# ============================================================

def contar_fuera_de_rango_numerico(
    serie: pd.Series,
    minimo: Optional[float] = None,
    maximo: Optional[float] = None,
) -> int:
    num = pd.to_numeric(serie, errors="coerce")
    mask = num.notna()

    if minimo is not None:
        mask &= num >= minimo
    if maximo is not None:
        mask &= num <= maximo

    fuera = num.notna() & (~mask)
    return int(fuera.sum())


def evaluar_anio_vs_fecha(anio: pd.Series, fecha: pd.Series) -> int:
    anios = pd.to_numeric(anio, errors="coerce")
    fechas = parsear_fechas_serie(fecha)
    mask = anios.notna() & fechas.notna()
    if not mask.any():
        return 0

    anios_cmp = anios[mask].astype("Int64")
    fechas_cmp = fechas[mask].dt.year.astype("Int64")
    return int((anios_cmp != fechas_cmp).sum())


def contar_fechas_fuera_periodo(
    serie_fecha: pd.Series,
    inicio: str = "2001-01-01",
    fin: str = "2025-12-31",
) -> int:
    fechas = parsear_fechas_serie(serie_fecha)
    fecha_ini = pd.to_datetime(inicio)
    fecha_fin = pd.to_datetime(fin)

    mask = fechas.notna() & ((fechas < fecha_ini) | (fechas > fecha_fin))
    return int(mask.sum())


def clasificar_severidad_nulos(pct_nulos: float, es_critico: bool) -> str:
    if es_critico:
        if pct_nulos >= 20:
            return "alta"
        if pct_nulos > 0:
            return "media"
        return "baja"

    if pct_nulos >= 50:
        return "media"
    if pct_nulos > 0:
        return "baja"
    return "baja"


# ============================================================
# CHEQUEOS DE CALIDAD TABULAR
# ============================================================

def evaluar_calidad_tabular(
    df: pd.DataFrame,
    fuente: str,
    grupo_fuente: str,
    formato: str,
    ruta: str,
    tipo_geometria: Optional[str] = None,
) -> tuple[dict, list[dict], list[dict]]:
    hallazgos: list[dict] = []

    df = df.copy()
    df.columns = [normalizar_texto(c) for c in df.columns]

    n_registros = len(df)
    n_columnas = len(df.columns)

    campos = obtener_campos_clave(df)
    campos_criticos = obtener_campos_criticos(campos, grupo_fuente)
    calidad_por_campo = construir_calidad_por_campo(
        df=df,
        fuente=fuente,
        grupo_fuente=grupo_fuente,
        formato=formato,
        ruta=ruta,
        campos_criticos=campos_criticos,
    )

    # ========================================================
    # DUPLICADOS
    # ========================================================
    duplicados_exactos = int(df.duplicated().sum())
    if duplicados_exactos > 0:
        pct_dup = (duplicados_exactos / n_registros) if n_registros else 0.0
        severidad = "alta" if pct_dup >= 0.01 else "media"
        agregar_hallazgo(
            hallazgos, fuente, grupo_fuente, formato, ruta,
            "duplicados_exactos", severidad, None,
            duplicados_exactos,
            f"Registros completamente duplicados ({pct_dup:.2%} del total).",
        )

    duplicados_clave = None
    if "evento" in grupo_fuente and campos["id_incendio"] and campos["id_incendio"] in df.columns:
        serie_id = limpiar_valores_faltantes(df[campos["id_incendio"]]).dropna()
        duplicados_clave = int(serie_id.duplicated().sum())
        if duplicados_clave > 0:
            agregar_hallazgo(
                hallazgos, fuente, grupo_fuente, formato, ruta,
                "duplicados_por_clave_incendio", "media",
                campos["id_incendio"], duplicados_clave,
                "Se detectaron claves de incendio repetidas.",
            )

    # ========================================================
    # NULOS EN CAMPOS CRÍTICOS
    # ========================================================
    for col in campos_criticos:
        serie = limpiar_valores_faltantes(df[col])
        nulos = int(serie.isna().sum())
        pct_nulos = round((nulos / n_registros) * 100, 4) if n_registros else 0.0

        if nulos > 0:
            severidad = clasificar_severidad_nulos(pct_nulos, es_critico=True)
            agregar_hallazgo(
                hallazgos, fuente, grupo_fuente, formato, ruta,
                "nulos_en_campo_critico", severidad, col, nulos,
                f"Campo crítico con {pct_nulos}% de nulos.",
            )

    # ========================================================
    # FECHAS
    # ========================================================
    fechas_invalidas_inicio = None
    fechas_invalidas_termino = None
    fechas_invertidas = None
    inconsistencia_anio_fecha = None

    fecha_inicio_col = campos["fecha_inicio"]
    fecha_termino_col = campos["fecha_termino"]

    fechas_inicio = None
    fechas_termino = None

    if fecha_inicio_col and fecha_inicio_col in df.columns:
        serie_raw = limpiar_valores_faltantes(df[fecha_inicio_col])
        fechas_inicio = parsear_fechas_serie(serie_raw)
        fechas_invalidas_inicio = int(serie_raw.notna().sum() - fechas_inicio.notna().sum())
        if fechas_invalidas_inicio > 0:
            agregar_hallazgo(
                hallazgos, fuente, grupo_fuente, formato, ruta,
                "fechas_invalidas", "media", fecha_inicio_col,
                fechas_invalidas_inicio,
                "Valores no nulos que no pudieron parsearse como fecha de inicio.",
            )

    if fecha_termino_col and fecha_termino_col in df.columns:
        serie_raw = limpiar_valores_faltantes(df[fecha_termino_col])
        fechas_termino = parsear_fechas_serie(serie_raw)
        fechas_invalidas_termino = int(serie_raw.notna().sum() - fechas_termino.notna().sum())
        if fechas_invalidas_termino > 0:
            agregar_hallazgo(
                hallazgos, fuente, grupo_fuente, formato, ruta,
                "fechas_invalidas", "media", fecha_termino_col,
                fechas_invalidas_termino,
                "Valores no nulos que no pudieron parsearse como fecha de término.",
            )

    if fechas_inicio is not None and fechas_termino is not None:
        mask = fechas_inicio.notna() & fechas_termino.notna() & (fechas_inicio > fechas_termino)
        fechas_invertidas = int(mask.sum())
        if fechas_invertidas > 0:
            agregar_hallazgo(
                hallazgos, fuente, grupo_fuente, formato, ruta,
                "fechas_invertidas", "alta",
                f"{fecha_inicio_col}/{fecha_termino_col}", fechas_invertidas,
                "Fecha de inicio posterior a fecha de término.",
            )

    fechas_fuera_periodo_proyecto = None

    if fecha_inicio_col and fecha_inicio_col in df.columns:
        fechas_fuera_periodo_proyecto = contar_fechas_fuera_periodo(
            df[fecha_inicio_col],
            inicio="2001-01-01",
            fin="2025-12-31",
        )

        if fechas_fuera_periodo_proyecto > 0:
            agregar_hallazgo(
                hallazgos, fuente, grupo_fuente, formato, ruta,
                "fechas_fuera_periodo_proyecto", "media", fecha_inicio_col,
                fechas_fuera_periodo_proyecto,
                "Se detectaron registros fuera del periodo definido para el proyecto [2001-2025].",
            )

    # ========================================================
    # AÑO
    # ========================================================
    anios_invalidos = None
    if campos["anio"] and campos["anio"] in df.columns:
        anios = pd.to_numeric(df[campos["anio"]], errors="coerce")
        mask_invalid = anios.notna() & ((anios < 1970) | (anios > 2025))
        anios_invalidos = int(mask_invalid.sum())
        if anios_invalidos > 0:
            agregar_hallazgo(
                hallazgos, fuente, grupo_fuente, formato, ruta,
                "anios_invalidos", "media", campos["anio"], anios_invalidos,
                "Años fuera de rango esperado [1970, 2025].",
            )

        if campos["fecha_inicio"] and campos["fecha_inicio"] in df.columns:
            inconsistencia_anio_fecha = evaluar_anio_vs_fecha(
                df[campos["anio"]], df[campos["fecha_inicio"]]
            )
            if inconsistencia_anio_fecha > 0:
                agregar_hallazgo(
                    hallazgos, fuente, grupo_fuente, formato, ruta,
                    "anio_vs_fecha_inconsistente", "media",
                    f"{campos['anio']}/{campos['fecha_inicio']}", inconsistencia_anio_fecha,
                    "El año reportado no coincide con el año de la fecha de inicio.",
                )

    # ========================================================
    # COORDENADAS
    # ========================================================
    latitudes_fuera_rango = None
    longitudes_fuera_rango = None

    if campos["latitud"] and campos["latitud"] in df.columns:
        latitudes_fuera_rango = contar_fuera_de_rango_numerico(
            df[campos["latitud"]], minimo=-90, maximo=90
        )
        if latitudes_fuera_rango > 0:
            agregar_hallazgo(
                hallazgos, fuente, grupo_fuente, formato, ruta,
                "latitudes_fuera_rango", "alta", campos["latitud"],
                latitudes_fuera_rango,
                "Se detectaron latitudes fuera del rango válido [-90, 90].",
            )

    if campos["longitud"] and campos["longitud"] in df.columns:
        longitudes_fuera_rango = contar_fuera_de_rango_numerico(
            df[campos["longitud"]], minimo=-180, maximo=180
        )
        if longitudes_fuera_rango > 0:
            agregar_hallazgo(
                hallazgos, fuente, grupo_fuente, formato, ruta,
                "longitudes_fuera_rango", "alta", campos["longitud"],
                longitudes_fuera_rango,
                "Se detectaron longitudes fuera del rango válido [-180, 180].",
            )


    # ========================================================
    # VARIABLES NUMÉRICAS DE INTERÉS
    # ========================================================
    superficie_negativa = None
    duracion_negativa = None

    if campos["superficie"] and campos["superficie"] in df.columns:
        superficie_negativa = contar_fuera_de_rango_numerico(
            df[campos["superficie"]], minimo=0
        )
        if superficie_negativa > 0:
            agregar_hallazgo(
                hallazgos, fuente, grupo_fuente, formato, ruta,
                "superficie_negativa", "alta", campos["superficie"],
                superficie_negativa,
                "Se detectaron valores negativos en superficie afectada.",
            )

    if campos["duracion"] and campos["duracion"] in df.columns:
        duracion_negativa = contar_fuera_de_rango_numerico(
            df[campos["duracion"]], minimo=0
        )
        if duracion_negativa > 0:
            agregar_hallazgo(
                hallazgos, fuente, grupo_fuente, formato, ruta,
                "duracion_negativa", "media", campos["duracion"],
                duracion_negativa,
                "Se detectaron valores negativos en duración.",
            )

    resumen = {
        "fuente": fuente,
        "grupo_fuente": grupo_fuente,
        "formato": formato,
        "ruta": ruta,
        "lectura_ok": "si",
        "error_lectura": None,
        "tipo_geometria": tipo_geometria,
        "registros": n_registros,
        "columnas": n_columnas,
        "duplicados_exactos": duplicados_exactos,
        "duplicados_por_clave_incendio": duplicados_clave,
        "fechas_invalidas_inicio": fechas_invalidas_inicio,
        "fechas_invalidas_termino": fechas_invalidas_termino,
        "fechas_invertidas": fechas_invertidas,
        "fechas_fuera_periodo_proyecto": fechas_fuera_periodo_proyecto,
        "anios_invalidos": anios_invalidos,
        "anio_vs_fecha_inconsistente": inconsistencia_anio_fecha,
        "latitudes_fuera_rango": latitudes_fuera_rango,
        "longitudes_fuera_rango": longitudes_fuera_rango,
        "superficie_negativa": superficie_negativa,
        "duracion_negativa": duracion_negativa,
        "geometrias_nulas": None,
        "geometrias_vacias": None,
        "geometrias_invalidas": None,
        "campos_criticos_evaluados": len(campos_criticos),
        "n_hallazgos": len(hallazgos),
    }

    return resumen, hallazgos, calidad_por_campo


# ============================================================
# CHEQUEOS DE CALIDAD SHP
# ============================================================

def evaluar_calidad_shp(
    gdf: Any,
    fuente: str,
    grupo_fuente: str,
    ruta: str,
) -> tuple[dict, list[dict], list[dict]]:
    hallazgos: list[dict] = []

    tipo_geometria = "desconocido"
    try:
        tipo_geometria = ", ".join(
            gdf.geometry.geom_type.dropna().astype(str).value_counts().index.tolist()[:5]
        ) or "desconocido"
    except Exception:
        pass

    df = pd.DataFrame(gdf.drop(columns="geometry", errors="ignore")).copy()
    df.columns = [normalizar_texto(c) for c in df.columns]

    resumen_tab, hallazgos_tab, calidad_por_campo = evaluar_calidad_tabular(
        df=df,
        fuente=fuente,
        grupo_fuente=grupo_fuente,
        formato="shp",
        ruta=ruta,
        tipo_geometria=tipo_geometria,
    )
    hallazgos.extend(hallazgos_tab)

    geometrias_nulas = int(gdf.geometry.isna().sum())

    try:
        geometrias_vacias = int(gdf.geometry.is_empty.sum())
    except Exception:
        geometrias_vacias = None

    try:
        geometrias_invalidas = int((~gdf.geometry.is_valid).sum())
    except Exception:
        geometrias_invalidas = None

    if geometrias_nulas > 0:
        agregar_hallazgo(
            hallazgos, fuente, grupo_fuente, "shp", ruta,
            "geometrias_nulas", "alta", "geometry",
            geometrias_nulas, "Se detectaron geometrías nulas.",
        )

    if geometrias_vacias is not None and geometrias_vacias > 0:
        agregar_hallazgo(
            hallazgos, fuente, grupo_fuente, "shp", ruta,
            "geometrias_vacias", "alta", "geometry",
            geometrias_vacias, "Se detectaron geometrías vacías.",
        )

    if geometrias_invalidas is not None and geometrias_invalidas > 0:
        severidad = "alta" if geometrias_invalidas >= 10 else "media"
        agregar_hallazgo(
            hallazgos, fuente, grupo_fuente, "shp", ruta,
            "geometrias_invalidas", severidad, "geometry",
            geometrias_invalidas, "Se detectaron geometrías inválidas.",
        )

    resumen_tab["geometrias_nulas"] = geometrias_nulas
    resumen_tab["geometrias_vacias"] = geometrias_vacias
    resumen_tab["geometrias_invalidas"] = geometrias_invalidas
    resumen_tab["n_hallazgos"] = len(hallazgos)

    return resumen_tab, hallazgos, calidad_por_campo


# ============================================================
# MAIN
# ============================================================

def main() -> None:
    print("CONAFOR DU03 | Calidad básica y hallazgos")
    print(f"Directorio base: {RAW_DIR}")

    if not RAW_DIR.exists():
        raise FileNotFoundError(f"No existe el directorio esperado: {RAW_DIR}")

    fuentes = descubrir_fuentes_conafor(RAW_DIR)
    if not fuentes:
        raise RuntimeError("No se detectaron fuentes CONAFOR en el directorio especificado.")

    filas_resumen: list[dict] = []
    filas_hallazgos: list[dict] = []
    filas_calidad_campo: list[dict] = []

    for fuente in fuentes:
        print(f"\nProcesando: {fuente['nombre_fuente']} ({fuente['tipo']})")
        path = fuente["path"]

        if not path.exists():
            filas_hallazgos.append({
                "fuente": fuente["nombre_fuente"],
                "grupo_fuente": fuente["grupo_fuente"],
                "formato": fuente["tipo"],
                "ruta": str(path),
                "tipo_hallazgo": "archivo_no_encontrado",
                "severidad": "alta",
                "campo": None,
                "cantidad": None,
                "detalle": f"No se encontró el archivo: {path}",
            })
            filas_resumen.append({
                "fuente": fuente["nombre_fuente"],
                "grupo_fuente": fuente["grupo_fuente"],
                "formato": fuente["tipo"],
                "ruta": str(path),
                "lectura_ok": "no",
                "error_lectura": "archivo_no_encontrado",
                "tipo_geometria": None,
                "registros": None,
                "columnas": None,
                "duplicados_exactos": None,
                "duplicados_por_clave_incendio": None,
                "fechas_invalidas_inicio": None,
                "fechas_invalidas_termino": None,
                "fechas_invertidas": None,
                "anios_invalidos": None,
                "anio_vs_fecha_inconsistente": None,
                "latitudes_fuera_rango": None,
                "longitudes_fuera_rango": None,
                "superficie_negativa": None,
                "duracion_negativa": None,
                "geometrias_nulas": None,
                "geometrias_vacias": None,
                "geometrias_invalidas": None,
                "campos_criticos_evaluados": None,
                "n_hallazgos": 1,
            })
            continue

        try:
            if fuente["tipo"] == "shp":
                if gpd is None:
                    raise ImportError("geopandas no está instalado.")
                gdf = gpd.read_file(path)
                resumen, hallazgos, calidad_campo = evaluar_calidad_shp(
                    gdf=gdf,
                    fuente=fuente["nombre_fuente"],
                    grupo_fuente=fuente["grupo_fuente"],
                    ruta=str(path),
                )

            elif fuente["tipo"] == "xlsx":
                df, meta = leer_excel_limpio(path)
                resumen, hallazgos, calidad_campo = evaluar_calidad_tabular(
                    df=df,
                    fuente=fuente["nombre_fuente"],
                    grupo_fuente=fuente["grupo_fuente"],
                    formato="xlsx",
                    ruta=str(path),
                )

            elif fuente["tipo"] == "csv":
                df, meta = leer_csv_limpio(path)
                resumen, hallazgos, calidad_campo = evaluar_calidad_tabular(
                    df=df,
                    fuente=fuente["nombre_fuente"],
                    grupo_fuente=fuente["grupo_fuente"],
                    formato="csv",
                    ruta=str(path),
                )

            else:
                raise ValueError(f"Tipo de fuente no soportado: {fuente['tipo']}")

            filas_resumen.append(resumen)
            filas_hallazgos.extend(hallazgos)
            filas_calidad_campo.extend(calidad_campo)

        except Exception as e:
            filas_hallazgos.append({
                "fuente": fuente["nombre_fuente"],
                "grupo_fuente": fuente["grupo_fuente"],
                "formato": fuente["tipo"],
                "ruta": str(path),
                "tipo_hallazgo": f"error_lectura_{fuente['tipo']}",
                "severidad": "alta",
                "campo": None,
                "cantidad": None,
                "detalle": str(e),
            })
            filas_resumen.append({
                "fuente": fuente["nombre_fuente"],
                "grupo_fuente": fuente["grupo_fuente"],
                "formato": fuente["tipo"],
                "ruta": str(path),
                "lectura_ok": "no",
                "error_lectura": str(e),
                "tipo_geometria": None,
                "registros": None,
                "columnas": None,
                "duplicados_exactos": None,
                "duplicados_por_clave_incendio": None,
                "fechas_invalidas_inicio": None,
                "fechas_invalidas_termino": None,
                "fechas_invertidas": None,
                "anios_invalidos": None,
                "anio_vs_fecha_inconsistente": None,
                "latitudes_fuera_rango": None,
                "longitudes_fuera_rango": None,
                "superficie_negativa": None,
                "duracion_negativa": None,
                "geometrias_nulas": None,
                "geometrias_vacias": None,
                "geometrias_invalidas": None,
                "campos_criticos_evaluados": None,
                "n_hallazgos": 1,
            })

    df_resumen = pd.DataFrame(filas_resumen)
    df_hallazgos = pd.DataFrame(filas_hallazgos)
    df_calidad_campo = pd.DataFrame(filas_calidad_campo)

    cols_resumen = [
        "fuente", "grupo_fuente", "formato", "ruta",
        "lectura_ok", "error_lectura",
        "tipo_geometria", "registros", "columnas",
        "duplicados_exactos", "duplicados_por_clave_incendio",
        "fechas_invalidas_inicio", "fechas_invalidas_termino", "fechas_invertidas",
        "fechas_fuera_periodo_proyecto",
        "anios_invalidos", "anio_vs_fecha_inconsistente",
        "latitudes_fuera_rango", "longitudes_fuera_rango",
        "superficie_negativa", "duracion_negativa",
        "geometrias_nulas", "geometrias_vacias", "geometrias_invalidas",
        "campos_criticos_evaluados", "n_hallazgos",
    ]
    if not df_resumen.empty:
        df_resumen = df_resumen.reindex(columns=cols_resumen).sort_values(
            by=["grupo_fuente", "fuente"]
        )

    cols_hallazgos = [
        "fuente", "grupo_fuente", "formato", "ruta",
        "tipo_hallazgo", "severidad", "campo", "cantidad", "detalle",
    ]
    if not df_hallazgos.empty:
        df_hallazgos = df_hallazgos.reindex(columns=cols_hallazgos).sort_values(
            by=["fuente", "severidad", "tipo_hallazgo"]
        )

    cols_calidad_campo = [
        "fuente", "grupo_fuente", "formato", "ruta",
        "campo", "es_critico", "tipo_original",
        "n_registros_fuente", "nulos", "pct_nulos", "cardinalidad", "ejemplos",
    ]
    if not df_calidad_campo.empty:
        df_calidad_campo = df_calidad_campo.reindex(columns=cols_calidad_campo).sort_values(
            by=["fuente", "campo"]
        )

    df_resumen.to_csv(CSV_RESUMEN, index=False, encoding="utf-8-sig")
    df_hallazgos.to_csv(CSV_HALLAZGOS, index=False, encoding="utf-8-sig")
    df_calidad_campo.to_csv(CSV_CALIDAD_CAMPO, index=False, encoding="utf-8-sig")

    print("\nArchivos generados:")
    print(f"  {CSV_RESUMEN}")
    print(f"  {CSV_HALLAZGOS}")
    print(f"  {CSV_CALIDAD_CAMPO}")
    print("\nProceso terminado.")


if __name__ == "__main__":
    main()