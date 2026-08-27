from __future__ import annotations

import json
from pathlib import Path

try:
    import geopandas as gpd
except ImportError as exc:
    raise SystemExit(
        "Falta geopandas. Instálalo con: python -m pip install geopandas"
    ) from exc


CAPAS = [
    "inegi_edafologia.geojson",
    "inegi_fisiografia.geojson",
    "inegi_hidrografia.geojson",
    "inegi_uso_suelo_vegetacion.geojson",
]


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


def main() -> None:
    raiz = encontrar_raiz(Path.cwd())
    carpeta = raiz / "ms02_procesamiento" / "04_integration" / "layers" / "inegi"
    salida = raiz / "data_deploy" / "capas_web" / "reporte_capas_tematicas.json"
    salida.parent.mkdir(parents=True, exist_ok=True)

    reporte = {
        "criterios": {
            "solo_auditoria": True,
            "archivos_modificados": False,
            "geometrias_simplificadas": False,
            "objetivo": "medir estructura y tamaño antes de definir la estrategia de entrega web",
        },
        "capas": [],
    }

    print("=== AUDITORÍA CAPAS TEMÁTICAS INEGI ===\n")

    for nombre in CAPAS:
        path = carpeta / nombre
        if not path.is_file():
            print(f"[FALTA] {nombre}")
            reporte["capas"].append({"archivo": nombre, "estado": "no_encontrado"})
            continue

        size = path.stat().st_size
        print(f"Leyendo {nombre} ({bytes_legibles(size)})...")
        gdf = gpd.read_file(path)

        columnas = [c for c in gdf.columns if c != gdf.geometry.name]
        geom_types = sorted(str(x) for x in gdf.geometry.geom_type.dropna().unique())
        invalidas = int((~gdf.geometry.is_valid).sum())
        nulas = int(gdf.geometry.isna().sum())

        posibles_claves_estado = [
            c for c in columnas
            if c.lower() in {"cve_ent", "cveent", "entidad", "estado", "nom_ent"}
        ]

        item = {
            "archivo": nombre,
            "estado": "ok",
            "bytes": size,
            "features": int(len(gdf)),
            "crs": str(gdf.crs),
            "tipos_geometria": geom_types,
            "geometrias_invalidas": invalidas,
            "geometrias_nulas": nulas,
            "columnas": columnas,
            "posibles_claves_estado": posibles_claves_estado,
            "bbox": [float(x) for x in gdf.total_bounds],
        }
        reporte["capas"].append(item)

        print(f"  Features: {len(gdf):,}")
        print(f"  CRS: {gdf.crs}")
        print(f"  Geometría: {', '.join(geom_types)}")
        print(f"  Inválidas: {invalidas:,} | Nulas: {nulas:,}")
        print(f"  Columnas: {', '.join(columnas) if columnas else '(sin atributos)'}")
        print(
            "  Clave estatal disponible: "
            + (", ".join(posibles_claves_estado) if posibles_claves_estado else "NO")
        )
        print()

    salida.write_text(json.dumps(reporte, ensure_ascii=False, indent=2), encoding="utf-8")

    print("========================================")
    print(f"Reporte: {salida.relative_to(raiz)}")
    print("No se modificó ni generó ninguna capa.")


if __name__ == "__main__":
    main()
