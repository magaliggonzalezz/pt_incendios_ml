from pathlib import Path
import argparse
import csv
import json
import re
from collections import defaultdict


RUTAS_DEFAULT = [
    Path("ms04_evaluation/app_ready/csv/exportacion"),
    Path("ms04_evaluation/app_ready/csv/municipio_dia"),
    Path("ms02_procesamiento/04_integration/layers"),
]

VALORES_NULOS = {"", "null", "none", "nan", "na", "n/a", "<na>"}
ANIO_RE = re.compile(r"(?:^|[_-])((?:19|20)\d{2})(?:[_-]|\.|$)")


def formatear_bytes(num_bytes):
    unidades = ["B", "KiB", "MiB", "GiB", "TiB"]
    valor = float(num_bytes)
    for unidad in unidades:
        if valor < 1024 or unidad == unidades[-1]:
            return f"{valor:.2f} {unidad}"
        valor /= 1024


def es_nulo(valor):
    if valor is None:
        return True
    return str(valor).strip().lower() in VALORES_NULOS


def detectar_anio(nombre):
    match = ANIO_RE.search(nombre)
    return int(match.group(1)) if match else None


def normalizar_familia(nombre):
    base = Path(nombre).stem
    base = re.sub(r"(?:^|[_-])(?:19|20)\d{2}(?=$|[_-])", "", base)
    base = re.sub(r"[_-]+", "_", base).strip("_")
    return base


def actualizar_perfil(perfil, valor, max_unicos):
    perfil["muestra"] += 1

    if es_nulo(valor):
        perfil["nulos"] += 1
        return

    texto = str(valor).strip()
    perfil["no_nulos"] += 1

    if len(perfil["ejemplos"]) < 5 and texto not in perfil["ejemplos"]:
        perfil["ejemplos"].append(texto[:160])

    if not perfil["unicos_truncados"]:
        perfil["unicos"].add(texto)
        if len(perfil["unicos"]) > max_unicos:
            perfil["unicos_truncados"] = True
            perfil["unicos"].clear()

    try:
        numero = float(texto.replace(",", "."))
        perfil["numericos"] += 1
        if perfil["min"] is None or numero < perfil["min"]:
            perfil["min"] = numero
        if perfil["max"] is None or numero > perfil["max"]:
            perfil["max"] = numero
    except ValueError:
        pass


def finalizar_perfiles(perfiles):
    salida = []
    for nombre, p in perfiles.items():
        muestra = p["muestra"] or 1
        no_nulos = p["no_nulos"]
        numericos = p["numericos"]

        if p["unicos_truncados"]:
            unicos = f">{p['max_unicos']}"
            constante = False
        else:
            unicos = len(p["unicos"])
            constante = no_nulos > 0 and unicos == 1

        salida.append({
            "campo": nombre,
            "muestra": p["muestra"],
            "nulos": p["nulos"],
            "porcentaje_nulos": round((p["nulos"] / muestra) * 100, 4),
            "unicos_muestra": unicos,
            "constante_en_muestra": constante,
            "porcentaje_numerico_no_nulo": round((numericos / no_nulos) * 100, 4) if no_nulos else 0.0,
            "min_numerico": p["min"],
            "max_numerico": p["max"],
            "ejemplos": p["ejemplos"],
        })

    salida.sort(key=lambda x: x["campo"])
    return salida


def nuevo_perfil(max_unicos):
    return {
        "muestra": 0,
        "nulos": 0,
        "no_nulos": 0,
        "numericos": 0,
        "min": None,
        "max": None,
        "unicos": set(),
        "unicos_truncados": False,
        "max_unicos": max_unicos,
        "ejemplos": [],
    }


