from __future__ import annotations

import argparse
import json
from pathlib import Path

import pyarrow.parquet as pq


CAMPOS_CATALOGO = {
    "estado",
    "municipio",
    "municipio_area_km2",
}

CAMPOS_CLUSTER = {
    "estado_app",
    "etiqueta_final",
    "color_sugerido_app",
    "prioridad_visual_app",
}


def normalizar_codigo(valor, ancho: int, campo: str) -> str:
    if valor is None:
        raise ValueError(f"{campo} no puede estar vacío")

    texto = str(valor).strip()
    if texto.endswith(".0") and texto[:-2].isdigit():
        texto = texto[:-2]

    if not texto.isdigit():
        raise ValueError(f"{campo} debe ser numérico; recibido: {valor!r}")
    if len(texto) > ancho:
        raise ValueError(f"{campo} excede {ancho} caracteres: {valor!r}")

    return texto.zfill(ancho)


def normalizar_valor(valor):
    if hasattr(valor, "as_py"):
        valor = valor.as_py()
    if hasattr(valor, "isoformat"):
        return valor.isoformat()
    return valor


def transformar_registro(registro: dict) -> dict:
    salida = {clave: normalizar_valor(valor) for clave, valor in registro.items()}

    cve_ent = normalizar_codigo(salida.get("cve_ent"), 2, "cve_ent")
    cve_mun = normalizar_codigo(salida.get("cve_mun"), 3, "cve_mun")
    cvegeo = normalizar_codigo(salida.get("cvegeo"), 5, "cvegeo")

    if cvegeo != f"{cve_ent}{cve_mun}":
        raise ValueError(f"cvegeo inconsistente: {cvegeo} != {cve_ent}{cve_mun}")

    fecha = salida.get("fecha")
    if fecha in (None, ""):
        raise ValueError("fecha no puede estar vacía")
    fecha = str(fecha)[:10]

    cluster = salida.pop("cluster_som_k07", None)
    if cluster in (None, ""):
        raise ValueError("cluster_som_k07 no puede estar vacío")

    salida["cve_ent"] = cve_ent
    salida["cve_mun"] = cve_mun
    salida["cvegeo"] = cvegeo
    salida["fecha"] = fecha
    salida["cluster"] = int(cluster)

    for campo in CAMPOS_CATALOGO | CAMPOS_CLUSTER:
        salida.pop(campo, None)

    return salida


def convertir_archivo(origen: Path, destino: Path, batch_size: int) -> dict:
    destino.parent.mkdir(parents=True, exist_ok=True)
    temporal = destino.with_suffix(destino.suffix + ".part")
    if temporal.exists():
        temporal.unlink()

    parquet = pq.ParquetFile(origen)
    filas = 0

    with temporal.open("w", encoding="utf-8", newline="\n") as salida:
        for batch in parquet.iter_batches(batch_size=batch_size):
            for registro in batch.to_pylist():
                limpio = transformar_registro(registro)
                salida.write(json.dumps(limpio, ensure_ascii=False, separators=(",", ":")))
                salida.write("\n")
                filas += 1

            if filas and filas % 500_000 < batch.num_rows:
                print(f"  {filas:,} registros preparados")

    temporal.replace(destino)
    return {
        "origen": str(origen),
        "destino": str(destino),
        "filas": filas,
        "bytes": destino.stat().st_size,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Prepara los Parquet deploy municipio-día existentes como JSONL compactos "
            "para mongoimport, sin regenerar los datasets fuente."
        )
    )
    parser.add_argument("--base-dir", default=".", help="Raíz del repositorio")
    parser.add_argument(
        "--input-dir",
        default="data_deploy/resultados/municipio_dia",
        help="Directorio de Parquet deploy relativo a la raíz",
    )
    parser.add_argument(
        "--output-dir",
        default="data_v2_mongo_ready/resultados_municipio_dia",
        help="Directorio de salida relativo a la raíz",
    )
    parser.add_argument("--anio", type=int, help="Procesa solo un año")
    parser.add_argument("--batch-size", type=int, default=100_000)
    args = parser.parse_args()

    base = Path(args.base_dir).resolve()
    origen_dir = base / args.input_dir
    salida_dir = base / args.output_dir

    if not origen_dir.is_dir():
        raise FileNotFoundError(f"No existe: {origen_dir}")

    patron = (
        f"app_municipio_dia_resultados_{args.anio}.parquet"
        if args.anio
        else "app_municipio_dia_resultados_*.parquet"
    )
    archivos = sorted(origen_dir.glob(patron))
    if not archivos:
        raise FileNotFoundError(f"No se encontraron archivos con patrón: {patron}")

    reporte = []
    for origen in archivos:
        anio = origen.stem.rsplit("_", 1)[-1]
        destino = salida_dir / f"resultados_municipio_dia_{anio}.jsonl"
        print(f"Procesando {origen.name} -> {destino.name}")
        datos = convertir_archivo(origen, destino, args.batch_size)
        reporte.append(datos)
        print(f"  {datos['filas']:,} filas | {datos['bytes'] / (1024**2):.2f} MiB")

    reporte_path = salida_dir / "reporte_municipio_dia_mongo.json"
    reporte_path.write_text(
        json.dumps(reporte, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"\nReporte: {reporte_path}")
    print(f"Total filas: {sum(x['filas'] for x in reporte):,}")


if __name__ == "__main__":
    main()
