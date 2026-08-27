from __future__ import annotations

import argparse
import json
from pathlib import Path

try:
    import geopandas as gpd
except ImportError as exc:
    raise SystemExit(
        "Falta geopandas. Instálalo con: python -m pip install geopandas"
    ) from exc

try:
    from shapely import make_valid
except ImportError:
    make_valid = None


CAPAS = {
    "edafologia": "inegi_edafologia.geojson",
    "fisiografia": "inegi_provincias_fisiograficas.geojson",
    "hidrografia": "inegi_hidrografia.geojson",
    "uso_suelo_vegetacion": "inegi_uso_suelo_vegetacion.geojson",
}


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
        if (candidato / "ms02_procesamiento" / "04_integration" / "layers" / "inegi").exists():
            return candidato
    raise FileNotFoundError("No se encontró la raíz del repositorio")


def reparar_invalidas(gdf: gpd.GeoDataFrame) -> tuple[gpd.GeoDataFrame, int]:
    invalidas = ~gdf.geometry.is_valid
    cantidad = int(invalidas.sum())
    if not cantidad:
        return gdf, 0

    copia = gdf.copy()
    if make_valid is not None:
        copia.loc[invalidas, copia.geometry.name] = copia.loc[invalidas, copia.geometry.name].map(make_valid)
    else:
        copia.loc[invalidas, copia.geometry.name] = copia.loc[invalidas, copia.geometry.name].buffer(0)

    restantes = int((~copia.geometry.is_valid).sum())
    if restantes:
        raise RuntimeError(f"No fue posible reparar {restantes} geometrías inválidas en la copia de despliegue")
    return copia, cantidad


def normalizar_cve_ent(valor) -> str:
    return str(valor).zfill(2)


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Genera copias de despliegue de capas temáticas INEGI separadas por estado. "
            "No simplifica geometrías; solo hace intersección espacial con los límites estatales."
        )
    )
    parser.add_argument(
        "--capa",
        choices=[*CAPAS.keys(), "todas"],
        default="todas",
        help="Capa a procesar (default: todas).",
    )
    parser.add_argument(
        "--desde-estado",
        type=int,
        default=1,
        help="CVE_ENT inicial para reanudar una capa (default: 1).",
    )
    args = parser.parse_args()

    raiz = encontrar_raiz(Path.cwd())
    origen_dir = raiz / "ms02_procesamiento" / "04_integration" / "layers" / "inegi"
    salida_dir = raiz / "data_deploy" / "capas_web" / "inegi" / "tematicas"
    salida_dir.mkdir(parents=True, exist_ok=True)

    estados_path = origen_dir / "inegi_entidades.geojson"
    estados = gpd.read_file(estados_path)[["cve_ent", "nom_ent", "geometry"]].copy()
    estados["cve_ent"] = estados["cve_ent"].map(normalizar_cve_ent)

    capas_objetivo = CAPAS if args.capa == "todas" else {args.capa: CAPAS[args.capa]}
    reporte = {
        "criterios": {
            "simplificacion_geometrica": False,
            "fuentes_maestras_modificadas": False,
            "operacion": "interseccion espacial por entidad federativa",
            "nota": (
                "Las geometrías que cruzan límites estatales pueden quedar divididas en las copias de despliegue. "
                "No se eliminan vértices ni se reduce precisión."
            ),
        },
        "capas": [],
    }

    for capa_id, archivo in capas_objetivo.items():
        origen = origen_dir / archivo
        if not origen.is_file():
            raise FileNotFoundError(f"No existe: {origen}")

        print(f"\n=== {capa_id.upper()} ===")
        print(f"Leyendo {archivo} ({bytes_legibles(origen.stat().st_size)})...")
        gdf = gpd.read_file(origen)
        gdf, reparadas = reparar_invalidas(gdf)

        if gdf.crs != estados.crs:
            gdf = gdf.to_crs(estados.crs)

        capa_out = salida_dir / capa_id
        capa_out.mkdir(parents=True, exist_ok=True)

        capa_reporte = {
            "capa": capa_id,
            "archivo_origen": str(origen.relative_to(raiz)),
            "features_origen": int(len(gdf)),
            "invalidas_reparadas_en_copia": reparadas,
            "particiones": [],
        }

        indice = gdf.sindex

        for _, estado in estados.sort_values("cve_ent").iterrows():
            cve_ent = estado["cve_ent"]
            if int(cve_ent) < args.desde_estado:
                continue

            print(f"  Estado {cve_ent} - {estado['nom_ent']}...")
            geom_estado = estado.geometry

            candidatos_idx = list(indice.query(geom_estado, predicate="intersects"))
            if candidatos_idx:
                subset = gdf.iloc[candidatos_idx].copy()
                subset.geometry = subset.geometry.intersection(geom_estado)
                subset = subset[~subset.geometry.is_empty & subset.geometry.notna()].copy()
            else:
                subset = gdf.iloc[0:0].copy()

            subset.insert(0, "cve_ent_web", cve_ent)
            subset.insert(1, "nom_ent_web", estado["nom_ent"])

            destino = capa_out / f"{capa_id}_{cve_ent}.geojson"
            subset.to_file(destino, driver="GeoJSON")

            verificacion = gpd.read_file(destino)
            invalidas_salida = int((~verificacion.geometry.is_valid).sum()) if len(verificacion) else 0
            if invalidas_salida:
                raise RuntimeError(
                    f"{destino.name}: se detectaron {invalidas_salida} geometrías inválidas después de escribir"
                )

            bytes_salida = destino.stat().st_size
            print(f"    {len(verificacion):,} features | {bytes_legibles(bytes_salida)}")
            capa_reporte["particiones"].append(
                {
                    "cve_ent": cve_ent,
                    "nom_ent": estado["nom_ent"],
                    "features": int(len(verificacion)),
                    "bytes": bytes_salida,
                    "archivo": str(destino.relative_to(raiz)),
                }
            )

        capa_reporte["bytes_particiones"] = sum(x["bytes"] for x in capa_reporte["particiones"])
        reporte["capas"].append(capa_reporte)

        reporte_path = salida_dir / "reporte_particiones_tematicas.json"
        reporte_path.write_text(json.dumps(reporte, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"  Reporte actualizado: {reporte_path.relative_to(raiz)}")

    print("\n========================================")
    print("PARTICIONADO TEMÁTICO TERMINADO")
    print("No se simplificaron geometrías ni se modificaron las capas maestras.")
    print("Las copias de despliegue sí se cortaron espacialmente en los límites estatales.")


if __name__ == "__main__":
    main()
