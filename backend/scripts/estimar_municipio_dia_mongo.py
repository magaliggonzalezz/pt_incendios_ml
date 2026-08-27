from __future__ import annotations

import argparse
import math
from pathlib import Path
from statistics import mean

import pyarrow.parquet as pq

try:
    from bson import BSON, ObjectId
except ImportError as exc:
    raise SystemExit(
        "Falta pymongo para calcular tamaño BSON real. Instala con: pip install pymongo"
    ) from exc


TOTAL_FILAS_ESPERADAS = 22_626_618
FLEX_BYTES = 5 * 1024**3
M10_BYTES = 10 * 1024**3


def encontrar_raiz(inicio: Path) -> Path:
    for candidato in [inicio.resolve(), *inicio.resolve().parents]:
        if (candidato / "data_deploy" / "resultados" / "municipio_dia").exists():
            return candidato
    raise FileNotFoundError("No se encontró data_deploy/resultados/municipio_dia")


def normalizar_valor(valor):
    if hasattr(valor, "as_py"):
        valor = valor.as_py()
    if hasattr(valor, "isoformat"):
        return valor.isoformat()
    return valor


def documento_desde_tabla(tabla, indice: int) -> dict:
    doc = {"_id": ObjectId()}
    for nombre in tabla.column_names:
        doc[nombre] = normalizar_valor(tabla[nombre][indice])
    return doc


def formato_bytes(valor: float) -> str:
    unidades = ["B", "KiB", "MiB", "GiB", "TiB"]
    i = 0
    while valor >= 1024 and i < len(unidades) - 1:
        valor /= 1024
        i += 1
    return f"{valor:.2f} {unidades[i]}"


def estimar_archivo(path: Path, muestra_objetivo: int) -> tuple[int, list[int]]:
    parquet = pq.ParquetFile(path)
    total = parquet.metadata.num_rows
    tamanos: list[int] = []
    restantes = muestra_objetivo

    for rg in range(parquet.num_row_groups):
        if restantes <= 0:
            break
        tabla = parquet.read_row_group(rg)
        tomar = min(restantes, tabla.num_rows)
        if tomar <= 0:
            continue

        paso = max(1, math.floor(tabla.num_rows / tomar))
        indices = list(range(0, tabla.num_rows, paso))[:tomar]
        for indice in indices:
            tamanos.append(len(BSON.encode(documento_desde_tabla(tabla, indice))))
        restantes -= len(indices)

    return total, tamanos


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Estima el tamaño BSON de resultados_municipio_dia para elegir Atlas Flex o M10."
    )
    parser.add_argument(
        "--muestra-por-anio",
        type=int,
        default=2000,
        help="Documentos BSON a muestrear por archivo anual (default: 2000).",
    )
    args = parser.parse_args()

    raiz = encontrar_raiz(Path.cwd())
    carpeta = raiz / "data_deploy" / "resultados" / "municipio_dia"
    archivos = sorted(carpeta.glob("app_municipio_dia_resultados_*.parquet"))
    if not archivos:
        raise FileNotFoundError(f"No se encontraron Parquet en {carpeta}")

    todas_medidas: list[int] = []
    filas_totales = 0

    print(f"Archivos encontrados: {len(archivos)}")
    print(f"Muestra objetivo por año: {args.muestra_por_anio:,}\n")

    for path in archivos:
        filas, medidas = estimar_archivo(path, args.muestra_por_anio)
        filas_totales += filas
        todas_medidas.extend(medidas)
        promedio = mean(medidas) if medidas else 0
        print(f"{path.name}: {filas:,} filas | BSON promedio muestra: {promedio:.1f} B")

    if not todas_medidas:
        raise RuntimeError("No se pudo obtener ninguna muestra BSON")

    promedio_bson = mean(todas_medidas)
    minimo = min(todas_medidas)
    maximo = max(todas_medidas)
    estimado_datos = promedio_bson * filas_totales

    # Margen orientativo para índice compuesto cvegeo+fecha y overhead de almacenamiento.
    # No pretende sustituir storageSize/totalIndexSize reales de MongoDB.
    margen_indice_20 = estimado_datos * 0.20
    estimado_con_margen = estimado_datos + margen_indice_20

    print("\n=== RESULTADO ===")
    print(f"Filas reales detectadas: {filas_totales:,}")
    if filas_totales != TOTAL_FILAS_ESPERADAS:
        print(f"Aviso: se esperaban {TOTAL_FILAS_ESPERADAS:,} filas según la auditoría previa.")
    print(f"Documentos muestreados: {len(todas_medidas):,}")
    print(f"BSON por documento: promedio {promedio_bson:.1f} B | min {minimo} B | max {maximo} B")
    print(f"Datos BSON proyectados: {formato_bytes(estimado_datos)}")
    print(f"Proyección + 20% orientativo para índice/overhead: {formato_bytes(estimado_con_margen)}")
    print(f"Flex (5 GiB): {'CABE por estimación' if estimado_con_margen < FLEX_BYTES else 'NO CABE por estimación'}")
    print(f"M10 (10 GiB): {'CABE por estimación' if estimado_con_margen < M10_BYTES else 'REQUIERE REVISIÓN / MÁS ALMACENAMIENTO'}")
    print("\nNota: la decisión final debe confirmarse con storageSize y totalIndexSize tras una importación piloto; esta prueba evita elegir tier a ciegas.")


if __name__ == "__main__":
    main()
