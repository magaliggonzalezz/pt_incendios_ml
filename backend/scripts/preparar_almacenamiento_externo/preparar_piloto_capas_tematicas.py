from __future__ import annotations

import argparse
import json
from pathlib import Path

try:
    import geopandas as gpd
except ImportError as exc:
    raise SystemExit("Falta geopandas. Instálalo con: python -m pip install geopandas") from exc


PATRONES = {
    "edafologia": ["inegi_edafologia.geojson", "*edafolog*.geojson"],
    "fisiografia": ["inegi_fisiografia.geojson", "*fisiograf*.geojson"],
    "hidrografia": ["inegi_hidrografia.geojson", "*hidrograf*.geojson"],
    "uso_suelo_vegetacion": ["inegi_uso_suelo_vegetacion.geojson", "*uso*suelo*veget*.geojson"],
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


def resolver_archivo(carpeta: Path, patrones: list[str]) -> Path | None:
    for patron in patrones:
        if "*" not in patron:
            candidato = carpeta / patron
            if candidato.is_file():
                return candidato
        else:
            encontrados = sorted(carpeta.glob(patron))
            if encontrados:
                return encontrados[0]
    return None


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Genera un piloto estatal de las capas temáticas para medir entrega web. "
            "No simplifica geometrías y nunca modifica las capas maestras."
        )
    )
    parser.add_argument("--cve-ent", default="01", help="Clave de entidad de dos dígitos (default: 01)")
    parser.add_argument(
        "--permitir-reparacion",
        action="store_true",
        help=(
            "Permite reparar geometrías inválidas SOLO en la copia de despliegue mediante make_valid(). "
            "Las fuentes maestras permanecen intactas."
        ),
    )
    args = parser.parse_args()

    cve_ent = str(args.cve_ent).zfill(2)
    if len(cve_ent) != 2 or not cve_ent.isdigit():
        raise SystemExit("--cve-ent debe ser una clave numérica de dos dígitos")

    raiz = encontrar_raiz(Path.cwd())
    carpeta = raiz / "ms02_procesamiento" / "04_integration" / "layers" / "inegi"
    estados_path = carpeta / "inegi_entidades.geojson"
    if not estados_path.is_file():
        raise FileNotFoundError(f"Falta la capa de entidades: {estados_path}")

    estados = gpd.read_file(estados_path)
    if "cve_ent" not in estados.columns:
        raise RuntimeError("inegi_entidades.geojson no contiene cve_ent")

    estados["_cve_ent_norm"] = estados["cve_ent"].astype(str).str.zfill(2)
    estado = estados[estados["_cve_ent_norm"] == cve_ent]
    if estado.empty:
        raise RuntimeError(f"No se encontró la entidad {cve_ent}")

    mascara = estado.geometry.union_all()
    salida_base = raiz / "data_deploy" / "capas_web" / "inegi" / "tematicas" / cve_ent
    salida_base.mkdir(parents=True, exist_ok=True)

    reporte = {
        "cve_ent": cve_ent,
        "criterios": {
            "fuentes_maestras_modificadas": False,
            "simplificacion_geometrica": False,
            "operacion_web": "recorte espacial por límite estatal para generar una copia de despliegue",
            "reparacion_invalidas_habilitada": bool(args.permitir_reparacion),
        },
        "capas": [],
    }

    print(f"=== PILOTO CAPAS TEMÁTICAS | ENTIDAD {cve_ent} ===\n")
    print("Las capas maestras NO se modifican.")
    print("No se simplifican geometrías; el piloto solo recorta la copia web al límite estatal.\n")

    for capa, patrones in PATRONES.items():
        origen = resolver_archivo(carpeta, patrones)
        if origen is None:
            print(f"[FALTA] {capa}: no se encontró archivo compatible")
            reporte["capas"].append({"capa": capa, "estado": "no_encontrado"})
            continue

        print(f"Leyendo {capa}: {origen.name} ({bytes_legibles(origen.stat().st_size)})")
        gdf = gpd.read_file(origen)
        invalidas_antes = int((~gdf.geometry.is_valid).sum())

        if invalidas_antes and not args.permitir_reparacion:
            print(
                f"  OMITIDA: {invalidas_antes} geometrías inválidas. "
                "No se reparan automáticamente sin --permitir-reparacion.\n"
            )
            reporte["capas"].append(
                {
                    "capa": capa,
                    "archivo_origen": origen.name,
                    "estado": "omitida_geometrias_invalidas",
                    "features_origen": int(len(gdf)),
                    "geometrias_invalidas": invalidas_antes,
                    "bytes_origen": origen.stat().st_size,
                }
            )
            continue

        if invalidas_antes:
            gdf = gdf.copy()
            gdf.geometry = gdf.geometry.make_valid()

        # sindex permite descartar features fuera del bbox antes del clip exacto.
        candidatos_idx = list(gdf.sindex.query(mascara, predicate="intersects"))
        candidatos = gdf.iloc[candidatos_idx].copy()
        recortada = gpd.clip(candidatos, mascara, keep_geom_type=False)
        recortada = recortada[~recortada.geometry.is_empty & recortada.geometry.notna()].copy()

        destino = salida_base / f"inegi_{capa}_{cve_ent}.geojson"
        recortada.to_file(destino, driver="GeoJSON")

        verificacion = gpd.read_file(destino)
        invalidas_salida = int((~verificacion.geometry.is_valid).sum())
        if invalidas_salida:
            raise RuntimeError(f"{destino.name}: se generaron {invalidas_salida} geometrías inválidas")

        print(f"  Features origen: {len(gdf):,}")
        print(f"  Candidatas por intersección: {len(candidatos):,}")
        print(f"  Features salida: {len(verificacion):,}")
        print(f"  Tamaño salida: {bytes_legibles(destino.stat().st_size)}\n")

        reporte["capas"].append(
            {
                "capa": capa,
                "archivo_origen": origen.name,
                "estado": "generada",
                "features_origen": int(len(gdf)),
                "features_candidatas": int(len(candidatos)),
                "features_salida": int(len(verificacion)),
                "geometrias_invalidas_origen": invalidas_antes,
                "geometrias_invalidas_salida": invalidas_salida,
                "bytes_origen": origen.stat().st_size,
                "bytes_salida": destino.stat().st_size,
                "archivo_salida": str(destino.relative_to(raiz)),
            }
        )

    reporte_path = salida_base / "reporte_piloto.json"
    reporte_path.write_text(json.dumps(reporte, ensure_ascii=False, indent=2), encoding="utf-8")

    print("========================================")
    print(f"Reporte: {reporte_path.relative_to(raiz)}")
    print("Este piloto no se sube automáticamente a R2.")


if __name__ == "__main__":
    main()