def auditar_csv(ruta, max_filas, max_unicos):
    perfiles = defaultdict(lambda: nuevo_perfil(max_unicos))
    filas = 0

    with ruta.open("r", encoding="utf-8-sig", newline="", errors="replace") as f:
        lector = csv.DictReader(f)
        columnas = lector.fieldnames or []

        for fila in lector:
            filas += 1
            for columna in columnas:
                actualizar_perfil(perfiles[columna], fila.get(columna), max_unicos)

            if max_filas and filas >= max_filas:
                break

    return {
        "columnas": columnas,
        "numero_columnas": len(columnas),
        "filas_muestreadas": filas,
        "muestreo_limitado": bool(max_filas and filas >= max_filas),
        "perfiles_campos": finalizar_perfiles(perfiles),
    }


def auditar_geojson(ruta, max_features, max_unicos):
    try:
        import ijson
    except ImportError:
        return {
            "estado": "requiere_ijson",
            "mensaje": "Instala ijson para auditar propiedades GeoJSON grandes: python -m pip install ijson",
            "features_muestreadas": 0,
            "columnas": [],
            "numero_columnas": 0,
            "perfiles_campos": [],
        }

    perfiles = defaultdict(lambda: nuevo_perfil(max_unicos))
    columnas = set()
    features = 0
    tipos_geometria = defaultdict(int)

    with ruta.open("rb") as f:
        for feature in ijson.items(f, "features.item"):
            features += 1
            props = feature.get("properties") or {}
            geometry = feature.get("geometry") or {}

            tipo_geom = geometry.get("type")
            if tipo_geom:
                tipos_geometria[tipo_geom] += 1

            for campo, valor in props.items():
                columnas.add(campo)
                actualizar_perfil(perfiles[campo], valor, max_unicos)

            if max_features and features >= max_features:
                break

    columnas = sorted(columnas)
    return {
        "estado": "ok",
        "features_muestreadas": features,
        "muestreo_limitado": bool(max_features and features >= max_features),
        "columnas": columnas,
        "numero_columnas": len(columnas),
        "tipos_geometria_muestra": dict(sorted(tipos_geometria.items())),
        "perfiles_campos": finalizar_perfiles(perfiles),
    }


def clasificar_fuente(ruta, raiz):
    try:
        relativa = ruta.relative_to(raiz)
    except ValueError:
        return None
    return relativa.parts[0] if len(relativa.parts) > 1 else None


def auditar_archivo(ruta, raiz, max_filas, max_features, max_unicos):
    extension = ruta.suffix.lower()
    resultado = {
        "archivo": str(ruta),
        "relativo": str(ruta.relative_to(raiz)),
        "nombre": ruta.name,
        "extension": extension,
        "bytes": ruta.stat().st_size,
        "tamano": formatear_bytes(ruta.stat().st_size),
        "anio_nombre": detectar_anio(ruta.name),
        "familia": normalizar_familia(ruta.name),
        "fuente": clasificar_fuente(ruta, raiz),
    }

    if extension == ".csv":
        resultado["auditoria"] = auditar_csv(ruta, max_filas, max_unicos)
    elif extension in {".geojson", ".json"}:
        resultado["auditoria"] = auditar_geojson(ruta, max_features, max_unicos)
    else:
        resultado["auditoria"] = {"estado": "extension_no_auditada"}

    return resultado


def construir_resumen_familias(archivos):
    grupos = defaultdict(list)

    for archivo in archivos:
        clave = (
            archivo.get("raiz"),
            archivo.get("fuente"),
            archivo.get("familia"),
            archivo.get("extension"),
        )
        grupos[clave].append(archivo)

    salida = []
    for (raiz, fuente, familia, extension), items in grupos.items():
        anuales = [x for x in items if x.get("anio_nombre")]
        completos = [x for x in items if not x.get("anio_nombre")]

        if len(items) < 2:
            continue

        salida.append({
            "raiz": raiz,
            "fuente": fuente,
            "familia": familia,
            "extension": extension,
            "archivos": len(items),
            "archivos_anuales": len(anuales),
            "archivos_sin_anio": len(completos),
            "bytes_total": sum(x["bytes"] for x in items),
            "tamano_total": formatear_bytes(sum(x["bytes"] for x in items)),
            "bytes_anuales": sum(x["bytes"] for x in anuales),
            "tamano_anuales": formatear_bytes(sum(x["bytes"] for x in anuales)),
            "bytes_sin_anio": sum(x["bytes"] for x in completos),
            "tamano_sin_anio": formatear_bytes(sum(x["bytes"] for x in completos)),
            "posible_redundancia_completo_mas_anuales": bool(anuales and completos),
            "nombres": [x["nombre"] for x in sorted(items, key=lambda y: y["nombre"])],
        })

    salida.sort(key=lambda x: x["bytes_total"], reverse=True)
    return salida


