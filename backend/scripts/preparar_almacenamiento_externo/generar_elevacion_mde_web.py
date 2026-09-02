from __future__ import annotations

import argparse
import json
from pathlib import Path

try:
    import mercantile
    import numpy as np
    import rasterio
    from PIL import Image
    from rasterio.enums import Resampling
    from rasterio.warp import reproject, transform_bounds
except ImportError as exc:
    raise SystemExit(
        "Faltan dependencias. Instala con: "
        "python -m pip install rasterio numpy pillow mercantile"
    ) from exc


MDE_RELATIVE = Path(
    "ms01_recoleccion/01_raw-data/inegi/modelos_digitales_de_elevacion/"
    "conjunto_de_datos/continuonacional_15m.tif"
)
OUT_RELATIVE = Path("data_deploy/capas_web/inegi/elevacion_mde")
WEB_CRS = "EPSG:3857"
TILE_SIZE = 256

# Rangos hipsometricos pensados para lectura cartografica en Mexico.
# El valor superior es exclusivo, salvo el ultimo rango.
ELEVATION_CLASSES = [
    {"min": -500, "max": 500, "label": "Menos de 500 m", "color": "#2E8B57"},
    {"min": 500, "max": 1000, "label": "500-999 m", "color": "#66A95C"},
    {"min": 1000, "max": 1500, "label": "1,000-1,499 m", "color": "#A8C66C"},
    {"min": 1500, "max": 2000, "label": "1,500-1,999 m", "color": "#D8D36F"},
    {"min": 2000, "max": 2500, "label": "2,000-2,499 m", "color": "#D8A85C"},
    {"min": 2500, "max": 3000, "label": "2,500-2,999 m", "color": "#B97A56"},
    {"min": 3000, "max": 3500, "label": "3,000-3,499 m", "color": "#8C5A4A"},
    {"min": 3500, "max": 9000, "label": "3,500 m o mas", "color": "#F1F5F9"},
]


def encontrar_raiz(inicio: Path) -> Path:
    for candidato in [inicio.resolve(), *inicio.resolve().parents]:
        if (candidato / MDE_RELATIVE).is_file():
            return candidato
    raise FileNotFoundError(f"No se encontro {MDE_RELATIVE}")


def bytes_legibles(value: int) -> str:
    unidades = ["B", "KiB", "MiB", "GiB"]
    size = float(value)
    for unidad in unidades:
        if size < 1024 or unidad == unidades[-1]:
            return f"{size:.2f} {unidad}"
        size /= 1024
    return f"{value} B"


def hex_to_rgb(value: str) -> tuple[int, int, int]:
    text = value.lstrip("#")
    return tuple(int(text[index:index + 2], 16) for index in (0, 2, 4))


def clasificar_elevacion(elevation: np.ndarray, mask: np.ndarray) -> np.ndarray:
    rgba = np.zeros((*elevation.shape, 4), dtype="uint8")

    for clase in ELEVATION_CLASSES:
        class_mask = (
            ~mask
            & (elevation >= clase["min"])
            & (elevation < clase["max"])
        )
        color = hex_to_rgb(clase["color"])
        rgba[class_mask, 0] = color[0]
        rgba[class_mask, 1] = color[1]
        rgba[class_mask, 2] = color[2]
        rgba[class_mask, 3] = 210

    # Cualquier valor valido fuera de los limites definidos conserva la clase extrema.
    low_mask = ~mask & (elevation < ELEVATION_CLASSES[0]["min"])
    high_mask = ~mask & (elevation >= ELEVATION_CLASSES[-1]["max"])
    low_color = hex_to_rgb(ELEVATION_CLASSES[0]["color"])
    high_color = hex_to_rgb(ELEVATION_CLASSES[-1]["color"])

    rgba[low_mask, :3] = low_color
    rgba[low_mask, 3] = 210
    rgba[high_mask, :3] = high_color
    rgba[high_mask, 3] = 210

    return rgba


def tile_bounds_mercator(tile: mercantile.Tile) -> tuple[float, float, float, float]:
    bounds = mercantile.xy_bounds(tile)
    return bounds.left, bounds.bottom, bounds.right, bounds.top


