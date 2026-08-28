from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

try:
    import geopandas as gpd
except ImportError as exc:
    raise SystemExit("Falta geopandas. Instálalo con: python -m pip install geopandas") from exc

from shapely.geometry import box


def bytes_legibles(num_bytes: int) -> str:
    unidades = ["B", "KiB", "MiB", "GiB"]
    valor = float(num_bytes)
    for unidad in unidades:
        if valor < 1024 or unidad == unidades[-1]:
            return f"{valor:.2f} {unidad}"
        valor /= 1024
    return f"{num_bytes} B"


def encontrar_raiz(inicio: Path) -> Path:
    for candidato in [inicio.resolve(), *inicio.resolve().parents]:
        if (candidato / "data_deploy" / "capas_web").exists():
            return candidato
    raise FileNotFoundError("No se encontró la raíz del repositorio")


def localizar_piloto(raiz: Path, capa: str, cve_ent: str, tolerancia: int) -> Path:
    carpeta = (
        raiz
        / "data_deploy"
        / "capas_web"
        / "pilotos_simplificacion"
        / capa
        / cve_ent
    )
    candidatos = sorted(carpeta.glob(f"*{tolerancia}m*.geojson"))
    if len(candidatos) != 1:
        raise FileNotFoundError(
            f"No se encontró exactamente un piloto de {tolerancia} m en {carpeta}. "
            "Ejecuta primero evaluar_simplificacion_capa_tematica.py."
        )
    return candidatos[0]


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Evalúa dividir una copia simplificada de una capa temática en mosaicos regulares. "
            "No modifica ni sustituye capas existentes."
        )
    )
    parser.add_argument("--capa", required=True)
    parser.add_argument("--cve-ent", required=True)
    parser.add_argument("--tolerancia", type=int, default=25)
    parser.add_argument(
        "--grados",
        type=float,
        default=1.0,
        help="Tamaño del lado de cada mosaico en grados (default: 1.0).",
    )
    args = parser.parse_args()

    cve_ent = str(args.cve_ent).zfill(2)
    raiz = encontrar_raiz(Path.cwd())
    origen = localizar_piloto(raiz, args.capa, cve_ent, args.tolerancia)

    print(f"Leyendo {origen.name} ({bytes_legibles(origen.stat().st_size)})...")
    gdf = gpd.read_file(origen)
    if gdf.crs is None:
        raise RuntimeError("La capa no tiene CRS")
    if str(gdf.crs).upper() != "EPSG:4326":
        gdf = gdf.to_crs(4326)

    minx, miny, maxx, maxy = gdf.total_bounds
    paso = float(args.grados)
    x0 = math.floor(minx / paso) * paso
    y0 = math.floor(miny / paso) * paso
    x1 = math.ceil(maxx / paso) * paso
    y1 = math.ceil(maxy / paso) * paso

    salida = (
        raiz
        / "data_deploy"
        / "capas_web"
        / "pilotos_tiling"
        / args.capa
        / cve_ent
        / f"{args.tolerancia}m_{paso:g}deg"
    )
    salida.mkdir(parents=True, exist_ok=True)

    indice = gdf.sindex
    tiles = []
    tile_id = 0

    y = y0
    while y < y1:
        x = x0
        while x < x1:
            geom_tile = box(x, y, x + paso, y + paso)
            candidatos = list(indice.query(geom_tile, predicate="intersects"))
            if candidatos:
                subset = gdf.iloc[candidatos].copy()
                subset.geometry = subset.geometry.intersection(geom_tile)
                subset = subset[subset.geometry.notna() & ~subset.geometry.is_empty].copy()
                if len(subset):
                    tile_id += 1
                    nombre = f"tile_{tile_id:03d}.geojson"
                    destino = salida / nombre
                    subset.to_file(destino, driver="GeoJSON")
                    size = destino.stat().st_size
                    tiles.append(
                        {
                            "tile": nombre,
                            "bbox": [x, y, x + paso, y + paso],
                            "features": int(len(subset)),
                            "bytes": size,
                        }
                    )
            x += paso
        y += paso

    if not tiles:
        raise RuntimeError("No se generó ningún mosaico")

    tamanos = [x["bytes"] for x in tiles]
    reporte = {
        "capa": args.capa,
        "cve_ent": cve_ent,
        "tolerancia_m": args.tolerancia,
        "tile_grados": paso,
        "origen": str(origen.relative_to(raiz)),
        "bytes_origen": origen.stat().st_size,
        "tiles": tiles,
        "resumen": {
            "cantidad_tiles": len(tiles),
            "bytes_total_tiles": sum(tamanos),
            "bytes_min": min(tamanos),
            "bytes_max": max(tamanos),
            "bytes_promedio": sum(tamanos) / len(tamanos),
        },
        "criterios": {
            "fuente_maestra_modificada": False,
            "piloto_simplificado_reemplazado": False,
            "operacion": "interseccion espacial en mosaicos regulares para evaluar entrega por viewport",
        },
    }

    reporte_path = salida / "reporte_tiling.json"
    reporte_path.write_text(json.dumps(reporte, ensure_ascii=False, indent=2), encoding="utf-8")

    print("\n=== RESULTADO TILING ===")
    print(f"Tiles: {len(tiles)}")
    print(f"Total tiles: {bytes_legibles(sum(tamanos))}")
    print(f"Promedio: {bytes_legibles(sum(tamanos) / len(tamanos))}")
    print(f"Máximo: {bytes_legibles(max(tamanos))}")
    print(f"Mínimo: {bytes_legibles(min(tamanos))}")
    print(f"Reporte: {reporte_path.relative_to(raiz)}")
    print("No se sustituyó ni se subió ninguna capa a R2.")


if __name__ == "__main__":
    main()
