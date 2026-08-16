# -*- coding: utf-8 -*-
"""
Evaluation 07 | Inventario de assets locales

Este script:
- Mide archivos locales sin leer su contenido.
- Detecta outputs grandes de municipio-dia segmentados por anio.
- Resume app_ready.
- Clasifica capas FIRMS, CONAFOR, SMN e INEGI por nombre/ruta.
- Permite agregar raices de busqueda externas al repositorio.
- Genera un CSV local de inventario (ignorado por .gitignore por ser *.csv).

Ejemplos:
    python 07_inventariar_assets_locales.py

    python 07_inventariar_assets_locales.py --root "C:\\ruta\\a\\capas"

    python 07_inventariar_assets_locales.py \
        --root "C:\\ruta\\a\\FIRMS" \
        --root "D:\\datos\\INEGI"
"""

from __future__ import annotations

import argparse
import csv
import re
from collections import defaultdict
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
EVALUATION_DIR = PROJECT_ROOT / "07_evaluation"
REPORTS_DIR = EVALUATION_DIR / "reports"
DEFAULT_OUTPUT = REPORTS_DIR / "inventario_assets_locales.csv"

YEAR_MIN = 2001
YEAR_MAX = 2025

RESULTADOS_RE = re.compile(r"^app_municipio_dia_resultados_(20\d{2})\.csv$", re.IGNORECASE)
DETALLE_RE = re.compile(
    r"^app_municipio_dia_detalle_exportacion_(20\d{2})\.csv$",
    re.IGNORECASE,
)

SKIP_DIRS = {
    ".git",
    ".venv",
    "venv",
    "env",
    "node_modules",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
}

LAYER_KEYWORDS = {
    "firms": ("firms",),
    "conafor": ("conafor",),
    "smn": ("smn",),
    "inegi": ("inegi", "inegi_capas_limpias"),
}


# ============================================================
# Utilidades
# ============================================================

def format_bytes(size: int) -> str:
    units = ("B", "KiB", "MiB", "GiB", "TiB")
    value = float(size)

    for unit in units:
        if value < 1024 or unit == units[-1]:
            return f"{value:.2f} {unit}"
        value /= 1024

    return f"{size} B"


def safe_resolve(path: Path) -> Path:
    try:
        return path.expanduser().resolve()
    except OSError:
        return path.expanduser().absolute()


def is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
        return True
    except ValueError:
        return False


def classify_file(path: Path) -> tuple[str, int | None]:
    name = path.name

    match = RESULTADOS_RE.match(name)
    if match:
        return "ml_resultados_municipio_dia", int(match.group(1))

    match = DETALLE_RE.match(name)
    if match:
        return "ml_detalle_exportacion", int(match.group(1))

    app_ready = EVALUATION_DIR / "app_ready"
    if is_relative_to(path, app_ready):
        return "app_ready", None

    searchable = str(path).lower()
    for category, keywords in LAYER_KEYWORDS.items():
        if any(keyword in searchable for keyword in keywords):
            return category, None

    return "otros", None


def iter_files(root: Path):
    if root.is_file():
        yield root
        return

    if not root.exists() or not root.is_dir():
        return

    for current in root.rglob("*"):
        if any(part.lower() in SKIP_DIRS for part in current.parts):
            continue
        if current.is_file():
            yield current


def should_include(path: Path, category: str) -> bool:
    if category != "otros":
        return True

    # Para la raiz del proyecto no queremos inventariar todo el codigo fuente.
    # Solo conservamos formatos tipicamente asociados a assets de datos.
    return path.suffix.lower() in {
        ".csv",
        ".json",
        ".geojson",
        ".gpkg",
        ".shp",
        ".dbf",
        ".shx",
        ".prj",
        ".tif",
        ".tiff",
        ".parquet",
        ".pmtiles",
        ".mbtiles",
        ".zip",
    }