def firma_columnas(archivo):
    auditoria = archivo.get("auditoria", {})
    columnas = auditoria.get("columnas") or []
    return tuple(sorted(columnas))


def construir_resumen_esquemas(archivos):
    grupos = defaultdict(list)

    for archivo in archivos:
        firma = firma_columnas(archivo)
        if not firma:
            continue
        grupos[firma].append(archivo)

    salida = []
    for firma, items in grupos.items():
        salida.append({
            "numero_columnas": len(firma),
            "columnas": list(firma),
            "archivos": len(items),
            "bytes_total": sum(x["bytes"] for x in items),
            "tamano_total": formatear_bytes(sum(x["bytes"] for x in items)),
            "ejemplos": [x["relativo"] for x in items[:8]],
        })

    salida.sort(key=lambda x: (x["archivos"], x["bytes_total"]), reverse=True)
    return salida


def escribir_csv_resumen(archivos, ruta_salida):
    campos = [
        "raiz", "fuente", "relativo", "extension", "tamano", "bytes",
        "anio_nombre", "familia", "numero_columnas", "registros_muestreados",
        "estado_auditoria",
    ]

    with ruta_salida.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=campos)
        writer.writeheader()

        for archivo in archivos:
            auditoria = archivo.get("auditoria", {})
            registros = auditoria.get("filas_muestreadas", auditoria.get("features_muestreadas"))
            writer.writerow({
                "raiz": archivo.get("raiz"),
                "fuente": archivo.get("fuente"),
                "relativo": archivo.get("relativo"),
                "extension": archivo.get("extension"),
                "tamano": archivo.get("tamano"),
                "bytes": archivo.get("bytes"),
                "anio_nombre": archivo.get("anio_nombre"),
                "familia": archivo.get("familia"),
                "numero_columnas": auditoria.get("numero_columnas"),
                "registros_muestreados": registros,
                "estado_auditoria": auditoria.get("estado", "ok"),
            })