def render_tile(src: rasterio.io.DatasetReader, tile: mercantile.Tile) -> Image.Image | None:
    left, bottom, right, top = tile_bounds_mercator(tile)
    dst_transform = rasterio.transform.from_bounds(
        left,
        bottom,
        right,
        top,
        TILE_SIZE,
        TILE_SIZE,
    )
    elevation = np.full((TILE_SIZE, TILE_SIZE), np.nan, dtype="float32")

    reproject(
        source=rasterio.band(src, 1),
        destination=elevation,
        src_transform=src.transform,
        src_crs=src.crs,
        src_nodata=src.nodata,
        dst_transform=dst_transform,
        dst_crs=WEB_CRS,
        dst_nodata=np.nan,
        resampling=Resampling.bilinear,
    )

    mask = ~np.isfinite(elevation)
    if mask.all():
        return None

    rgba = clasificar_elevacion(elevation, mask)
    return Image.fromarray(rgba, mode="RGBA")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Genera tiles XYZ PNG de elevacion hipsometrica a partir del MDE INEGI."
    )
    parser.add_argument("--zoom-min", type=int, default=4)
    parser.add_argument("--zoom-max", type=int, default=10)
    parser.add_argument("--recrear", action="store_true")
    args = parser.parse_args()

    if args.zoom_min < 0 or args.zoom_max < args.zoom_min:
        raise ValueError("Rango de zoom invalido")

    raiz = encontrar_raiz(Path.cwd())
    mde = raiz / MDE_RELATIVE
    salida = raiz / OUT_RELATIVE
    salida.mkdir(parents=True, exist_ok=True)

    print(f"MDE: {mde.relative_to(raiz)}")
    print(f"Salida: {salida.relative_to(raiz)}")
    print(f"Zoom: {args.zoom_min}-{args.zoom_max}")

    total_tiles = 0
    escritos = 0
    omitidos_existentes = 0
    vacios = 0
    total_bytes = 0
    por_zoom = {}

    with rasterio.open(mde) as src:
        if src.crs is None:
            raise RuntimeError("El MDE no tiene CRS")
        if src.count != 1:
            raise RuntimeError(f"Se esperaba 1 banda y el MDE tiene {src.count}")
        if src.nodata != 32767:
            raise RuntimeError(f"NoData inesperado: {src.nodata}; se esperaba 32767")
        if src.crs.to_epsg() != 6365:
            raise RuntimeError(f"EPSG inesperado: {src.crs.to_epsg()}; se esperaba 6365")

        lonlat_bounds = transform_bounds(
            src.crs,
            "EPSG:4326",
            *src.bounds,
            densify_pts=21,
        )
        west, south, east, north = lonlat_bounds
        west = max(-180.0, west)
        east = min(180.0, east)
        south = max(-85.05112878, south)
        north = min(85.05112878, north)

        for zoom in range(args.zoom_min, args.zoom_max + 1):
            tiles = list(mercantile.tiles(west, south, east, north, [zoom]))
            zoom_written = 0
            zoom_empty = 0
            print(f"\nZoom {zoom}: {len(tiles):,} tiles candidatos")

            for index, tile in enumerate(tiles, 1):
                total_tiles += 1
                destino = salida / str(tile.z) / str(tile.x) / f"{tile.y}.png"

                if destino.is_file() and not args.recrear:
                    omitidos_existentes += 1
                    total_bytes += destino.stat().st_size
                    continue

                image = render_tile(src, tile)
                if image is None:
                    vacios += 1
                    zoom_empty += 1
                    continue

                destino.parent.mkdir(parents=True, exist_ok=True)
                image.save(destino, format="PNG", optimize=True, compress_level=9)
                escritos += 1
                zoom_written += 1
                total_bytes += destino.stat().st_size

                if index % 250 == 0 or index == len(tiles):
                    print(f"  {index:,}/{len(tiles):,}", end="\r")

            print(f"  escritos={zoom_written:,} | vacios={zoom_empty:,}")
            por_zoom[str(zoom)] = {
                "candidatos": len(tiles),
                "escritos": zoom_written,
                "vacios": zoom_empty,
            }

    manifest = {
        "capa": "elevacion_mde_inegi",
        "fuente": MDE_RELATIVE.as_posix(),
        "producto": "elevacion hipsometrica XYZ PNG",
        "unidad": "m s. n. m.",
        "zoom_min": args.zoom_min,
        "zoom_max": args.zoom_max,
        "tile_size": TILE_SIZE,
        "crs_fuente_esperado": "EPSG:6365",
        "nodata_fuente_esperado": 32767,
        "crs_tiles": WEB_CRS,
        "clases": ELEVATION_CLASSES,
        "alpha_valida": 210,
        "tiles_candidatos": total_tiles,
        "tiles_escritos": escritos,
        "tiles_omitidos_existentes": omitidos_existentes,
        "tiles_vacios": vacios,
        "bytes_total": total_bytes,
        "por_zoom": por_zoom,
        "fuente_original_modificada": False,
    }
    manifest_path = salida / "manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print("\n=== ELEVACION MDE GENERADA ===")
    print(f"Tiles escritos: {escritos:,}")
    print(f"Tiles existentes omitidos: {omitidos_existentes:,}")
    print(f"Tiles vacios: {vacios:,}")
    print(f"Tamano: {bytes_legibles(total_bytes)}")
    print(f"Manifest: {manifest_path.relative_to(raiz)}")
    print("No se modifico el TIFF original.")


if __name__ == "__main__":
    main()
