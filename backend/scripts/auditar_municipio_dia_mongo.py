from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

import pyarrow.parquet as pq


CAMPOS_AUDITAR = [
    "has_conafor",
    "has_firms",
    "has_smn",
    "has_inegi_contexto",
    "has_infys_contexto",
]


def encontrar_raiz(inicio: Path) -> Path:
    for candidato in [inicio.resolve(), *inicio.resolve().parents]:
        carpeta = candidato / "data_deploy" / "resultados" / "municipio_dia"
        if carpeta.is_dir():
            return candidato
    raise FileNotFoundError("No se encontro data_deploy/resultados/municipio_dia")


def normalizar_codigo(valor, ancho: int) -> str | None:
    if valor is None:
        return None
    texto = str(valor).strip()
    if texto.endswith(".0") and texto[:-2].isdigit():
        texto = texto[:-2]
    if not texto.isdigit() or len(texto) > ancho:
        return None
    return texto.zfill(ancho)


def es_positivo(valor) -> bool:
    if valor is None:
        return False
    try:
        return float(valor) > 0
    except (TypeError, ValueError):
        return False


def es_presente(valor) -> bool:
    return valor is not None


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Audita redundancias del dataset municipio-dia antes de definir el esquema "
            "final para MongoDB. No modifica ningun archivo."
        )
    )
    parser.add_argument("--base-dir", default=".", help="Raiz del repositorio")
    parser.add_argument(
        "--batch-size",
        type=int,
        default=100_000,
        help="Filas por lote de lectura (default: 100000)",
    )
    args = parser.parse_args()

    base = Path(args.base_dir).resolve()
    try:
        raiz = encontrar_raiz(base)
    except FileNotFoundError:
        raiz = encontrar_raiz(Path.cwd())

    carpeta = raiz / "data_deploy" / "resultados" / "municipio_dia"
    archivos = sorted(carpeta.glob("app_municipio_dia_resultados_*.parquet"))
    if not archivos:
        raise FileNotFoundError(f"No se encontraron Parquet en {carpeta}")

    total = 0
    codigo_inconsistente = 0
    valores = {campo: Counter() for campo in CAMPOS_AUDITAR}
    nulos = Counter()

    relaciones = {
        "has_firms_equiv_detecciones_firms_gt_0": 0,
        "has_conafor_equiv_event_count_gt_0": 0,
        "has_conafor_equiv_confirmed_fire_gt_0": 0,
        "has_smn_equiv_estaciones_obs_gt_0": 0,
        "has_smn_equiv_estaciones_obs_no_nulo": 0,
    }
    discrepancias = Counter()

    columnas = [
        "cve_ent",
        "cve_mun",
        "cvegeo",
        "has_conafor",
        "has_firms",
        "has_smn",
        "has_inegi_contexto",
        "has_infys_contexto",
        "conafor_event_count",
        "conafor_confirmed_fire",
        "detecciones_firms",
        "smn_estaciones_obs",
    ]

    print(f"Archivos encontrados: {len(archivos)}")
    print("Auditoria de redundancias municipio-dia\n")

    por_anio = []

    for path in archivos:
        parquet = pq.ParquetFile(path)
        disponibles = set(parquet.schema_arrow.names)
        faltantes = [campo for campo in columnas if campo not in disponibles]
        if faltantes:
            raise ValueError(f"{path.name}: faltan columnas requeridas: {faltantes}")

        filas_anio = 0
        inconsistencias_anio = 0

        for batch in parquet.iter_batches(batch_size=args.batch_size, columns=columnas):
            data = batch.to_pydict()
            for i in range(batch.num_rows):
                total += 1
                filas_anio += 1

                cve_ent = normalizar_codigo(data["cve_ent"][i], 2)
                cve_mun = normalizar_codigo(data["cve_mun"][i], 3)
                cvegeo = normalizar_codigo(data["cvegeo"][i], 5)
                if cve_ent is None or cve_mun is None or cvegeo != f"{cve_ent}{cve_mun}":
                    codigo_inconsistente += 1
                    inconsistencias_anio += 1

                for campo in CAMPOS_AUDITAR:
                    valor = data[campo][i]
                    if valor is None:
                        nulos[campo] += 1
                    valores[campo][str(valor)] += 1

                has_firms = bool(data["has_firms"][i])
                firms_derivado = es_positivo(data["detecciones_firms"][i])
                if has_firms == firms_derivado:
                    relaciones["has_firms_equiv_detecciones_firms_gt_0"] += 1
                else:
                    discrepancias["has_firms_vs_detecciones_firms"] += 1

                has_conafor = bool(data["has_conafor"][i])
                conafor_eventos = es_positivo(data["conafor_event_count"][i])
                if has_conafor == conafor_eventos:
                    relaciones["has_conafor_equiv_event_count_gt_0"] += 1
                else:
                    discrepancias["has_conafor_vs_event_count"] += 1

                conafor_confirmado = es_positivo(data["conafor_confirmed_fire"][i])
                if has_conafor == conafor_confirmado:
                    relaciones["has_conafor_equiv_confirmed_fire_gt_0"] += 1
                else:
                    discrepancias["has_conafor_vs_confirmed_fire"] += 1

                has_smn = bool(data["has_smn"][i])
                smn_positivo = es_positivo(data["smn_estaciones_obs"][i])
                if has_smn == smn_positivo:
                    relaciones["has_smn_equiv_estaciones_obs_gt_0"] += 1
                else:
                    discrepancias["has_smn_vs_estaciones_obs_gt_0"] += 1

                smn_presente = es_presente(data["smn_estaciones_obs"][i])
                if has_smn == smn_presente:
                    relaciones["has_smn_equiv_estaciones_obs_no_nulo"] += 1
                else:
                    discrepancias["has_smn_vs_estaciones_obs_no_nulo"] += 1

        anio = path.stem.rsplit("_", 1)[-1]
        por_anio.append(
            {
                "anio": anio,
                "filas": filas_anio,
                "cvegeo_inconsistentes": inconsistencias_anio,
            }
        )
        print(
            f"{anio}: {filas_anio:,} filas | "
            f"cvegeo inconsistentes={inconsistencias_anio:,}"
        )

    constantes = {}
    for campo in CAMPOS_AUDITAR:
        no_nulos = {clave: cuenta for clave, cuenta in valores[campo].items() if clave != "None"}
        constantes[campo] = {
            "es_constante_no_nulo": len(no_nulos) == 1 and nulos[campo] == 0,
            "valores": dict(valores[campo]),
            "nulos": nulos[campo],
        }

    relaciones_reporte = {}
    for nombre, coincidencias in relaciones.items():
        relaciones_reporte[nombre] = {
            "coincidencias": coincidencias,
            "total": total,
            "equivalencia_exacta": coincidencias == total,
            "porcentaje": round(100 * coincidencias / total, 6) if total else 0,
        }

    reporte = {
        "archivos": len(archivos),
        "filas": total,
        "cvegeo_derivable_de_cve_ent_cve_mun": codigo_inconsistente == 0,
        "cvegeo_inconsistentes": codigo_inconsistente,
        "campos_has": constantes,
        "relaciones": relaciones_reporte,
        "discrepancias": dict(discrepancias),
        "por_anio": por_anio,
    }

    reporte_path = raiz / "data_v2_mongo_ready" / "auditoria_municipio_dia_mongo.json"
    reporte_path.parent.mkdir(parents=True, exist_ok=True)
    reporte_path.write_text(
        json.dumps(reporte, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print("\n=== RESULTADO ===")
    print(f"Filas auditadas: {total:,}")
    print(
        "cve_ent/cve_mun redundantes respecto a cvegeo: "
        f"{'SI' if codigo_inconsistente == 0 else 'NO'}"
    )

    for campo in CAMPOS_AUDITAR:
        info = constantes[campo]
        print(
            f"{campo}: valores={info['valores']} | "
            f"constante={'SI' if info['es_constante_no_nulo'] else 'NO'}"
        )

    print("\nEquivalencias exactas:")
    for nombre, info in relaciones_reporte.items():
        print(
            f"- {nombre}: {'SI' if info['equivalencia_exacta'] else 'NO'} "
            f"({info['porcentaje']:.6f}%)"
        )

    print(f"\nReporte: {reporte_path}")
    print("No se modifico ningun dataset.")


if __name__ == "__main__":
    main()
