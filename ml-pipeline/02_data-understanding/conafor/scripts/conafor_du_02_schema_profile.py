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

CSV_ESQUEMA = OUT_DIR / "conafor_du02_esquema.csv"
CSV_RESUMEN = OUT_DIR / "conafor_du02_resumen.csv"


# ============================================================
# INFERENCIA DE TIPO Y ROL
# ============================================================

def inferir_tipo_semantico(serie: pd.Series) -> str:
    s = limpiar_valores_faltantes(serie)
    n_validos = int(s.notna().sum())

    if n_validos == 0:
        return "vacio"

    if pd.api.types.is_datetime64_any_dtype(s):
        return "fecha"

    num = pd.to_numeric(s, errors="coerce")
    ratio_num = float(num.notna().sum()) / n_validos if n_validos else 0.0
    if ratio_num >= 0.90:
        return "numerico"

    fec = parsear_fechas_serie(s)
    ratio_fec = float(fec.notna().sum()) / n_validos if n_validos else 0.0
    if ratio_fec >= 0.90:
        return "fecha"

    unicos = int(s.nunique(dropna=True))
    ratio_unicos = unicos / n_validos if n_validos else 0.0

    if unicos <= 20 or ratio_unicos <= 0.20:
        return "categorico"

    return "texto"


def inferir_rol_campo(nombre_col: str, serie: pd.Series) -> str:
    cn = normalizar_texto(nombre_col)
    tipo_sem = inferir_tipo_semantico(serie)

    claves_fecha = ["fecha", "fechainic", "fechafin", "fechaliq", "inicio", "termino", "f_inicio", "f_fin",]
    claves_temporal_anual = ["anio", "ano", "año", "year"]
    claves_geo = ["lat", "lon", "long", "x", "y", "geom", "geometry", "coorden"]

    claves_id_exactas = {
        "id", "folio", "clave", "claveinc", "clave_ince", "clave_del_incendio",
        "cve_ent", "cve_mun", "cvegeo", "clave_municipio", "codigo",
    }

    claves_cat = [
        "estado", "municipio", "causa", "region", "predio", "veget", "impact",
        "tamano", "tamaño", "tipoinc", "tipo_de_incendio", "tipo_vegetacion",
        "entidad_federativa",
    ]

    claves_num = [
        "sup", "superficie", "ha", "hect", "duracion", "duracion_dias", "dias",
        "cantidad_de_incendios_forestales",
    ]

    if any(k in cn for k in claves_fecha):
        return "fecha"
    if cn in claves_temporal_anual:
        return "temporal_anual"
    if any(k in cn for k in claves_geo) or cn == "geometry":
        return "geografico"
    if cn in claves_id_exactas:
        return "identificador"
    if any(k in cn for k in claves_cat):
        return "categorico"
    if any(k in cn for k in claves_num):
        return "numerico"

    if tipo_sem == "fecha":
        return "fecha"
    if tipo_sem == "numerico":
        return "numerico"
    if tipo_sem == "categorico":
        return "categorico"
    if tipo_sem == "texto":
        return "texto_libre"

    return "desconocido"


# ============================================================
# PERFILADO DE COLUMNAS
# ============================================================

def perfilar_dataframe(
    df: pd.DataFrame,
    nombre_fuente: str,
    grupo_fuente: str,
    formato: str,
    ruta: str,
    tipo_geometria: Optional[str] = None,
) -> tuple[list[dict], dict]:

    filas_esquema: list[dict] = []
    n_registros = len(df)
    n_columnas = len(df.columns)

    contadores = {
        "campos_fecha": 0,
        "campos_temporal_anual": 0,
        "campos_geograficos": 0,
        "campos_identificador": 0,
        "campos_categoricos": 0,
        "campos_numericos": 0,
        "campos_texto_libre": 0,
        "campos_vacios": 0,
    }

    for col in df.columns:
        serie = limpiar_valores_faltantes(df[col])
        nulos = int(serie.isna().sum())
        pct_nulos = round((nulos / n_registros) * 100, 4) if n_registros else None
        cardinalidad = int(serie.nunique(dropna=True))
        tipo_original = str(df[col].dtype)
        tipo_inferido = inferir_tipo_semantico(serie)
        rol = inferir_rol_campo(col, serie)
        muestra = serializar_valores(serie.dropna().astype(str).head(10).tolist())

        filas_esquema.append({
            "fuente": nombre_fuente,
            "grupo_fuente": grupo_fuente,
            "formato": formato,
            "ruta": ruta,
            "tipo_geometria": tipo_geometria,
            "campo": col,
            "tipo_original": tipo_original,
            "tipo_inferido": tipo_inferido,
            "rol_campo": rol,
            "n_registros_fuente": n_registros,
            "nulos": nulos,
            "pct_nulos": pct_nulos,
            "cardinalidad": cardinalidad,
            "ejemplos": muestra,
        })

        rol_key = {
            "fecha": "campos_fecha",
            "temporal_anual": "campos_temporal_anual",
            "geografico": "campos_geograficos",
            "identificador": "campos_identificador",
            "categorico": "campos_categoricos",
            "numerico": "campos_numericos",
            "texto_libre": "campos_texto_libre",
        }.get(rol)

        if rol_key:
            contadores[rol_key] += 1
        if tipo_inferido == "vacio":
            contadores["campos_vacios"] += 1

    resumen = {
        "fuente": nombre_fuente,
        "grupo_fuente": grupo_fuente,
        "formato": formato,
        "ruta": ruta,
        "tipo_geometria": tipo_geometria,
        "registros": n_registros,
        "columnas": n_columnas,
        **contadores,
    }

    return filas_esquema, resumen


