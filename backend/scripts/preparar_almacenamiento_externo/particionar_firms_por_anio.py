from __future__ import annotations

import json
from pathlib import Path

import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.parquet as pq


ANIO_MIN = 2001
ANIO_MAX = 2025


def encontrar_raiz(inicio: Path) -> Path:
    for candidato in [inicio.resolve(), *inicio.resolve().parents]:
        if (candidato / "data_deploy" / "fuentes" / "firms" / "firms_detecciones.parquet").is_file():
            return candidato
    raise FileNotFoundError("No se encontró data_deploy/fuentes/firms/firms_detecciones.parquet")


def bytes_legibles(num_bytes: int) -> str:
    unidades = ["B", "KiB", "MiB", "GiB"]
    valor = float(num_bytes)
    for unidad in unidades:
        if valor < 1024 or unidad == unidades[-1]:
            return f"{valor:.2f} {unidad}"
        valor /= 1024
    return f"{num_bytes} B"


def main() -> None:
    raiz = encontrar_raiz(Path.cwd())
    origen = raiz / "data_deploy" / "fuentes" / "firms" / "firms_detecciones.parquet"
    salida = raiz / "data_deploy" / "capas_web" / "puntos" / "firms"
    salida.mkdir(parents=True, exist_ok=True)

    parquet = pq.ParquetFile(origen)
    schema = parquet.schema_arrow
    if "anio" not in schema.names:
        raise RuntimeError("El Parquet FIRMS no contiene la columna anio")

    escritores: dict[int, pq.ParquetWriter] = {}
    filas: dict[int, int] = {anio: 0 for anio in range(ANIO_MIN, ANIO_MAX + 1)}

    print(f"Origen: {origen.relative_to(raiz)}")
    print(f"Filas: {parquet.metadata.num_rows:,}")
    print(f"Row groups: {parquet.num_row_groups}")
    print("Particionando por año sin eliminar columnas...\n")

    try:
        for i, batch in enumerate(parquet.iter_batches(batch_size=100_000), start=1):
            tabla = pa.Table.from_batches([batch])
            anios_presentes = pc.unique(tabla["anio"]).to_pylist()

            for valor in anios_presentes:
                if valor is None:
                    continue
                anio = int(valor)
                if not (ANIO_MIN <= anio <= ANIO_MAX):
                    continue

                mascara = pc.equal(tabla["anio"], anio)
                subset = tabla.filter(mascara)
                if subset.num_rows == 0:
                    continue

                if anio not in escritores:
                    path = salida / f"firms_detecciones_{anio}.parquet"
                    escritores[anio] = pq.ParquetWriter(
                        path,
                        subset.schema,
                        compression="zstd",
                        use_dictionary=True,
                    )

                escritores[anio].write_table(subset)
                filas[anio] += subset.num_rows

            if i % 10 == 0:
                print(f"  Batches procesados: {i}")
    finally:
        for writer in escritores.values():
            writer.close()

    total_salida = 0
    reporte_anios = []
    print("\n=== PARTICIONES FIRMS ===")
    for anio in range(ANIO_MIN, ANIO_MAX + 1):
        path = salida / f"firms_detecciones_{anio}.parquet"
        if not path.is_file():
            raise RuntimeError(f"No se generó la partición esperada: {path.name}")

        metadata = pq.ParquetFile(path).metadata
        if metadata.num_rows != filas[anio]:
            raise RuntimeError(
                f"Conteo inconsistente en {anio}: escrito={filas[anio]}, metadata={metadata.num_rows}"
            )

        size = path.stat().st_size
        total_salida += size
        print(f"{anio}: {filas[anio]:,} filas | {bytes_legibles(size)}")
        reporte_anios.append(
            {
                "anio": anio,
                "filas": filas[anio],
                "bytes": size,
                "archivo": str(path.relative_to(raiz)),
            }
        )

    total_filas = sum(filas.values())
    if total_filas != parquet.metadata.num_rows:
        raise RuntimeError(
            f"La suma de las particiones ({total_filas:,}) no coincide con el origen ({parquet.metadata.num_rows:,})"
        )

    reporte = {
        "origen": str(origen.relative_to(raiz)),
        "filas_origen": parquet.metadata.num_rows,
        "bytes_origen": origen.stat().st_size,
        "criterios": {
            "columnas_eliminadas": False,
            "filas_eliminadas": False,
            "operacion": "particion por anio para entrega eficiente al mapa",
            "compresion_salida": "zstd",
        },
        "particiones": reporte_anios,
        "filas_salida": total_filas,
        "bytes_salida": total_salida,
    }
    reporte_path = salida / "manifest.json"
    reporte_path.write_text(json.dumps(reporte, ensure_ascii=False, indent=2), encoding="utf-8")

    print("\n========================================")
    print(f"Filas verificadas: {total_filas:,}")
    print(f"Tamaño origen: {bytes_legibles(origen.stat().st_size)}")
    print(f"Tamaño particiones: {bytes_legibles(total_salida)}")
    print(f"Manifest: {reporte_path.relative_to(raiz)}")
    print("No se modificó el Parquet FIRMS original.")


if __name__ == "__main__":
    main()
