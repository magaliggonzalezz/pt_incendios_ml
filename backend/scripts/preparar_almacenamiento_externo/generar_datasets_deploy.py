from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

try:
    import pandas as pd
except ImportError as exc:
    raise SystemExit(
        "Falta pandas. Instala dependencias con: python -m pip install pandas pyarrow"
    ) from exc

try:
    import pyarrow as pa
    import pyarrow.parquet as pq
except ImportError as exc:
    raise SystemExit(
        "Falta pyarrow. Instálalo con: python -m pip install pyarrow"
    ) from exc


COLUMNAS_DERIVABLES_TEMPORALES = {"anio", "mes"}


def bytes_legibles(num_bytes: int) -> str:
    unidades = ["B", "KiB", "MiB", "GiB", "TiB"]
    valor = float(num_bytes)
    for unidad in unidades:
        if valor < 1024 or unidad == unidades[-1]:
            return f"{valor:.2f} {unidad}"
        valor /= 1024
    return f"{num_bytes} B"


def asegurar_padre(ruta: Path) -> None:
    ruta.parent.mkdir(parents=True, exist_ok=True)


def alinear_tabla_al_esquema(tabla: pa.Table, esquema: pa.Schema) -> pa.Table:
    """Alinea tipos entre chunks cuando pandas infiere int/float distinto.

    Es común en CSV grandes que una columna sea int64 en un bloque y float64 en
    otro solo porque aparecen nulos. Parquet exige un esquema fijo por archivo.
    """
    if tabla.schema.equals(esquema, check_metadata=False):
        return tabla.cast(esquema, safe=False)

    columnas = []
    for campo in esquema:
        columna = tabla[campo.name]
        if columna.type != campo.type:
            columna = columna.cast(campo.type, safe=False)
        columnas.append(columna)

    return pa.Table.from_arrays(columnas, schema=esquema)


def convertir_csv_a_parquet(
    origen: Path,
    destino: Path,
    *,
    eliminar_columnas: set[str] | None = None,
    chunksize: int = 150_000,
) -> dict:
    asegurar_padre(destino)
    eliminar_columnas = eliminar_columnas or set()

    # Se escribe primero a .part para nunca dejar un parquet final incompleto.
    temporal = destino.with_suffix(destino.suffix + ".part")
    if temporal.exists():
        temporal.unlink()

    writer = None
    esquema_base = None
    filas = 0
    columnas_finales = None

    try:
        for chunk in pd.read_csv(origen, chunksize=chunksize, low_memory=False):
            columnas_a_eliminar = [c for c in eliminar_columnas if c in chunk.columns]
            if columnas_a_eliminar:
                chunk = chunk.drop(columns=columnas_a_eliminar)

            tabla = pa.Table.from_pandas(chunk, preserve_index=False)

            if writer is None:
                esquema_base = tabla.schema
                writer = pq.ParquetWriter(
                    temporal,
                    esquema_base,
                    compression="zstd",
                    compression_level=6,
                    use_dictionary=True,
                )
                columnas_finales = list(chunk.columns)
            else:
                tabla = alinear_tabla_al_esquema(tabla, esquema_base)

            writer.write_table(tabla)
            filas += len(chunk)

        if writer is None:
            # CSV sin filas: conserva al menos el esquema.
            df = pd.read_csv(origen, nrows=0)
            columnas_a_eliminar = [c for c in eliminar_columnas if c in df.columns]
            if columnas_a_eliminar:
                df = df.drop(columns=columnas_a_eliminar)
            df.to_parquet(temporal, index=False, compression="zstd")
            columnas_finales = list(df.columns)
        else:
            writer.close()
            writer = None

        temporal.replace(destino)

    except Exception:
        if writer is not None:
            writer.close()
        if temporal.exists():
            temporal.unlink()
        raise

    return {
        "origen": str(origen),
        "destino": str(destino),
        "filas": filas,
        "columnas": columnas_finales,
        "bytes_origen": origen.stat().st_size,
        "bytes_destino": destino.stat().st_size,
        "estado": "generado",
    }


def registrar_parquet_existente(origen: Path, destino: Path) -> dict:
    """Registra un parquet ya generado sin volver a procesar el CSV."""
    if not destino.is_file():
        raise FileNotFoundError(
            f"Se pidió reanudar, pero falta el archivo ya generado: {destino}"
        )

    parquet = pq.ParquetFile(destino)
    return {
        "origen": str(origen),
        "destino": str(destino),
        "filas": parquet.metadata.num_rows,
        "columnas": parquet.schema_arrow.names,
        "bytes_origen": origen.stat().st_size,
        "bytes_destino": destino.stat().st_size,
        "estado": "reutilizado",
    }


def copiar_archivo(origen: Path, destino: Path) -> dict:
    asegurar_padre(destino)
    shutil.copy2(origen, destino)
    return {
        "origen": str(origen),
        "destino": str(destino),
        "bytes_origen": origen.stat().st_size,
        "bytes_destino": destino.stat().st_size,
        "estado": "generado",
    }


