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
OUT_RELATIVE = Path("data_deploy/capas_web/inegi/relieve_mde")
WEB_CRS = "EPSG:3857"
TILE_SIZE = 256
BUFFER = 1


def encontrar_raiz(inicio: Path) -> Path:
    for candidato in [inicio.resolve(), *inicio.resolve().parents]:
        if (candidato / MDE_RELATIVE).is_file():
            return candidato
    raise FileNotFoundError(f"No se encontró {MDE_RELATIVE}")


def bytes_legibles(value: int) -> str:
    unidades = ["B", "KiB", "MiB", "GiB"]
    size = float(value)
    for unidad in unidades:
        if size < 1024 or unidad == unidades[-1]:
            return f"{size:.2f} {unidad}"
        size /= 1024
    return f"{value} B"


def hillshade(elevation: np.ndarray, xres: float, yres: float) -> np.ndarray:
    elev = elevation.astype("float32", copy=False)
    dy, dx = np.gradient(elev, abs(yres), abs(xres))
    slope = np.pi / 2.0 - np.arctan(np.sqrt(dx * dx + dy * dy))
    aspect = np.arctan2(-dx, dy)

    azimuth = np.deg2rad(315.0)
    altitude = np.deg2rad(45.0)
    shaded = (
        np.sin(altitude) * np.sin(slope)
        + np.cos(altitude) * np.cos(slope) * np.cos(azimuth - aspect)
    )
    shaded = np.clip((shaded + 1.0) * 127.5, 0, 255)
    return shaded.astype("uint8")


def tile_bounds_mercator(tile: mercantile.Tile) -> tuple[float, float, float, float]:
    bounds = mercantile.xy_bounds(tile)
    return bounds.left, bounds.bottom, bounds.right, bounds.top


def render_tile(src: rasterio.io.DatasetReader, tile: mercantile.Tile) -> Image.Image | None:
    left, bottom, right, top = tile_bounds_mercator(tile)
    pixel_x = (right - left) / TILE_SIZE
    pixel_y = (top - bottom) / TILE_SIZE

    expanded_left = left - BUFFER * pixel_x
    expanded_right = right + BUFFER * pixel_x
    expanded_bottom = bottom - BUFFER * pixel_y
    expanded_top = top + BUFFER * pixel_y
    size = TILE_SIZE + BUFFER * 2

    dst_transform = rasterio.transform.from_bounds(
        expanded_left,
        expanded_bottom,
        expanded_right,
        expanded_top,
        size,
        size,
    )
    elevation = np.full((size, size), np.nan, dtype="float32")

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

    safe_elevation = np.where(mask, 0.0, elevation)
    hs = hillshade(safe_elevation, dst_transform.a, dst_transform.e)

    if BUFFER:
        hs = hs[BUFFER:-BUFFER, BUFFER:-BUFFER]
        mask = mask[BUFFER:-BUFFER, BUFFER:-BUFFER]

    alpha = np.where(mask, 0, 185).astype("uint8")
    rgba = np.dstack([hs, hs, hs, alpha])
    return Image.fromarray(rgba, mode="RGBA")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Genera tiles XYZ PNG de relieve sombreado a partir del MDE INEGI."
    )
    parser.add_argument("--zoom-min", type=int, default=4)
    parser.add_argument("--zoom-max", type=int, default=10)
    parser.add_argument("--recrear", action="store_true")
    args = parser.parse_args()

    if args.zoom_min < 0 or args.zoom_max < args.zoom_min:
        raise ValueError("Rango de zoom inválido")

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

            print(f"  escritos={zoom_written:,} | vacíos={zoom_empty:,}")
            por_zoom[str(zoom)] = {
                "candidatos": len(tiles),
                "escritos": zoom_written,
                "vacios": zoom_empty,
            }

    manifest = {
        "capa": "relieve_mde_inegi",
        "fuente": MDE_RELATIVE.as_posix(),
        "producto": "hillshade XYZ PNG",
        "zoom_min": args.zoom_min,
        "zoom_max": args.zoom_max,
        "tile_size": TILE_SIZE,
        "crs_fuente_esperado": "EPSG:6365",
        "nodata_fuente_esperado": 32767,
        "crs_tiles": WEB_CRS,
        "azimuth_deg": 315,
        "altitude_deg": 45,
        "alpha_valida": 185,
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

    print("\n=== RELIEVE MDE GENERADO ===")
    print(f"Tiles escritos: {escritos:,}")
    print(f"Tiles existentes omitidos: {omitidos_existentes:,}")
    print(f"Tiles vacíos: {vacios:,}")
    print(f"Tamaño: {bytes_legibles(total_bytes)}")
    print(f"Manifest: {manifest_path.relative_to(raiz)}")
    print("No se modificó el TIFF original.")


if __name__ == "__main__":
    main()