def main():
    parser = argparse.ArgumentParser(
        description="Audita estructura, campos y posibles redundancias de datasets candidatos a almacenamiento externo."
    )
    parser.add_argument(
        "--base-dir",
        default=".",
        help="Raíz del proyecto. Por defecto usa el directorio actual.",
    )
    parser.add_argument(
        "--rutas",
        nargs="*",
        help="Rutas relativas opcionales. Si se omiten, usa las tres rutas del proyecto ya definidas.",
    )
    parser.add_argument(
        "--max-filas-csv",
        type=int,
        default=200000,
        help="Máximo de filas a muestrear por CSV. Usa 0 para recorrer el archivo completo.",
    )
    parser.add_argument(
        "--max-features-geojson",
        type=int,
        default=50000,
        help="Máximo de features a muestrear por GeoJSON. Usa 0 para recorrer el archivo completo.",
    )
    parser.add_argument(
        "--max-unicos",
        type=int,
        default=5000,
        help="Máximo de valores únicos conservados por campo antes de truncar el conteo.",
    )
    parser.add_argument(
        "--salida-json",
        default="reporte_auditoria_datasets_externos.json",
    )
    parser.add_argument(
        "--salida-csv",
        default="reporte_auditoria_datasets_externos_resumen.csv",
    )

    args = parser.parse_args()
    base_dir = Path(args.base_dir).resolve()
    rutas = [Path(x) for x in args.rutas] if args.rutas else RUTAS_DEFAULT

    archivos = []
    rutas_no_encontradas = []

    print("Auditoría de datasets externos")
    print(f"Base: {base_dir}")
    print(f"CSV: hasta {args.max_filas_csv:,} filas por archivo" if args.max_filas_csv else "CSV: recorrido completo")
    print(f"GeoJSON: hasta {args.max_features_geojson:,} features por archivo" if args.max_features_geojson else "GeoJSON: recorrido completo")

    for ruta_rel in rutas:
        raiz = (base_dir / ruta_rel).resolve()
        if not raiz.exists():
            rutas_no_encontradas.append(str(raiz))
            print(f"\n[NO EXISTE] {raiz}")
            continue

        candidatos = sorted(
            p for p in raiz.rglob("*")
            if p.is_file() and p.suffix.lower() in {".csv", ".geojson", ".json"}
        )

        print(f"\n{ruta_rel}: {len(candidatos)} archivos")

        for i, archivo in enumerate(candidatos, start=1):
            print(f"  [{i}/{len(candidatos)}] {archivo.relative_to(raiz)} ({formatear_bytes(archivo.stat().st_size)})")
            try:
                resultado = auditar_archivo(
                    archivo,
                    raiz,
                    args.max_filas_csv,
                    args.max_features_geojson,
                    args.max_unicos,
                )
            except Exception as exc:
                resultado = {
                    "archivo": str(archivo),
                    "relativo": str(archivo.relative_to(raiz)),
                    "nombre": archivo.name,
                    "extension": archivo.suffix.lower(),
                    "bytes": archivo.stat().st_size,
                    "tamano": formatear_bytes(archivo.stat().st_size),
                    "anio_nombre": detectar_anio(archivo.name),
                    "familia": normalizar_familia(archivo.name),
                    "fuente": clasificar_fuente(archivo, raiz),
                    "auditoria": {
                        "estado": "error",
                        "error": repr(exc),
                    },
                }

            resultado["raiz"] = str(ruta_rel)
            archivos.append(resultado)

    total_bytes = sum(x["bytes"] for x in archivos)

    reporte = {
        "configuracion": {
            "base_dir": str(base_dir),
            "rutas": [str(x) for x in rutas],
            "max_filas_csv": args.max_filas_csv,
            "max_features_geojson": args.max_features_geojson,
            "max_unicos": args.max_unicos,
        },
        "rutas_no_encontradas": rutas_no_encontradas,
        "resumen": {
            "archivos": len(archivos),
            "bytes": total_bytes,
            "tamano": formatear_bytes(total_bytes),
        },
        "familias": construir_resumen_familias(archivos),
        "esquemas_repetidos": construir_resumen_esquemas(archivos),
        "archivos": archivos,
    }

    salida_json = Path(args.salida_json)
    salida_csv = Path(args.salida_csv)

    with salida_json.open("w", encoding="utf-8") as f:
        json.dump(reporte, f, ensure_ascii=False, indent=2)

    escribir_csv_resumen(archivos, salida_csv)

    print("\n===================================")
    print("AUDITORÍA TERMINADA")
    print("===================================")
    print(f"Archivos auditados: {len(archivos):,}")
    print(f"Volumen referenciado: {formatear_bytes(total_bytes)}")
    print(f"JSON: {salida_json}")
    print(f"CSV:  {salida_csv}")

    geojson_sin_ijson = [
        x for x in archivos
        if x["extension"] in {".geojson", ".json"}
        and x.get("auditoria", {}).get("estado") == "requiere_ijson"
    ]
    if geojson_sin_ijson:
        print("\nATENCIÓN: no se inspeccionaron propiedades GeoJSON porque falta ijson.")
        print("Instálalo y vuelve a ejecutar:")
        print("  python -m pip install ijson")


if __name__ == "__main__":
    main()