def validar_archivo(ruta: Path) -> None:
    if not ruta.is_file():
        raise FileNotFoundError(f"No existe el archivo requerido: {ruta}")


def procesar_o_reutilizar(
    *,
    etapa: int,
    desde_etapa: int,
    origen: Path,
    destino: Path,
    eliminar_columnas: set[str],
    chunksize: int,
) -> dict:
    if etapa < desde_etapa:
        print(f"  [reutiliza] {destino.name}")
        return registrar_parquet_existente(origen, destino)

    print(f"  {origen.name}")
    return convertir_csv_a_parquet(
        origen,
        destino,
        eliminar_columnas=eliminar_columnas,
        chunksize=chunksize,
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Genera una versión de despliegue optimizada para almacenamiento externo, "
            "sin modificar los archivos originales."
        )
    )
    parser.add_argument(
        "--base-dir",
        default=".",
        help="Raíz del repositorio (por defecto, directorio actual).",
    )
    parser.add_argument(
        "--output-dir",
        default="data_deploy",
        help="Directorio de salida relativo a base-dir.",
    )
    parser.add_argument(
        "--chunksize",
        type=int,
        default=150_000,
        help="Filas por bloque al convertir CSV grandes a Parquet.",
    )
    parser.add_argument(
        "--desde-etapa",
        type=int,
        choices=range(1, 6),
        default=1,
        metavar="N",
        help=(
            "Reanuda desde la etapa N (1-5). Las etapas anteriores se reutilizan "
            "desde data_deploy sin reconvertirlas."
        ),
    )
    args = parser.parse_args()

    base = Path(args.base_dir).resolve()
    salida = (base / args.output_dir).resolve()
    salida.mkdir(parents=True, exist_ok=True)

    ruta_resultados = base / "ms04_evaluation" / "app_ready" / "csv" / "municipio_dia"
    ruta_exportacion = base / "ms04_evaluation" / "app_ready" / "csv" / "exportacion"
    ruta_layers = base / "ms02_procesamiento" / "04_integration" / "layers"

    if not ruta_resultados.is_dir():
        raise FileNotFoundError(f"No existe: {ruta_resultados}")
    if not ruta_exportacion.is_dir():
        raise FileNotFoundError(f"No existe: {ruta_exportacion}")
    if not ruta_layers.is_dir():
        raise FileNotFoundError(f"No existe: {ruta_layers}")

    reporte = {
        "criterios": {
            "originales_modificados": False,
            "compresion_parquet": "zstd nivel 6",
            "municipio_dia": "Parquet anual; se eliminan anio y mes porque se derivan de fecha/partición.",
            "exportacion": "Parquet anual detallado; se eliminan solo anio y mes, conservando el resto para descarga analítica.",
            "firms": "Solo dataset completo canónico; no se duplican versiones anuales ni GeoJSON.",
            "conafor": "Solo dataset completo canónico; no se duplican versiones anuales ni GeoJSON.",
            "inegi": "Se conserva contexto municipal agregado; capas fuente pesadas quedan fuera del deploy por ahora.",
            "smn": "Se conserva GeoJSON de estaciones por ser una capa ligera y directamente visualizable.",
            "geometrias_inegi": "Pendientes de optimización web específica (no se copian todavía).",
            "desde_etapa": args.desde_etapa,
        },
        "archivos": [],
        "excluidos_deploy": [],
    }

    print("\n[1/5] Resultados municipio-día -> Parquet")
    for origen in sorted(ruta_resultados.glob("app_municipio_dia_resultados_*.csv")):
        destino = salida / "resultados" / "municipio_dia" / f"{origen.stem}.parquet"
        reporte["archivos"].append(
            {
                "categoria": "resultados_municipio_dia",
                **procesar_o_reutilizar(
                    etapa=1,
                    desde_etapa=args.desde_etapa,
                    origen=origen,
                    destino=destino,
                    eliminar_columnas=COLUMNAS_DERIVABLES_TEMPORALES,
                    chunksize=args.chunksize,
                ),
            }
        )

    print("\n[2/5] Exportación detallada -> Parquet")
    for origen in sorted(ruta_exportacion.glob("app_municipio_dia_detalle_exportacion_*.csv")):
        destino = salida / "exportaciones" / "municipio_dia_detalle" / f"{origen.stem}.parquet"
        reporte["archivos"].append(
            {
                "categoria": "exportacion_municipio_dia_detalle",
                **procesar_o_reutilizar(
                    etapa=2,
                    desde_etapa=args.desde_etapa,
                    origen=origen,
                    destino=destino,
                    eliminar_columnas=COLUMNAS_DERIVABLES_TEMPORALES,
                    chunksize=args.chunksize,
                ),
            }
        )

    print("\n[3/5] Fuentes canónicas FIRMS y CONAFOR -> Parquet")
    fuentes = [
        (
            "firms",
            ruta_layers / "firms" / "firms_detecciones.csv",
            salida / "fuentes" / "firms" / "firms_detecciones.parquet",
        ),
        (
            "conafor",
            ruta_layers / "conafor" / "conafor_incendios_eventos.csv",
            salida / "fuentes" / "conafor" / "conafor_incendios_eventos.parquet",
        ),
    ]
    for categoria, origen, destino in fuentes:
        validar_archivo(origen)
        reporte["archivos"].append(
            {
                "categoria": f"fuente_{categoria}_canonica",
                **procesar_o_reutilizar(
                    etapa=3,
                    desde_etapa=args.desde_etapa,
                    origen=origen,
                    destino=destino,
                    eliminar_columnas=set(),
                    chunksize=args.chunksize,
                ),
            }
        )

    print("\n[4/5] Contexto INEGI agregado -> Parquet")
    inegi_contexto = ruta_layers / "inegi" / "inegi_contexto_municipal.csv"
    validar_archivo(inegi_contexto)
    destino_inegi = salida / "contexto" / "inegi_contexto_municipal.parquet"
    reporte["archivos"].append(
        {
            "categoria": "contexto_inegi_municipal",
            **procesar_o_reutilizar(
                etapa=4,
                desde_etapa=args.desde_etapa,
                origen=inegi_contexto,
                destino=destino_inegi,
                eliminar_columnas=set(),
                chunksize=args.chunksize,
            ),
        }
    )

    print("\n[5/5] Capa ligera SMN -> GeoJSON")
    smn_geojson = ruta_layers / "smn" / "smn_estaciones.geojson"
    validar_archivo(smn_geojson)
    destino_smn = salida / "capas_web" / "smn" / "smn_estaciones.geojson"
    if args.desde_etapa > 5:
        # No ocurre con choices 1-5; se deja explícito por consistencia.
        datos_smn = {
            "origen": str(smn_geojson),
            "destino": str(destino_smn),
            "bytes_origen": smn_geojson.stat().st_size,
            "bytes_destino": destino_smn.stat().st_size,
            "estado": "reutilizado",
        }
    else:
        datos_smn = copiar_archivo(smn_geojson, destino_smn)
    reporte["archivos"].append(
        {
            "categoria": "capa_web_smn_estaciones",
            **datos_smn,
        }
    )

    reporte["excluidos_deploy"].extend(
        [
            {
                "patron": "layers/firms/firms_detecciones_YYYY.(csv|geojson)",
                "motivo": "Duplican temporalmente el dataset completo canónico FIRMS.",
            },
            {
                "patron": "layers/firms/firms_detecciones.geojson",
                "motivo": "Duplica atributos del canónico y es demasiado pesado para servirse directamente como GeoJSON web.",
            },
            {
                "patron": "layers/conafor/conafor_incendios_eventos_YYYY.(csv|geojson)",
                "motivo": "Duplican temporalmente el dataset completo canónico CONAFOR.",
            },
            {
                "patron": "layers/conafor/conafor_incendios_eventos.geojson",
                "motivo": "Duplica atributos del canónico; la representación web se definirá por separado.",
            },
            {
                "patron": "layers/inegi/*.geojson",
                "motivo": "Capas fuente grandes; se conserva el contexto municipal agregado. Las geometrías necesarias para mapa se optimizarán aparte.",
            },
            {
                "patron": "layers/smn/smn_estaciones.csv",
                "motivo": "La capa GeoJSON es pequeña y suficiente para visualización; evita mantener ambas representaciones en deploy.",
            },
        ]
    )

    total_origen_referenciado = sum(x["bytes_origen"] for x in reporte["archivos"])
    total_deploy = sum(x["bytes_destino"] for x in reporte["archivos"])
    reduccion = (
        (1 - total_deploy / total_origen_referenciado) * 100
        if total_origen_referenciado
        else 0.0
    )

    reporte["resumen"] = {
        "archivos_generados_o_reutilizados": len(reporte["archivos"]),
        "bytes_origen_referenciado": total_origen_referenciado,
        "tamano_origen_referenciado": bytes_legibles(total_origen_referenciado),
        "bytes_deploy": total_deploy,
        "tamano_deploy": bytes_legibles(total_deploy),
        "reduccion_por_compresion_y_limpieza_pct": round(reduccion, 2),
        "nota": (
            "La reducción no incluye todavía la optimización de geometrías INEGI/FIRMS/CONAFOR para web; "
            "esas capas se decidirán después de medir este deploy base."
        ),
    }

    reporte_path = salida / "reporte_generacion_deploy.json"
    reporte_path.write_text(json.dumps(reporte, ensure_ascii=False, indent=2), encoding="utf-8")

    print("\n===================================")
    print("DEPLOY BASE GENERADO")
    print("===================================")
    print(f"Archivos: {len(reporte['archivos']):,}")
    print(f"Origen referenciado: {bytes_legibles(total_origen_referenciado)}")
    print(f"Deploy:             {bytes_legibles(total_deploy)}")
    print(f"Reducción:          {reduccion:.2f}%")
    print(f"Reporte:            {reporte_path}")
    print("\nLos originales no fueron modificados.")


if __name__ == "__main__":
    main()
