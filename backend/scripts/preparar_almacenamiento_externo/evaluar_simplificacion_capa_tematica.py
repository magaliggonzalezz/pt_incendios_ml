from __future__ import annotations

import argparse
import json
from pathlib import Path

try:
    import geopandas as gpd
except ImportError as exc:
    raise SystemExit("Falta geopandas. Instálalo con: python -m pip install geopandas") from exc


CAPAS = ["edafologia", "fisiografia", "hidrografia", "uso_suelo_vegetacion"]


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


def medida_total(gdf_metrico: gpd.GeoDataFrame) -> tuple[str, float]:
    tipos = set(gdf_metrico.geometry.geom_type.dropna())
    if tipos and all("Line" in tipo for tipo in tipos):
        return "longitud_m", float(gdf_metrico.geometry.length.sum())
    return "area_m2", float(gdf_metrico.geometry.area.sum())


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Genera pilotos simplificados de una partición temática para medir reducción y desviación. "
            "No reemplaza ni sube ninguna capa."
        )
    )
    parser.add_argument("--capa", choices=CAPAS, required=True)
    parser.add_argument("--cve-ent", required=True, help="CVE_ENT de dos dígitos")
    parser.add_argument(
        "--tolerancias",
        default="10,25,50",
        help="Tolerancias en metros separadas por coma (default: 10,25,50)",
    )
    args = parser.parse_args()

    cve_ent = str(args.cve_ent).zfill(2)
    if len(cve_ent) != 2 or not cve_ent.isdigit():
        raise ValueError("cve-ent debe ser numérico de dos dígitos")

    tolerancias = [float(x.strip()) for x in args.tolerancias.split(",") if x.strip()]
    if not tolerancias or any(x <= 0 for x in tolerancias):
        raise ValueError("Las tolerancias deben ser números positivos")

    raiz = encontrar_raiz(Path.cwd())
    origen = (
        raiz
        / "data_deploy"
        / "capas_web"
        / "inegi"
        / "tematicas"
        / args.capa
        / f"{args.capa}_{cve_ent}.geojson"
    )
    if not origen.is_file():
        raise FileNotFoundError(f"No existe la partición: {origen}")

    salida_dir = (
        raiz
        / "data_deploy"
        / "capas_web"
        / "pilotos_simplificacion"
        / args.capa
        / cve_ent
    )
    salida_dir.mkdir(parents=True, exist_ok=True)

    print(f"Leyendo {origen.name} ({bytes_legibles(origen.stat().st_size)})...")
    gdf = gpd.read_file(origen)
    if gdf.empty:
        raise RuntimeError("La partición está vacía")

    crs_metrico = gdf.estimate_utm_crs()
    if crs_metrico is None:
        raise RuntimeError("No se pudo estimar un CRS métrico para la partición")

    metrico = gdf.to_crs(crs_metrico)
    tipo_medida, medida_original = medida_total(metrico)

    reporte = {
        "capa": args.capa,
        "cve_ent": cve_ent,
        "origen": str(origen.relative_to(raiz)),
        "bytes_origen": origen.stat().st_size,
        "features_origen": int(len(gdf)),
        "crs_origen": str(gdf.crs),
        "crs_metrico_piloto": str(crs_metrico),
        "tipo_medida": tipo_medida,
        "medida_original": medida_original,
        "criterios": {
            "preserve_topology": True,
            "fuente_reemplazada": False,
            "subida_r2": False,
            "objetivo": "comparar tamaño y desviación antes de decidir si se adopta simplificación web",
        },
        "pilotos": [],
    }

    print(f"Features: {len(gdf):,}")
    print(f"CRS métrico usado: {crs_metrico}")
    print()

    for tolerancia in tolerancias:
        print(f"Tolerancia {tolerancia:g} m...")
        simplificado_m = metrico.copy()
        simplificado_m.geometry = simplificado_m.geometry.simplify(
            tolerance=tolerancia,
            preserve_topology=True,
        )
        simplificado_m = simplificado_m[
            simplificado_m.geometry.notna() & ~simplificado_m.geometry.is_empty
        ].copy()

        invalidas = int((~simplificado_m.geometry.is_valid).sum())
        tipo_medida_s, medida_simplificada = medida_total(simplificado_m)
        if tipo_medida_s != tipo_medida:
            raise RuntimeError("Cambió inesperadamente el tipo de medida geométrica")

        desviacion = (
            abs(medida_simplificada - medida_original) / medida_original * 100
            if medida_original
            else 0.0
        )

        simplificado = simplificado_m.to_crs(gdf.crs)
        destino = salida_dir / f"{args.capa}_{cve_ent}_simpl_{int(tolerancia)}m.geojson"
        simplificado.to_file(destino, driver="GeoJSON")

        bytes_salida = destino.stat().st_size
        reduccion = (1 - bytes_salida / origen.stat().st_size) * 100
        item = {
            "tolerancia_m": tolerancia,
            "archivo": str(destino.relative_to(raiz)),
            "bytes": bytes_salida,
            "reduccion_pct": reduccion,
            "features": int(len(simplificado)),
            "geometrias_invalidas": invalidas,
            "medida": medida_simplificada,
            "desviacion_medida_pct": desviacion,
        }
        reporte["pilotos"].append(item)

        print(
            f"  {bytes_legibles(bytes_salida)} | reducción {reduccion:.2f}% | "
            f"desviación {desviacion:.4f}% | inválidas {invalidas}"
        )

    reporte_path = salida_dir / "reporte_simplificacion.json"
    reporte_path.write_text(json.dumps(reporte, ensure_ascii=False, indent=2), encoding="utf-8")

    print("\n========================================")
    print(f"Reporte: {reporte_path.relative_to(raiz)}")
    print("No se reemplazó ni se subió ninguna capa a R2.")


if __name__ == "__main__":
    main()
