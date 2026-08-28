from __future__ import annotations

import argparse
import json
import math
import shutil
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
        if (candidato / "data_deploy" / "capas_web" / "inegi" / "tematicas").exists():
            return candidato
    raise FileNotFoundError("No se encontró la raíz del repositorio")


def crs_metrico_aproximado(gdf: gpd.GeoDataFrame):
    crs = gdf.estimate_utm_crs()
    if crs is None:
        raise RuntimeError("No fue posible estimar un CRS métrico para simplificación")
    return crs


def simplificar(gdf: gpd.GeoDataFrame, tolerancia_m: float) -> gpd.GeoDataFrame:
    if tolerancia_m <= 0:
        return gdf.copy()

    original_crs = gdf.crs
    metrico = gdf.to_crs(crs_metrico_aproximado(gdf))
    simplificada = metrico.copy()
    simplificada.geometry = metrico.geometry.simplify(tolerancia_m, preserve_topology=True)
    simplificada = simplificada[~simplificada.geometry.is_empty & simplificada.geometry.notna()].copy()
    simplificada = simplificada.to_crs(original_crs)

    invalidas = int((~simplificada.geometry.is_valid).sum())
    if invalidas:
        raise RuntimeError(f"La simplificación produjo {invalidas} geometrías inválidas")
    return simplificada


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Genera tiles GeoJSON de despliegue a partir de una partición estatal temática. "
            "La capa maestra y la partición estatal no se modifican."
        )
    )
    parser.add_argument("--capa", required=True)
    parser.add_argument("--cve-ent", required=True)
    parser.add_argument("--tolerancia", type=float, default=25.0)
    parser.add_argument("--grados", type=float, default=1.0)
    parser.add_argument("--recrear", action="store_true")
    args = parser.parse_args()

    cve_ent = str(args.cve_ent).zfill(2)
    raiz = encontrar_raiz(Path.cwd())
    base = raiz / "data_deploy" / "capas_web" / "inegi" / "tematicas"
    origen = base / args.capa / f"{args.capa}_{cve_ent}.geojson"
    if not origen.is_file():
        raise FileNotFoundError(f"No existe la partición estatal: {origen}")

    salida = (
        raiz
        / "data_deploy"
        / "capas_web"
        / "inegi"
        / "tiles"
        / args.capa
        / cve_ent
    )
    if salida.exists() and args.recrear:
        shutil.rmtree(salida)
    salida.mkdir(parents=True, exist_ok=True)

    print(f"Leyendo {origen.name} ({bytes_legibles(origen.stat().st_size)})...")
    gdf = gpd.read_file(origen)
    if gdf.crs is None:
        raise RuntimeError("La capa no tiene CRS")
    if str(gdf.crs).upper() != "EPSG:4326":
        gdf = gdf.to_crs(4326)

    print(f"Simplificando copia de despliegue a {args.tolerancia:g} m...")
    web = simplificar(gdf, args.tolerancia)

    paso = float(args.grados)
    minx, miny, maxx, maxy = web.total_bounds
    x0 = math.floor(minx / paso) * paso
    y0 = math.floor(miny / paso) * paso
    x1 = math.ceil(maxx / paso) * paso
    y1 = math.ceil(maxy / paso) * paso

    indice = web.sindex
    tiles = []
    iy = 0
    y = y0
    while y < y1:
        ix = 0
        x = x0
        while x < x1:
            geom_tile = box(x, y, x + paso, y + paso)
            candidatos = list(indice.query(geom_tile, predicate="intersects"))
            if candidatos:
                subset = web.iloc[candidatos].copy()
                subset.geometry = subset.geometry.intersection(geom_tile)
                subset = subset[subset.geometry.notna() & ~subset.geometry.is_empty].copy()
                if len(subset):
                    tile_id = f"x{ix:02d}_y{iy:02d}"
                    nombre = f"{args.capa}_{cve_ent}_{tile_id}.geojson"
                    destino = salida / nombre
                    subset.to_file(destino, driver="GeoJSON")
                    invalidas = int((~gpd.read_file(destino).geometry.is_valid).sum())
                    if invalidas:
                        raise RuntimeError(f"{nombre}: {invalidas} geometrías inválidas")
                    tiles.append(
                        {
                            "id": tile_id,
                            "archivo": nombre,
                            "bbox": [x, y, x + paso, y + paso],
                            "features": int(len(subset)),
                            "bytes": destino.stat().st_size,
                        }
                    )
            ix += 1
            x += paso
        iy += 1
        y += paso

    if not tiles:
        raise RuntimeError("No se generó ningún tile")

    manifest = {
        "capa": args.capa,
        "cve_ent": cve_ent,
        "tolerancia_m": args.tolerancia,
        "tile_grados": paso,
        "bbox_estado": [float(minx), float(miny), float(maxx), float(maxy)],
        "tiles": tiles,
        "resumen": {
            "cantidad_tiles": len(tiles),
            "features_origen_estado": int(len(gdf)),
            "features_simplificadas": int(len(web)),
            "bytes_origen_estado": origen.stat().st_size,
            "bytes_total_tiles": sum(x["bytes"] for x in tiles),
            "bytes_max_tile": max(x["bytes"] for x in tiles),
            "bytes_promedio_tile": sum(x["bytes"] for x in tiles) / len(tiles),
        },
        "criterios": {
            "fuente_maestra_modificada": False,
            "particion_estatal_modificada": False,
            "simplificacion_preserva_topologia": True,
            "tiles_recortados_por_bbox": True,
        },
    }

    manifest_path = salida / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    print("\n=== TILES DE DESPLIEGUE GENERADOS ===")
    print(f"Tiles: {len(tiles)}")
    print(f"Total: {bytes_legibles(manifest['resumen']['bytes_total_tiles'])}")
    print(f"Promedio: {bytes_legibles(manifest['resumen']['bytes_promedio_tile'])}")
    print(f"Máximo: {bytes_legibles(manifest['resumen']['bytes_max_tile'])}")
    print(f"Manifest: {manifest_path.relative_to(raiz)}")
    print("No se modificó la capa maestra ni la partición estatal original.")


if __name__ == "__main__":
    main()
