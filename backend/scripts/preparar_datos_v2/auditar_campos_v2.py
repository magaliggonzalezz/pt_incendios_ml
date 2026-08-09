#!/usr/bin/env python3
"""Audita el peso aproximado por campo y compara perfiles de almacenamiento v2.

Trabaja sobre los JSONL compactos generados por transformar_resultados.py. No modifica
archivos ni se conecta a MongoDB. El objetivo es cuantificar qué campos dominan el peso
y estimar el ahorro de distintos perfiles antes de definir el esquema definitivo.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


DATASETS = [
    "resultados_estado_anio",
    "resultados_estado_mes",
    "resultados_estado_dia",
    "resultados_municipio_anio",
    "resultados_municipio_mes",
]

# Campos necesarios para identificar territorio, periodo y patrón dominante.
BASE_FIELDS = {
    "cve_ent",
    "cve_mun",
    "cvegeo",
    "fecha",
    "anio",
    "mes",
    "cluster",
}

# Métricas que actualmente encajan con mapas/resúmenes del dashboard.
INTERACTIVE_METRICS = {
    "dias_observados",
    "municipios_observados",
    "dias_con_incendio_activo",
    "dias_con_patron_extremo",
    "dias_con_conafor",
    "dias_con_firms",
    "dias_con_smn",
    "conafor_event_count_total",
    "conafor_total_hectareas_total",
    "firms_detection_count_total",
    "firms_frp_total",
    "smn_station_count_promedio",
    "precipitacion_mm_promedio",
    "temperatura_minima_c_promedio",
    "temperatura_maxima_c_promedio",
}

# Distribución de días por cluster: útil para explicar cómo se obtiene el patrón dominante
# en resúmenes mensuales/anuales y para gráficas de composición.
CLUSTER_DISTRIBUTION_FIELDS = {f"dias_cluster_{i}" for i in range(7)}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Audita peso por campo y perfiles de los JSONL v2."
    )
    parser.add_argument(
        "--input-dir",
        type=Path,
        default=Path("data_v2_generada"),
        help="Carpeta con los JSONL v2 generados (default: ./data_v2_generada).",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Ruta del reporte JSON. Default: <input-dir>/reporte_auditoria_campos.json",
    )
    return parser.parse_args()


def encoded_size(value: Any) -> int:
    return len(json.dumps(value, ensure_ascii=False, separators=(",", ":")).encode("utf-8"))


def projected_record_size(row: dict[str, Any], fields: set[str]) -> int:
    projected = {key: value for key, value in row.items() if key in fields}
    return len(json.dumps(projected, ensure_ascii=False, separators=(",", ":")).encode("utf-8")) + 1


def main() -> None:
    args = parse_args()
    input_dir = args.input_dir.resolve()
    output_path = (args.output or input_dir / "reporte_auditoria_campos.json").resolve()

    missing = [name for name in DATASETS if not (input_dir / f"{name}.jsonl").is_file()]
    if missing:
        raise FileNotFoundError(
            "Faltan JSONL v2:\n- " + "\n- ".join(f"{name}.jsonl" for name in missing)
        )

    report: dict[str, Any] = {"datasets": {}, "global": {}}
    global_field_bytes: Counter[str] = Counter()
    global_field_occurrences: Counter[str] = Counter()
    global_profile_bytes: Counter[str] = Counter()
    global_original_bytes = 0
    global_rows = 0

    for dataset in DATASETS:
        path = input_dir / f"{dataset}.jsonl"
        print(f"Auditando {path.name}...")

        field_bytes: Counter[str] = Counter()
        field_occurrences: Counter[str] = Counter()
        type_counts: dict[str, Counter[str]] = defaultdict(Counter)
        profile_bytes: Counter[str] = Counter()
        rows = 0

        with path.open("r", encoding="utf-8") as source:
            for line_number, line in enumerate(source, start=1):
                if not line.strip():
                    continue
                row = json.loads(line)
                rows += 1

                for key, value in row.items():
                    # Aproxima la contribución JSON del campo como clave + ':' + valor + coma.
                    contribution = encoded_size(key) + 1 + encoded_size(value) + 1
                    field_bytes[key] += contribution
                    field_occurrences[key] += 1
                    type_counts[key][type(value).__name__] += 1

                all_fields = set(row.keys())
                minimum_fields = BASE_FIELDS & all_fields
                interactive_fields = (BASE_FIELDS | INTERACTIVE_METRICS) & all_fields
                explanatory_fields = (
                    BASE_FIELDS | INTERACTIVE_METRICS | CLUSTER_DISTRIBUTION_FIELDS
                ) & all_fields

                profile_bytes["minimo"] += projected_record_size(row, minimum_fields)
                profile_bytes["interactivo"] += projected_record_size(row, interactive_fields)
                profile_bytes["interactivo_con_distribucion"] += projected_record_size(
                    row, explanatory_fields
                )
                profile_bytes["completo"] += len(line.encode("utf-8"))

                if rows % 100_000 == 0:
                    print(f"  {rows:,} registros")

        dataset_size = path.stat().st_size
        sorted_fields = sorted(field_bytes, key=field_bytes.get, reverse=True)

        report["datasets"][dataset] = {
            "registros": rows,
            "bytes_archivo": dataset_size,
            "campos": [
                {
                    "campo": field,
                    "bytes_aprox": field_bytes[field],
                    "porcentaje_archivo_aprox": round(100 * field_bytes[field] / dataset_size, 3),
                    "ocurrencias": field_occurrences[field],
                    "tipos": dict(type_counts[field]),
                }
                for field in sorted_fields
            ],
            "perfiles": {
                profile: {
                    "bytes_estimados_jsonl": size,
                    "porcentaje_del_completo": round(100 * size / profile_bytes["completo"], 2),
                    "reduccion_porcentual": round(100 * (1 - size / profile_bytes["completo"]), 2),
                }
                for profile, size in profile_bytes.items()
            },
        }

        global_original_bytes += dataset_size
        global_rows += rows
        global_field_bytes.update(field_bytes)
        global_field_occurrences.update(field_occurrences)
        global_profile_bytes.update(profile_bytes)

    report["global"] = {
        "registros": global_rows,
        "bytes_archivos": global_original_bytes,
        "campos_mas_costosos": [
            {
                "campo": field,
                "bytes_aprox": size,
                "ocurrencias": global_field_occurrences[field],
            }
            for field, size in global_field_bytes.most_common()
        ],
        "perfiles": {
            profile: {
                "bytes_estimados_jsonl": size,
                "mb_estimados": round(size / (1024**2), 2),
                "porcentaje_del_completo": round(100 * size / global_profile_bytes["completo"], 2),
                "reduccion_porcentual": round(100 * (1 - size / global_profile_bytes["completo"]), 2),
            }
            for profile, size in global_profile_bytes.items()
        },
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as target:
        json.dump(report, target, ensure_ascii=False, indent=2)
        target.write("\n")

    print("\nAuditoría terminada.")
    print(f"Reporte: {output_path}")
    print("Perfiles globales estimados:")
    for profile, data in report["global"]["perfiles"].items():
        print(
            f"  {profile}: {data['mb_estimados']:.2f} MiB "
            f"({data['reduccion_porcentual']:.2f}% menos que completo)"
        )


if __name__ == "__main__":
    main()
