from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

try:
    import geopandas as gpd
except ImportError as exc:
    raise SystemExit(
        "Falta geopandas. Instálalo con: python -m pip install geopandas"
    ) from exc


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


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
        if (candidato / "ms02_procesamiento" / "04_integration" / "layers").exists():
            return candidato
    raise FileNotFoundError("No se encontró la raíz del repositorio")


def validar_geojson(path: Path, esperadas: int | None = None) -> gpd.GeoDataFrame:
    if not path.is_file():
        raise FileNotFoundError(f"No existe: {path}")

    gdf = gpd.read_file(path)
    if esperadas is not None and len(gdf) != esperadas:
        raise RuntimeError(
            f"{path.name}: se esperaban {esperadas:,} geometrías y se encontraron {len(gdf):,}"
        )
    if gdf.geometry.isna().any():
        raise RuntimeError(f"{path.name}: contiene geometrías nulas")
    if (~gdf.geometry.is_valid).any():
        raise RuntimeError(f"{path.name}: contiene geometrías inválidas")
    return gdf


def main() -> None:
    raiz = encontrar_raiz(Path.cwd())
    layers = raiz / "ms02_procesamiento" / "04_integration" / "layers"
    salida = raiz / "data_deploy" / "capas_web"
    salida.mkdir(parents=True, exist_ok=True)

    origen_entidades = layers / "inegi" / "inegi_entidades.geojson"
    origen_municipios = layers / "inegi" / "inegi_municipios.geojson"
    origen_smn = layers / "smn" / "smn_estaciones.geojson"

    print("Validando capas maestras propias...")
    entidades = validar_geojson(origen_entidades, 32)
    municipios = validar_geojson(origen_municipios, 2478)
    validar_geojson(origen_smn)

    if "cve_ent" not in municipios.columns:
        raise RuntimeError("inegi_municipios.geojson no contiene el campo cve_ent")

    # 1) Entidades: se copia byte a byte. No se simplifica ni reescribe geometría.
    destino_entidades = salida / "inegi" / "inegi_entidades.geojson"
    destino_entidades.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(origen_entidades, destino_entidades)

    # 2) Municipios: se generan archivos por entidad para entrega web granular.
    # No se simplifica ni recorta ninguna geometría; solo se separan features existentes.
    municipios_dir = salida / "inegi" / "municipios"
    municipios_dir.mkdir(parents=True, exist_ok=True)

    salidas_municipios = []
    suma_features = 0
    for cve_ent in sorted(municipios["cve_ent"].astype(str).str.zfill(2).unique()):
        subset = municipios[municipios["cve_ent"].astype(str).str.zfill(2) == cve_ent].copy()
        destino = municipios_dir / f"inegi_municipios_{cve_ent}.geojson"
        subset.to_file(destino, driver="GeoJSON")

        verificacion = gpd.read_file(destino)
        if len(verificacion) != len(subset):
            raise RuntimeError(f"Conteo inconsistente al generar {destino.name}")
        if (~verificacion.geometry.is_valid).any():
            raise RuntimeError(f"Se generaron geometrías inválidas en {destino.name}")

        suma_features += len(subset)
        salidas_municipios.append(
            {
                "cve_ent": cve_ent,
                "features": len(subset),
                "archivo": str(destino.relative_to(raiz)),
                "bytes": destino.stat().st_size,
                "sha256": sha256(destino),
            }
        )

    if suma_features != len(municipios):
        raise RuntimeError(
            f"La partición municipal perdió o duplicó features: origen={len(municipios)}, salida={suma_features}"
        )

    # 3) SMN: se copia byte a byte, sin transformación.
    destino_smn = salida / "smn" / "smn_estaciones.geojson"
    destino_smn.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(origen_smn, destino_smn)

    reporte = {
        "criterios": {
            "simplificacion_geometrica": False,
            "recorte_geometrico": False,
            "cambio_semantico": False,
            "entidades": "copia byte a byte de la capa procesada",
            "municipios": "mismas features y geometrías; únicamente separadas por cve_ent para entrega web",
            "smn": "copia byte a byte de la capa procesada",
        },
        "entidades": {
            "features": len(entidades),
            "origen": str(origen_entidades.relative_to(raiz)),
            "destino": str(destino_entidades.relative_to(raiz)),
            "bytes_origen": origen_entidades.stat().st_size,
            "bytes_destino": destino_entidades.stat().st_size,
            "sha256_origen": sha256(origen_entidades),
            "sha256_destino": sha256(destino_entidades),
        },
        "municipios": {
            "features_origen": len(municipios),
            "features_salida": suma_features,
            "particiones": len(salidas_municipios),
            "archivos": salidas_municipios,
        },
        "smn": {
            "origen": str(origen_smn.relative_to(raiz)),
            "destino": str(destino_smn.relative_to(raiz)),
            "bytes_origen": origen_smn.stat().st_size,
            "bytes_destino": destino_smn.stat().st_size,
            "sha256_origen": sha256(origen_smn),
            "sha256_destino": sha256(destino_smn),
        },
    }

    reporte_path = salida / "reporte_capas_web_base.json"
    reporte_path.write_text(json.dumps(reporte, ensure_ascii=False, indent=2), encoding="utf-8")

    print("\n=== CAPAS WEB BASE PREPARADAS ===")
    print(f"Entidades:  {len(entidades):,} features | {bytes_legibles(destino_entidades.stat().st_size)}")
    print(f"Municipios: {suma_features:,} features | {len(salidas_municipios)} archivos por estado")
    print(f"SMN:        {bytes_legibles(destino_smn.stat().st_size)}")
    print(f"Reporte:    {reporte_path.relative_to(raiz)}")
    print("No se simplificó ni recortó ninguna geometría.")


if __name__ == "__main__":
    main()
