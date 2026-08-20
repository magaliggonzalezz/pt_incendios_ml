from pathlib import Path
import argparse
import json


def formatear_bytes(num_bytes):
    unidades = ["B", "KiB", "MiB", "GiB", "TiB"]
    valor = float(num_bytes)

    for unidad in unidades:
        if valor < 1024 or unidad == unidades[-1]:
            return f"{valor:.2f} {unidad}"
        valor /= 1024


def analizar_directorio(ruta):
    ruta = Path(ruta)

    if not ruta.exists():
        raise FileNotFoundError(f"No existe la ruta: {ruta}")

    archivos = []
    total_bytes = 0
    por_extension = {}

    for archivo in ruta.rglob("*"):
        if not archivo.is_file():
            continue

        try:
            size = archivo.stat().st_size
        except OSError:
            continue

        total_bytes += size
        extension = archivo.suffix.lower() or "[sin_extension]"

        if extension not in por_extension:
            por_extension[extension] = {
                "archivos": 0,
                "bytes": 0,
            }

        por_extension[extension]["archivos"] += 1
        por_extension[extension]["bytes"] += size

        archivos.append({
            "archivo": str(archivo.relative_to(ruta)),
            "extension": extension,
            "bytes": size,
            "tamano": formatear_bytes(size),
        })

    archivos.sort(key=lambda x: x["bytes"], reverse=True)

    resumen_extensiones = []
    for extension, datos in por_extension.items():
        resumen_extensiones.append({
            "extension": extension,
            "archivos": datos["archivos"],
            "bytes": datos["bytes"],
            "tamano": formatear_bytes(datos["bytes"]),
        })

    resumen_extensiones.sort(key=lambda x: x["bytes"], reverse=True)

    return {
        "ruta": str(ruta.resolve()),
        "total_archivos": len(archivos),
        "total_bytes": total_bytes,
        "total_tamano": formatear_bytes(total_bytes),
        "por_extension": resumen_extensiones,
        "archivos": archivos,
    }


def main():
    parser = argparse.ArgumentParser(
        description="Audita tamaños de archivos candidatos a almacenamiento externo."
    )

    parser.add_argument(
        "rutas",
        nargs="+",
        help="Directorios que se desean analizar",
    )

    parser.add_argument(
        "--salida",
        default="reporte_almacenamiento_externo.json",
        help="Archivo JSON de salida",
    )

    args = parser.parse_args()

    reportes = []
    total_global = 0
    archivos_global = 0

    for ruta in args.rutas:
        print(f"\nAnalizando: {ruta}")

        reporte = analizar_directorio(ruta)
        reportes.append(reporte)

        total_global += reporte["total_bytes"]
        archivos_global += reporte["total_archivos"]

        print(f"  Archivos: {reporte['total_archivos']:,}")
        print(f"  Tamaño:   {reporte['total_tamano']}")

        print("\n  Por extensión:")
        for item in reporte["por_extension"]:
            print(
                f"    {item['extension']:15} "
                f"{item['archivos']:>6,} archivos   "
                f"{item['tamano']:>12}"
            )

        print("\n  15 archivos más grandes:")
        for archivo in reporte["archivos"][:15]:
            print(
                f"    {archivo['tamano']:>12}  "
                f"{archivo['archivo']}"
            )

    salida = {
        "total_directorios": len(reportes),
        "total_archivos": archivos_global,
        "total_bytes": total_global,
        "total_tamano": formatear_bytes(total_global),
        "directorios": reportes,
    }

    with open(args.salida, "w", encoding="utf-8") as f:
        json.dump(salida, f, ensure_ascii=False, indent=2)

    print("\n===================================")
    print("TOTAL GLOBAL")
    print("===================================")
    print(f"Archivos: {archivos_global:,}")
    print(f"Tamaño:   {formatear_bytes(total_global)}")
    print(f"Reporte:  {args.salida}")


if __name__ == "__main__":
    main()
