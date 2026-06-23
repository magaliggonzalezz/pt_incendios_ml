from __future__ import annotations

from pathlib import Path
from typing import Optional

import pandas as pd

try:
    import geopandas as gpd
except ImportError:
    gpd = None

from conafor_du_utils import (
    normalizar_texto,
    parsear_fechas_serie,
    leer_excel_limpio,
    leer_csv_limpio,
    descubrir_fuentes_conafor,
    extraer_rango_nominal_desde_nombre,
)


# ============================================================
# CONFIGURACIÓN
# ============================================================

BASE_DIR = Path(r"C:\Users\Hp\OneDrive\Documentos\PT_Analisis")
RAW_DIR = BASE_DIR / "01_raw-data" / "conafor"
OUT_DIR = BASE_DIR / "02_data-understanding" / "conafor" / "reports"

OUT_DIR.mkdir(parents=True, exist_ok=True)

CSV_REPORTE = OUT_DIR / "conafor_du01_cobertura.csv"


# ============================================================
# DETECCIÓN DE COLUMNAS TEMPORALES
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


def detectar_columna_fecha(df: pd.DataFrame) -> Optional[str]:
    """
    Prioriza la fecha de inicio del evento.
    Solo usa fechas de término u otras fechas si no encuentra fecha de inicio.
    """
    grupos_candidatos = [
        ["fecha_inicio", "fechainic", "fecha_ini", "f_inicio", "inicio"],
        ["fecha_termino", "fechafin", "fechaliq", "fecha_fin", "f_fin", "termino"],
        ["fecha", "Fecha Inicio"],
    ]

    for candidatos in grupos_candidatos:
        col = buscar_columna(df, candidatos)
        if col:
            return col

    return None


def detectar_columna_anio(df: pd.DataFrame) -> Optional[str]:
    candidatos = ["anio", "ano", "año", "year"]
    return buscar_columna(df, candidatos)


def inferir_cobertura_observada(df: pd.DataFrame) -> tuple[Optional[str], Optional[str], Optional[str], Optional[str]]:
    """
    Retorna:
    - fecha_min_observada
    - fecha_max_observada
    - granularidad_observada: 'fecha', 'anual' o None
    - campo_temporal_usado
    """
    col_fecha = detectar_columna_fecha(df)
    if col_fecha and col_fecha in df.columns:
        fechas = parsear_fechas_serie(df[col_fecha])
        fechas_validas = fechas.dropna()
        if not fechas_validas.empty:
            return (
                fechas_validas.min().strftime("%Y-%m-%d"),
                fechas_validas.max().strftime("%Y-%m-%d"),
                "fecha",
                col_fecha,
            )

    col_anio = detectar_columna_anio(df)
    if col_anio and col_anio in df.columns:
        anios = pd.to_numeric(df[col_anio], errors="coerce").dropna()
        if not anios.empty:
            anio_min = int(anios.min())
            anio_max = int(anios.max())
            return (
                f"{anio_min}-01-01",
                f"{anio_max}-12-31",
                "anual",
                col_anio,
            )

    return None, None, None, None


def inferir_granularidad_fuente(grupo_fuente: str) -> str:
    if "agregado" in grupo_fuente:
        return "agregado_anual"
    return "por_evento"


# ============================================================
# RESUMEN DE FUENTE
# ============================================================

def construir_resumen_fuente(
    fuente: dict,
    existe: bool,
    legible: bool,
    ruta: str,
    registros: Optional[int] = None,
    columnas: Optional[int] = None,
    tipo_geometria: Optional[str] = None,
    cobertura_nominal_inicio: Optional[str] = None,
    cobertura_nominal_fin: Optional[str] = None,
    campo_temporal_usado: Optional[str] = None,
    cobertura_obs_inicio: Optional[str] = None,
    cobertura_obs_fin: Optional[str] = None,
    granularidad_observada: Optional[str] = None,
    observacion: Optional[str] = None,
) -> dict:
    return {
        "fuente": fuente["nombre_fuente"],
        "grupo_fuente": fuente["grupo_fuente"],
        "formato": fuente["tipo"],
        "ruta": ruta,
        "existe": "si" if existe else "no",
        "legible": "si" if legible else "no",
        "registros": registros,
        "columnas": columnas,
        "tipo_geometria": tipo_geometria,
        "cobertura_nominal_inicio": cobertura_nominal_inicio,
        "cobertura_nominal_fin": cobertura_nominal_fin,
        "campo_temporal_usado": campo_temporal_usado,
        "cobertura_observada_inicio": cobertura_obs_inicio,
        "cobertura_observada_fin": cobertura_obs_fin,
        "granularidad_temporal_fuente": inferir_granularidad_fuente(fuente["grupo_fuente"]),
        "granularidad_temporal_observada": granularidad_observada,
        "observacion": observacion,
    }


# ============================================================
# MAIN
# ============================================================