def collect_inventory(roots: list[Path]) -> list[dict]:
    rows: list[dict] = []
    seen: set[Path] = set()

    for root in roots:
        resolved_root = safe_resolve(root)

        if not resolved_root.exists():
            print(f"[AVISO] No existe la raiz: {resolved_root}")
            continue

        print(f"Escaneando: {resolved_root}")

        for path in iter_files(resolved_root):
            resolved_path = safe_resolve(path)
            if resolved_path in seen:
                continue
            seen.add(resolved_path)

            category, year = classify_file(resolved_path)
            if not should_include(resolved_path, category):
                continue

            try:
                size = resolved_path.stat().st_size
            except OSError as exc:
                print(f"[AVISO] No se pudo medir {resolved_path}: {exc}")
                continue

            rows.append(
                {
                    "categoria": category,
                    "anio": year or "",
                    "archivo": resolved_path.name,
                    "extension": resolved_path.suffix.lower(),
                    "tamano_bytes": size,
                    "tamano_mib": round(size / (1024**2), 3),
                    "tamano_gib": round(size / (1024**3), 6),
                    "ruta": str(resolved_path),
                    "raiz_busqueda": str(resolved_root),
                }
            )

    rows.sort(key=lambda row: (row["categoria"], str(row["anio"]), row["archivo"]))
    return rows


def write_csv(rows: list[dict], output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = [
        "categoria",
        "anio",
        "archivo",
        "extension",
        "tamano_bytes",
        "tamano_mib",
        "tamano_gib",
        "ruta",
        "raiz_busqueda",
    ]

    with output.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def print_summary(rows: list[dict]) -> None:
    grouped: dict[str, dict[str, int]] = defaultdict(lambda: {"files": 0, "bytes": 0})

    for row in rows:
        category = row["categoria"]
        grouped[category]["files"] += 1
        grouped[category]["bytes"] += int(row["tamano_bytes"])

    print("\nResumen por categoria")
    print("-" * 72)
    print(f"{'Categoria':32} {'Archivos':>10} {'Tamano':>24}")
    print("-" * 72)

    total_files = 0
    total_bytes = 0

    for category in sorted(grouped):
        files = grouped[category]["files"]
        size = grouped[category]["bytes"]
        total_files += files
        total_bytes += size
        print(f"{category:32} {files:>10} {format_bytes(size):>24}")

    print("-" * 72)
    print(f"{'TOTAL':32} {total_files:>10} {format_bytes(total_bytes):>24}")

    print_annual_summary(rows, "ml_resultados_municipio_dia", "Resultados municipio-dia")
    print_annual_summary(rows, "ml_detalle_exportacion", "Detalle de exportacion")


def print_annual_summary(rows: list[dict], category: str, label: str) -> None:
    annual = [row for row in rows if row["categoria"] == category and row["anio"] != ""]

    if not annual:
        print(f"\n{label}: no se encontraron archivos anuales.")
        return

    by_year: dict[int, int] = {}
    for row in annual:
        year = int(row["anio"])
        by_year[year] = by_year.get(year, 0) + int(row["tamano_bytes"])

    expected_years = set(range(YEAR_MIN, YEAR_MAX + 1))
    present_years = set(by_year)
    missing_years = sorted(expected_years - present_years)
    sizes = list(by_year.values())

    print(f"\n{label}")
    print(f"  Anios encontrados: {len(present_years)}/{len(expected_years)}")
    print(f"  Total: {format_bytes(sum(sizes))}")
    print(f"  Minimo anual: {format_bytes(min(sizes))}")
    print(f"  Maximo anual: {format_bytes(max(sizes))}")
    print(f"  Promedio anual: {format_bytes(sum(sizes) // len(sizes))}")

    if missing_years:
        print("  Anios faltantes: " + ", ".join(map(str, missing_years)))
    else:
        print("  Anios faltantes: ninguno")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Inventaria tamanos de outputs ML y assets geoespaciales locales."
    )
    parser.add_argument(
        "--root",
        action="append",
        default=[],
        help=(
            "Raiz adicional a escanear. Puede repetirse. "
            "Util para capas almacenadas fuera de ml-pipeline."
        ),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help=f"CSV de salida. Default: {DEFAULT_OUTPUT}",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    roots = [PROJECT_ROOT]
    roots.extend(Path(value) for value in args.root)

    print("\nEvaluation 07 | Inventario de assets locales")
    print(f"Proyecto: {PROJECT_ROOT}")

    rows = collect_inventory(roots)
    output = safe_resolve(args.output)
    write_csv(rows, output)
    print_summary(rows)

    print(f"\nInventario detallado: {output}")
    print("Nota: el CSV contiene rutas locales y no debe versionarse.")


if __name__ == "__main__":
    main()
