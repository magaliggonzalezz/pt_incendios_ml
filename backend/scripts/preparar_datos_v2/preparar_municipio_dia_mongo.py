from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd


def normalizar_codigo(valor, ancho: int) -> str | None:
    if pd.isna(valor):
        return None
    texto = str(valor).strip()
    if texto.endswith(".0"):
        texto = texto[:-2]
    return texto.zfill(ancho)


def normalizar_valor(valor):
    if pd.isna(valor):
        return None
    if hasattr(valor, "item"):
        try:
            return valor.item()
        except ValueError:
            pass
    return valor


def convertir_archivo(origen: Path, destino: Path, chunksize: int) -> dict:
    destino.parent.mkdir(parents=True, exist_ok=True)
    temporal = destino.with_suffix(destino.suffix + ".part")
    if temporal.exists():
        temporal.unlink()

    filas = 0
    with temporal.open("w", encoding="utf-8", newline="\n") as salida:
        for chunk in pd.read_csv(origen, chunksize=chunksize, low_memory=False):
            for columna, ancho in (("cve_ent", 2), ("cve_mun", 3), ("cvegeo", 5)):
                if columna in chunk.columns:
                    chunk[columna] = chunk[columna].map(lambda v: normalizar_codigo(v, ancho))

            if "fecha" in chunk.columns:
                chunk["fecha"] = pd.to_datetime(chunk["fecha"], errors="coerce").dt.strftime("%Y-%m-%d")

            registros = chunk.to_dict(orient="records")
            for registro in registros:
                limpio = {clave: normalizar_valor(valor) for clave, valor in registro.items()}
                salida.write(json.dumps(limpio, ensure_ascii=False, separators=(",", ":")))
                salida.write("\n")

            filas += len(chunk)

    temporal.replace(destino)
    return {
        "origen": str(origen),
        "destino": str(destino),
        "filas": filas,
        "bytes": destino.stat().st_size,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Prepara los resultados municipio-día anuales como JSONL para mongoimport."
    )
    parser.add_argument("--base-dir", default=".", help="Raíz del repositorio")
    parser.add_argument(
        "--output-dir",
        default="data_v2_mongo_ready/resultados_municipio_dia",
        help="Directorio de salida relativo a la raíz",
    )
    parser.add_argument("--anio", type=int, help="Procesa solo un año")
    parser.add_argument("--chunksize", type=int, default=100_000)
    args = parser.parse_args()

    base = Path(args.base_dir).resolve()
    origen_dir = base / "ms04_evaluation" / "app_ready" / "csv" / "municipio_dia"
    salida_dir = base / args.output_dir

    if not origen_dir.is_dir():
        raise FileNotFoundError(f"No existe: {origen_dir}")

    patron = (
        f"app_municipio_dia_resultados_{args.anio}.csv"
        if args.anio
        else "app_municipio_dia_resultados_*.csv"
    )
    archivos = sorted(origen_dir.glob(patron))
    if not archivos:
        raise FileNotFoundError(f"No se encontraron archivos con patrón: {patron}")

    reporte = []
    for origen in archivos:
        anio = origen.stem.rsplit("_", 1)[-1]
        destino = salida_dir / f"resultados_municipio_dia_{anio}.jsonl"
        print(f"Procesando {origen.name} -> {destino.name}")
        datos = convertir_archivo(origen, destino, args.chunksize)
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