def main() -> None:
    print("CONAFOR DU01 | Inventario y cobertura de fuentes")
    print(f"Directorio base: {RAW_DIR}")

    if not RAW_DIR.exists():
        raise FileNotFoundError(f"No existe el directorio esperado: {RAW_DIR}")

    fuentes = descubrir_fuentes_conafor(RAW_DIR)
    if not fuentes:
        raise RuntimeError("No se detectaron fuentes CONAFOR en el directorio especificado.")

    filas_reporte: list[dict] = []

    for fuente in fuentes:
        print(f"\nProcesando: {fuente['nombre_fuente']} ({fuente['tipo']})")
        path = fuente["path"]
        ruta = str(path)

        cobertura_nominal_inicio, cobertura_nominal_fin = extraer_rango_nominal_desde_nombre(
            fuente["nombre_fuente"]
        )

        if not path.exists():
            filas_reporte.append(
                construir_resumen_fuente(
                    fuente=fuente,
                    existe=False,
                    legible=False,
                    ruta=ruta,
                    cobertura_nominal_inicio=cobertura_nominal_inicio,
                    cobertura_nominal_fin=cobertura_nominal_fin,
                    observacion="Archivo no encontrado.",
                )
            )
            continue

        try:
            if fuente["tipo"] == "shp":
                if gpd is None:
                    raise ImportError("geopandas no está instalado.")

                gdf = gpd.read_file(path)

                tipo_geometria = ", ".join(
                    gdf.geometry.geom_type.dropna().astype(str).value_counts().index.tolist()[:5]
                ) or "desconocido"

                df = pd.DataFrame(gdf.drop(columns="geometry", errors="ignore")).copy()
                df.columns = [normalizar_texto(c) for c in df.columns]

                obs_ini, obs_fin, granularidad_obs, campo_temporal = inferir_cobertura_observada(df)

                filas_reporte.append(
                    construir_resumen_fuente(
                        fuente=fuente,
                        existe=True,
                        legible=True,
                        ruta=ruta,
                        registros=len(gdf),
                        columnas=len(gdf.columns),
                        tipo_geometria=tipo_geometria,
                        cobertura_nominal_inicio=cobertura_nominal_inicio,
                        cobertura_nominal_fin=cobertura_nominal_fin,
                        cobertura_obs_inicio=obs_ini,
                        cobertura_obs_fin=obs_fin,
                        campo_temporal_usado=campo_temporal,
                        granularidad_observada=granularidad_obs,
                    )
                )

            elif fuente["tipo"] == "xlsx":
                df, _meta = leer_excel_limpio(path)
                obs_ini, obs_fin, granularidad_obs = inferir_cobertura_observada(df)

                filas_reporte.append(
                    construir_resumen_fuente(
                        fuente=fuente,
                        existe=True,
                        legible=True,
                        ruta=ruta,
                        registros=len(df),
                        columnas=len(df.columns),
                        tipo_geometria=None,
                        cobertura_nominal_inicio=cobertura_nominal_inicio,
                        cobertura_nominal_fin=cobertura_nominal_fin,
                        cobertura_obs_inicio=obs_ini,
                        cobertura_obs_fin=obs_fin,
                        campo_temporal_usado=campo_temporal,
                        granularidad_observada=granularidad_obs,
                    )
                )

            else:  # csv
                df, _meta = leer_csv_limpio(path)
                obs_ini, obs_fin, granularidad_obs = inferir_cobertura_observada(df)

                filas_reporte.append(
                    construir_resumen_fuente(
                        fuente=fuente,
                        existe=True,
                        legible=True,
                        ruta=ruta,
                        registros=len(df),
                        columnas=len(df.columns),
                        tipo_geometria=None,
                        cobertura_nominal_inicio=cobertura_nominal_inicio,
                        cobertura_nominal_fin=cobertura_nominal_fin,
                        cobertura_obs_inicio=obs_ini,
                        cobertura_obs_fin=obs_fin,
                        campo_temporal_usado=campo_temporal,
                        granularidad_observada=granularidad_obs,
                    )
                )

        except Exception as e:
            filas_reporte.append(
                construir_resumen_fuente(
                    fuente=fuente,
                    existe=True,
                    legible=False,
                    ruta=ruta,
                    cobertura_nominal_inicio=cobertura_nominal_inicio,
                    cobertura_nominal_fin=cobertura_nominal_fin,
                    observacion=str(e),
                )
            )

    df_reporte = pd.DataFrame(filas_reporte)

    cols_reporte = [
        "fuente", "grupo_fuente", "formato", "ruta",
        "existe", "legible", "registros", "columnas",
        "tipo_geometria",
        "cobertura_nominal_inicio", "cobertura_nominal_fin",
        "cobertura_observada_inicio", "cobertura_observada_fin",
        "granularidad_temporal_fuente", "granularidad_temporal_observada",
        "campo_temporal_usado", "observacion",
    ]

    if not df_reporte.empty:
        df_reporte = df_reporte.reindex(columns=cols_reporte).sort_values(
            by=["grupo_fuente", "fuente"]
        )

    df_reporte.to_csv(CSV_REPORTE, index=False, encoding="utf-8-sig")

    print("\nArchivo generado:")
    print(f"  {CSV_REPORTE}")
    print("\nProceso terminado.")


if __name__ == "__main__":
    main()