# ============================================================
# MAIN
# ============================================================

def main() -> None:
    print("CONAFOR DU02 | Perfil de esquema")
    print(f"Directorio base: {RAW_DIR}")

    if not RAW_DIR.exists():
        raise FileNotFoundError(f"No existe el directorio esperado: {RAW_DIR}")

    fuentes = descubrir_fuentes_conafor(RAW_DIR)
    if not fuentes:
        raise RuntimeError("No se detectaron fuentes CONAFOR en el directorio especificado.")

    filas_esquema_totales: list[dict] = []
    filas_resumen_totales: list[dict] = []

    for fuente in fuentes:
        print(f"\nProcesando: {fuente['nombre_fuente']} ({fuente['tipo']})")
        path = fuente["path"]

        if not path.exists():
            print(f"  - No encontrado: {path}")
            filas_resumen_totales.append({
                "fuente": fuente["nombre_fuente"],
                "grupo_fuente": fuente["grupo_fuente"],
                "formato": fuente["tipo"],
                "ruta": str(path),
                "tipo_geometria": None,
                "registros": None,
                "columnas": None,
                "campos_fecha": None,
                "campos_temporal_anual": None,
                "campos_geograficos": None,
                "campos_identificador": None,
                "campos_categoricos": None,
                "campos_numericos": None,
                "campos_texto_libre": None,
                "campos_vacios": None,
            })
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
                formato = "shp"

            elif fuente["tipo"] == "xlsx":
                df, meta = leer_excel_limpio(path)
                tipo_geometria = None
                formato = "xlsx"

            else:  # csv
                df, meta = leer_csv_limpio(path)
                tipo_geometria = None
                formato = "csv"

            filas_esquema, resumen = perfilar_dataframe(
                df=df,
                nombre_fuente=fuente["nombre_fuente"],
                grupo_fuente=fuente["grupo_fuente"],
                formato=formato,
                ruta=str(path),
                tipo_geometria=tipo_geometria,
            )
            filas_esquema_totales.extend(filas_esquema)
            filas_resumen_totales.append(resumen)

        except Exception as e:
            print(f"  - Error: {e}")
            filas_resumen_totales.append({
                "fuente": fuente["nombre_fuente"],
                "grupo_fuente": fuente["grupo_fuente"],
                "formato": fuente["tipo"],
                "ruta": str(path),
                "tipo_geometria": None,
                "registros": None,
                "columnas": None,
                "campos_fecha": None,
                "campos_temporal_anual": None,
                "campos_geograficos": None,
                "campos_identificador": None,
                "campos_categoricos": None,
                "campos_numericos": None,
                "campos_texto_libre": None,
                "campos_vacios": None,
            })

    df_esquema = pd.DataFrame(filas_esquema_totales)
    df_resumen = pd.DataFrame(filas_resumen_totales)

    cols_esquema = [
        "fuente", "grupo_fuente", "formato", "ruta",
        "tipo_geometria", "campo", "tipo_original",
        "tipo_inferido", "rol_campo", "n_registros_fuente",
        "nulos", "pct_nulos", "cardinalidad", "ejemplos",
    ]
    if not df_esquema.empty:
        df_esquema = df_esquema.reindex(columns=cols_esquema)
        df_esquema = df_esquema.sort_values(by=["fuente", "campo"])

    cols_resumen = [
        "fuente", "grupo_fuente", "formato", "ruta",
        "tipo_geometria", "registros", "columnas",
        "campos_fecha", "campos_temporal_anual", "campos_geograficos",
        "campos_identificador", "campos_categoricos", "campos_numericos",
        "campos_texto_libre", "campos_vacios",
    ]
    if not df_resumen.empty:
        df_resumen = df_resumen.reindex(columns=cols_resumen)
        df_resumen = df_resumen.sort_values(by=["grupo_fuente", "fuente"])

    df_esquema.to_csv(CSV_ESQUEMA, index=False, encoding="utf-8-sig")
    df_resumen.to_csv(CSV_RESUMEN, index=False, encoding="utf-8-sig")

    print("\nArchivos generados:")
    print(f"  {CSV_ESQUEMA}")
    print(f"  {CSV_RESUMEN}")
    print("\nProceso terminado.")


if __name__ == "__main__":
    main()