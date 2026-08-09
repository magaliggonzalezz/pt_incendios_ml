#!/usr/bin/env python3
"""Genera una versión mongo-ready compacta de los resultados v2.

Parte de los JSONL creados por transformar_resultados.py. Conserva únicamente campos
necesarios para consultas interactivas y usa nombres de campo más cortos pero legibles
para reducir el costo por documento. No se conecta a MongoDB.
"""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path
from typing import Any

DATASETS = [
    "resultados_estado_anio",
    "resultados_estado_mes",
    "resultados_estado_dia",
    "resultados_municipio_anio",
    "resultados_municipio_mes",
]

# Campos métricos retenidos y su nombre de almacenamiento.
METRIC_MAP = {
    "dias_observados": "observaciones",
    "municipio_dias_observados": "observaciones",
    "municipios_observados": "municipios",
    "dias_con_incendio_activo": "dias_incendio",
    "dias_con_patron_extremo": "dias_extremo",
    "dias_con_conafor": "dias_conafor",
    "dias_con_firms": "dias_firms",
    "dias_con_smn": "dias_smn",
    "conafor_event_count_total": "conafor_eventos",
    "conafor_total_hectareas_total": "conafor_ha",
    "firms_detection_count_total": "firms_detecciones",
    "firms_frp_total": "firms_frp",
    "precipitacion_mm_promedio": "precip_mm",
    "temperatura_minima_c_promedio": "temp_min_c",
    "temperatura_maxima_c_promedio": "temp_max_c",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Genera JSONL mongo-ready a partir de data_v2_generada."
    )
    parser.add_argument(
        "--input-dir",
        type=Path,
        default=Path("data_v2_generada"),
        help="Carpeta con JSONL v2 (default: ./data_v2_generada).",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("data_v2_mongo_ready"),
        help="Carpeta de salida (default: ./data_v2_mongo_ready).",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Permite reemplazar la carpeta de salida si ya existe.",
    )
    return parser.parse_args()


def compact_json(record: dict[str, Any]) -> str:
    return json.dumps(record, ensure_ascii=False, separators=(",", ":"))


def base_document(dataset: str, row: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}

    if dataset.startswith("resultados_estado_"):
        out["cve_ent"] = row["cve_ent"]
    else:
        # cve_mun es redundante con cvegeo y se conserva en catalogo_municipios.
        out["cve_ent"] = row["cve_ent"]
        out["cvegeo"] = row["cvegeo"]

    # estado-dia usa fecha como única dimensión temporal; anio/mes son derivables.
    if dataset == "resultados_estado_dia":
        out["fecha"] = row["fecha"]
    else:
        out["anio"] = row["anio"]
        if dataset.endswith("_mes"):
            out["mes"] = row["mes"]

    out["cluster"] = row["cluster"]
    return out


def transform(dataset: str, row: dict[str, Any]) -> dict[str, Any]:
    out = base_document(dataset, row)

    for source, target in METRIC_MAP.items():
        if source in row:
            if target in out and out[target] != row[source]:
                raise ValueError(
                    f"Colisión de campo {target}: {out[target]!r} != {row[source]!r}"
                )
            out[target] = row[source]

    return out


def prepare_output_dir(path: Path, overwrite: bool) -> None:
    if path.exists():
        if not overwrite:
            raise FileExistsError(
                f"La carpeta de salida ya existe: {path}. Usa --overwrite para reemplazarla."
            )
        shutil.rmtree(path)
    path.mkdir(parents=True, exist_ok=True)


def copy_catalog(input_dir: Path, output_dir: Path, filename: str) -> None:
    source = input_dir / filename
    if not source.is_file():
        raise FileNotFoundError(f"Falta catálogo requerido: {source}")
    shutil.copy2(source, output_dir / filename)


def main() -> None:
    args = parse_args()
    input_dir = args.input_dir.resolve()
    output_dir = args.output_dir.resolve()

    missing = [
        f"{name}.jsonl"
        for name in DATASETS
        if not (input_dir / f"{name}.jsonl").is_file()
    ]
    if missing:
        raise FileNotFoundError(
            "Faltan archivos v2 requeridos:\n- " + "\n- ".join(missing)
        )

    prepare_output_dir(output_dir, args.overwrite)

    for catalog in ("clusters.jsonl", "estados.jsonl", "municipios.jsonl"):
        copy_catalog(input_dir, output_dir, catalog)

    report: dict[str, Any] = {"datasets": {}, "catalogos": {}, "total": {}}
    original_total = 0
    mongo_ready_total = 0
    total_rows = 0

    for dataset in DATASETS:
        source_path = input_dir / f"{dataset}.jsonl"
        target_path = output_dir / f"{dataset}.jsonl"
        rows = 0

        print(f"Generando {target_path.name}...")
        with source_path.open("r", encoding="utf-8") as source, target_path.open(
            "w", encoding="utf-8", newline="\n"
        ) as target:
            for line_number, line in enumerate(source, start=1):
                if not line.strip():
                    continue
                try:
                    row = json.loads(line)
                    compact = transform(dataset, row)
                except Exception as exc:
                    raise ValueError(
                        f"Error en {source_path.name}, línea {line_number}: {exc}"
                    ) from exc

                target.write(compact_json(compact))
                target.write("\n")
                rows += 1

                if rows % 100_000 == 0:
                    print(f"  {rows:,} registros")

        source_bytes = source_path.stat().st_size
        target_bytes = target_path.stat().st_size
        report["datasets"][dataset] = {
            "registros": rows,
            "bytes_origen_v2": source_bytes,
            "bytes_mongo_ready": target_bytes,
            "mib_mongo_ready": round(target_bytes / (1024**2), 2),
            "reduccion_porcentual": round(100 * (1 - target_bytes / source_bytes), 2),
        }
        original_total += source_bytes
        mongo_ready_total += target_bytes
        total_rows += rows

    for catalog in ("clusters.jsonl", "estados.jsonl", "municipios.jsonl"):
        size = (output_dir / catalog).stat().st_size
        report["catalogos"][catalog] = size
        mongo_ready_total += size

    report["total"] = {
        "registros_resultados": total_rows,
        "bytes_origen_v2_resultados": original_total,
        "bytes_mongo_ready_incluyendo_catalogos": mongo_ready_total,
        "mib_mongo_ready_incluyendo_catalogos": round(mongo_ready_total / (1024**2), 2),
        "reduccion_vs_resultados_v2_porcentual": round(
            100 * (1 - mongo_ready_total / original_total), 2
        ),
    }

    report_path = output_dir / "reporte_mongo_ready.json"
    with report_path.open("w", encoding="utf-8") as target:
        json.dump(report, target, ensure_ascii=False, indent=2)
        target.write("\n")

    print("\nGeneración mongo-ready terminada.")
    print(f"Reporte: {report_path}")
    print(
        "Tamaño total mongo-ready: "
        f"{report['total']['mib_mongo_ready_incluyendo_catalogos']:.2f} MiB"
    )


if __name__ == "__main__":
    main()
