from __future__ import annotations

import argparse
import math
from pathlib import Path
from statistics import mean

import pyarrow.parquet as pq

from preparar_datos_v2.preparar_municipio_dia_mongo import transformar_registro

try:
    from bson import BSON, ObjectId
except ImportError as exc:
    raise SystemExit(
        "Falta pymongo para calcular tamaño BSON real. Instala con: pip install pymongo"
    ) from exc


TOTAL_FILAS_ESPERADAS = 22_626_618
FLEX_BYTES = 5 * 1024**3
DEFAULT_STORAGE_GB = 10.0


def encontrar_raiz(inicio: Path) -> Path:
    for candidato in [inicio.resolve(), *inicio.resolve().parents]:
        if (candidato / "data_deploy" / "resultados" / "municipio_dia").exists():
            return candidato
    raise FileNotFoundError("No se encontró data_deploy/resultados/municipio_dia")


def documento_desde_tabla(tabla, indice: int) -> dict:
    registro = {
        nombre: tabla[nombre][indice].as_py()
        for nombre in tabla.column_names
    }
    doc = transformar_registro(registro)
    return {"_id": ObjectId(), **doc}


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
        description=(
            "Estima el tamaño BSON real del esquema compacto de resultados_municipio_dia "
            "y lo compara con el almacenamiento actualmente asignado en Atlas."
        )
    )
    parser.add_argument(
        "--muestra-por-anio",
        type=int,
        default=2000,
        help="Documentos BSON a muestrear por archivo anual (default: 2000).",
    )
    parser.add_argument(
        "--storage-gb",
        type=float,
        default=DEFAULT_STORAGE_GB,
        help=(
            "Almacenamiento asignado actualmente al cluster Atlas en GB decimales "
            "(default: 10). No representa un límite fijo del tier M10."
        ),
    )
    parser.add_argument(
        "--margen-pct",
        type=float,
        default=20.0,
        help=(
            "Margen orientativo para índice compuesto y overhead de almacenamiento "
            "(default: 20)."
        ),
    )
    args = parser.parse_args()

    if args.storage_gb <= 0:
        parser.error("--storage-gb debe ser mayor que 0")
    if args.margen_pct < 0:
        parser.error("--margen-pct no puede ser negativo")

    raiz = encontrar_raiz(Path.cwd())
    carpeta = raiz / "data_deploy" / "resultados" / "municipio_dia"
    archivos = sorted(carpeta.glob("app_municipio_dia_resultados_*.parquet"))
    if not archivos:
        raise FileNotFoundError(f"No se encontraron Parquet en {carpeta}")

    todas_medidas: list[int] = []
    filas_totales = 0

    print(f"Archivos encontrados: {len(archivos)}")
    print(f"Muestra objetivo por año: {args.muestra_por_anio:,}")
    print(f"Storage Atlas asignado para comparación: {args.storage_gb:.2f} GB\n")

    for path in archivos:
        filas, medidas = estimar_archivo(path, args.muestra_por_anio)
        filas_totales += filas
        todas_medidas.extend(medidas)
        promedio = mean(medidas) if medidas else 0
        print(f"{path.name}: {filas:,} filas | BSON compacto promedio muestra: {promedio:.1f} B")

    if not todas_medidas:
        raise RuntimeError("No se pudo obtener ninguna muestra BSON")

    promedio_bson = mean(todas_medidas)
    minimo = min(todas_medidas)
    maximo = max(todas_medidas)
    estimado_datos = promedio_bson * filas_totales
    margen = estimado_datos * (args.margen_pct / 100)
    estimado_con_margen = estimado_datos + margen
    storage_asignado = args.storage_gb * 1_000_000_000
    ocupacion_proyectada = (estimado_con_margen / storage_asignado) * 100

    print("\n=== RESULTADO ===")
    print(f"Filas reales detectadas: {filas_totales:,}")
    if filas_totales != TOTAL_FILAS_ESPERADAS:
        print(f"Aviso: se esperaban {TOTAL_FILAS_ESPERADAS:,} filas según la auditoría previa.")
    print(f"Documentos muestreados: {len(todas_medidas):,}")
    print(f"BSON compacto por documento: promedio {promedio_bson:.1f} B | min {minimo} B | max {maximo} B")
    print(f"Datos BSON proyectados: {formato_bytes(estimado_datos)}")
    print(
        f"Proyección + {args.margen_pct:.1f}% orientativo para índice/overhead: "
        f"{formato_bytes(estimado_con_margen)}"
    )
    print(f"Flex (5 GiB): {'CABE por estimación' if estimado_con_margen < FLEX_BYTES else 'NO CABE por estimación'}")
    print(f"Storage Atlas indicado: {args.storage_gb:.2f} GB")
    print(f"Ocupación proyectada sobre ese storage: {ocupacion_proyectada:.1f}%")

    if estimado_con_margen >= storage_asignado:
        print(
            "Estado: STORAGE INSUFICIENTE para la proyección. Amplía el almacenamiento "
            "antes del bulk import; no dependas de que el auto-scaling reaccione durante la carga."
        )
    elif ocupacion_proyectada >= 80:
        print(
            "Estado: STORAGE MUY AJUSTADO. Conviene ampliar almacenamiento antes del bulk import "
            "para dejar margen operativo a datos, índices y oplog."
        )
    else:
        print("Estado: CAPACIDAD PRELIMINAR SUFICIENTE para esta proyección.")

    print(
        "\nNota: M10 no se modela aquí como un límite fijo de 10 GB. "
        "La decisión final depende del storage realmente asignado al cluster y debe confirmarse "
        "con storageSize y totalIndexSize después de una importación piloto."
    )


if __name__ == "__main__":
    main()
