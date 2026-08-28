from __future__ import annotations

import json
from pathlib import Path

import pyarrow.parquet as pq


CANDIDATOS = {
    "firms": [
        "data_deploy/fuentes/firms/firms_detecciones.parquet",
    ],
    "conafor": [
        "data_deploy/fuentes/conafor/conafor_incendios_eventos.parquet",
    ],
}


def encontrar_raiz(inicio: Path) -> Path:
    for candidato in [inicio.resolve(), *inicio.resolve().parents]:
        if (candidato / "data_deploy").exists():
            return candidato
    raise FileNotFoundError("No se encontró la raíz del repositorio")


def bytes_legibles(num_bytes: int) -> str:
    unidades = ["B", "KiB", "MiB", "GiB"]
    valor = float(num_bytes)
    for unidad in unidades:
        if valor < 1024 or unidad == unidades[-1]:
            return f"{valor:.2f} {unidad}"
        valor /= 1024
    return f"{num_bytes} B"


def resolver_archivo(raiz: Path, rutas: list[str]) -> Path:
    existentes = [raiz / ruta for ruta in rutas if (raiz / ruta).is_file()]
    if len(existentes) != 1:
        raise FileNotFoundError(
            "No se encontró exactamente un archivo esperado entre: "
            + ", ".join(rutas)
        )
    return existentes[0]


def detectar_columnas(columnas: list[str], candidatos: list[str]) -> list[str]:
    mapa = {c.lower(): c for c in columnas}
    return [mapa[c] for c in candidatos if c in mapa]


def main() -> None:
    raiz = encontrar_raiz(Path.cwd())
    reporte = {"fuentes": []}

    print("=== AUDITORÍA FIRMS / CONAFOR ===\n")

    for fuente, rutas in CANDIDATOS.items():
        path = resolver_archivo(raiz, rutas)
        parquet = pq.ParquetFile(path)
        columnas = parquet.schema_arrow.names
        filas = parquet.metadata.num_rows
        grupos = parquet.num_row_groups

        lat_cols = detectar_columnas(columnas, ["latitude", "latitud", "lat", "y"])
        lon_cols = detectar_columnas(columnas, ["longitude", "longitud", "lon", "lng", "x"])
        fecha_cols = detectar_columnas(
            columnas,
            ["fecha", "acq_date", "fecha_inicio", "fecha_reporte", "fecha_evento"],
        )
        estado_cols = detectar_columnas(columnas, ["cve_ent", "estado", "entidad", "nom_ent"])
        municipio_cols = detectar_columnas(
            columnas,
            ["cvegeo", "cve_mun", "municipio", "nom_mun"],
        )

        print(f"{fuente.upper()}")
        print(f"  Archivo: {path.relative_to(raiz)}")
        print(f"  Tamaño: {bytes_legibles(path.stat().st_size)}")
        print(f"  Filas: {filas:,}")
        print(f"  Row groups: {grupos}")
        print(f"  Columnas ({len(columnas)}): {', '.join(columnas)}")
        print(f"  Latitud candidata: {lat_cols or 'NO'}")
        print(f"  Longitud candidata: {lon_cols or 'NO'}")
        print(f"  Fecha candidata: {fecha_cols or 'NO'}")
        print(f"  Estado candidato: {estado_cols or 'NO'}")
        print(f"  Municipio candidato: {municipio_cols or 'NO'}")
        print()

        reporte["fuentes"].append(
            {
                "fuente": fuente,
                "archivo": str(path.relative_to(raiz)),
                "bytes": path.stat().st_size,
                "filas": filas,
                "row_groups": grupos,
                "columnas": columnas,
                "candidatas": {
                    "latitud": lat_cols,
                    "longitud": lon_cols,
                    "fecha": fecha_cols,
                    "estado": estado_cols,
                    "municipio": municipio_cols,
                },
            }
        )

    salida = raiz / "data_deploy" / "reporte_fuentes_puntuales_r2.json"
    salida.write_text(json.dumps(reporte, ensure_ascii=False, indent=2), encoding="utf-8")

    print("========================================")
    print(f"Reporte: {salida.relative_to(raiz)}")
    print("No se modificó ni se subió ningún dataset.")


if __name__ == "__main__":
    main()
