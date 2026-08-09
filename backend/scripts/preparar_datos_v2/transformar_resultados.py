#!/usr/bin/env python3
"""Transforma los JSONL finales de evaluation a documentos compactos para la BD v2.

El script trabaja en streaming para poder procesar archivos grandes sin cargarlos completos
en memoria. No se conecta a MongoDB: únicamente genera artefactos locales que después se
pueden validar, medir e importar de forma controlada.
"""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path
from typing import Any


DATASETS = {
    "resultados_estado_anio": "app_estado_anio_resultados.jsonl",
    "resultados_estado_mes": "app_estado_mes_resultados.jsonl",
    "resultados_estado_dia": "app_estado_dia_resultados.jsonl",
    "resultados_municipio_anio": "app_municipio_anio_resultados.jsonl",
    "resultados_municipio_mes": "app_municipio_mes_resultados.jsonl",
}

CLUSTER_FIELDS = {
    "estado_app_dominante",
    "etiqueta_final_dominante",
    "color_sugerido_app",
    "prioridad_visual_app",
}

STATE_CATALOG_FIELDS = {"estado", "estado_area_km2"}
MUNICIPALITY_CATALOG_FIELDS = {"estado", "municipio", "municipio_area_km2"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Genera JSONL compactos y catálogos para incendios_forestales_v2."
    )
    parser.add_argument(
        "--input-dir",
        type=Path,
        required=True,
        help="Carpeta que contiene los cinco JSONL finales de consulta.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        required=True,
        help="Carpeta donde se escribirán los artefactos v2.",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Permite reemplazar una carpeta de salida existente.",
    )
    return parser.parse_args()


def normalize_code(value: Any, width: int, field: str) -> str:
    if value is None or value == "":
        raise ValueError(f"{field} no puede estar vacío")

    text = str(value).strip()
    if text.endswith(".0") and text[:-2].isdigit():
        text = text[:-2]

    if not text.isdigit():
        raise ValueError(f"{field} debe ser numérico; recibido: {value!r}")

    if len(text) > width:
        raise ValueError(f"{field} excede {width} caracteres: {value!r}")

    return text.zfill(width)


def normalize_int(value: Any, field: str) -> int:
    if value is None or value == "":
        raise ValueError(f"{field} no puede estar vacío")
    return int(value)


def compact_json(record: dict[str, Any]) -> str:
    return json.dumps(record, ensure_ascii=False, separators=(",", ":"))


def merge_catalog_entry(
    catalog: dict[str, dict[str, Any]],
    key: str,
    entry: dict[str, Any],
    catalog_name: str,
) -> None:
    previous = catalog.get(key)
    if previous is None:
        catalog[key] = entry
        return

    # Los catálogos se consideran dimensiones estables. Si dos fuentes finales discrepan,
    # es preferible detener la transformación que ocultar la inconsistencia.
    for field, value in entry.items():
        old_value = previous.get(field)
        if old_value is None and value is not None:
            previous[field] = value
        elif value is not None and old_value != value:
            if isinstance(value, float) and isinstance(old_value, float):
                if abs(old_value - value) <= 1e-6:
                    continue
            raise ValueError(
                f"Inconsistencia en {catalog_name} {key}, campo {field}: "
                f"{old_value!r} != {value!r}"
            )


def register_cluster(clusters: dict[str, dict[str, Any]], row: dict[str, Any]) -> None:
    cluster_id = normalize_int(row["cluster_dominante"], "cluster_dominante")
    key = str(cluster_id)
    entry = {
        "cluster": cluster_id,
        "estado_app": row.get("estado_app_dominante"),
        "etiqueta_final": row.get("etiqueta_final_dominante"),
        "color": row.get("color_sugerido_app"),
        "prioridad_visual": row.get("prioridad_visual_app"),
    }
    merge_catalog_entry(clusters, key, entry, "clusters")


def register_state(states: dict[str, dict[str, Any]], row: dict[str, Any]) -> str:
    cve_ent = normalize_code(row["cve_ent"], 2, "cve_ent")
    entry = {
        "cve_ent": cve_ent,
        "nombre": row.get("estado"),
        "area_km2": row.get("estado_area_km2"),
    }
    merge_catalog_entry(states, cve_ent, entry, "estados")
    return cve_ent


def register_municipality(
    municipalities: dict[str, dict[str, Any]], row: dict[str, Any]
) -> tuple[str, str, str]:
    cve_ent = normalize_code(row["cve_ent"], 2, "cve_ent")
    cve_mun = normalize_code(row["cve_mun"], 3, "cve_mun")
    cvegeo_from_parts = f"{cve_ent}{cve_mun}"

    raw_cvegeo = row.get("cvegeo")
    cvegeo = (
        normalize_code(raw_cvegeo, 5, "cvegeo")
        if raw_cvegeo not in (None, "")
        else cvegeo_from_parts
    )

    if cvegeo != cvegeo_from_parts:
        raise ValueError(
            f"cvegeo inconsistente: {cvegeo} != {cvegeo_from_parts} "
            f"({row.get('estado')} / {row.get('municipio')})"
        )

    entry = {
        "cvegeo": cvegeo,
        "cve_ent": cve_ent,
        "cve_mun": cve_mun,
        "estado": row.get("estado"),
        "nombre": row.get("municipio"),
        "area_km2": row.get("municipio_area_km2"),
    }
    merge_catalog_entry(municipalities, cvegeo, entry, "municipios")
    return cve_ent, cve_mun, cvegeo


def transform_row(
    dataset: str,
    row: dict[str, Any],
    clusters: dict[str, dict[str, Any]],
    states: dict[str, dict[str, Any]],
    municipalities: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    register_cluster(clusters, row)

    output = dict(row)
    output["cluster"] = normalize_int(output.pop("cluster_dominante"), "cluster_dominante")

    for field in CLUSTER_FIELDS:
        output.pop(field, None)

    if dataset.startswith("resultados_estado_"):
        cve_ent = register_state(states, row)
        output["cve_ent"] = cve_ent
        for field in STATE_CATALOG_FIELDS:
            output.pop(field, None)
    else:
        cve_ent, cve_mun, cvegeo = register_municipality(municipalities, row)
        output["cve_ent"] = cve_ent
        output["cve_mun"] = cve_mun
        output["cvegeo"] = cvegeo
        for field in MUNICIPALITY_CATALOG_FIELDS:
            output.pop(field, None)

    if "anio" in output:
        output["anio"] = normalize_int(output["anio"], "anio")
    if "mes" in output:
        output["mes"] = normalize_int(output["mes"], "mes")

    return output


def process_dataset(
    dataset: str,
    input_path: Path,
    output_path: Path,
    clusters: dict[str, dict[str, Any]],
    states: dict[str, dict[str, Any]],
    municipalities: dict[str, dict[str, Any]],
) -> int:
    count = 0
    with input_path.open("r", encoding="utf-8-sig") as source, output_path.open(
        "w", encoding="utf-8", newline="\n"
    ) as target:
        for line_number, line in enumerate(source, start=1):
            if not line.strip():
                continue
            try:
                row = json.loads(line)
                transformed = transform_row(
                    dataset, row, clusters, states, municipalities
                )
            except Exception as exc:
                raise ValueError(
                    f"Error en {input_path.name}, línea {line_number}: {exc}"
                ) from exc

            target.write(compact_json(transformed))
            target.write("\n")
            count += 1

            if count % 100_000 == 0:
                print(f"  {dataset}: {count:,} registros")

    return count


def write_catalog(path: Path, records: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8", newline="\n") as target:
        for record in records:
            target.write(compact_json(record))
            target.write("\n")


def prepare_output_dir(path: Path, overwrite: bool) -> None:
    if path.exists():
        if not overwrite:
            raise FileExistsError(
                f"La carpeta de salida ya existe: {path}. Usa --overwrite para reemplazarla."
            )
        shutil.rmtree(path)
    path.mkdir(parents=True, exist_ok=True)


def main() -> None:
    args = parse_args()
    input_dir = args.input_dir.resolve()
    output_dir = args.output_dir.resolve()

    missing = [
        filename
        for filename in DATASETS.values()
        if not (input_dir / filename).is_file()
    ]
    if missing:
        raise FileNotFoundError(
            "Faltan archivos requeridos en --input-dir:\n- " + "\n- ".join(missing)
        )

    prepare_output_dir(output_dir, args.overwrite)

    clusters: dict[str, dict[str, Any]] = {}
    states: dict[str, dict[str, Any]] = {}
    municipalities: dict[str, dict[str, Any]] = {}
    counts: dict[str, int] = {}

    print(f"Entrada: {input_dir}")
    print(f"Salida:  {output_dir}")

    for dataset, filename in DATASETS.items():
        print(f"Procesando {filename}...")
        counts[dataset] = process_dataset(
            dataset=dataset,
            input_path=input_dir / filename,
            output_path=output_dir / f"{dataset}.jsonl",
            clusters=clusters,
            states=states,
            municipalities=municipalities,
        )
        print(f"  OK: {counts[dataset]:,} registros")

    cluster_records = sorted(clusters.values(), key=lambda x: x["cluster"])
    state_records = sorted(states.values(), key=lambda x: x["cve_ent"])
    municipality_records = sorted(
        municipalities.values(), key=lambda x: x["cvegeo"]
    )

    write_catalog(output_dir / "clusters.jsonl", cluster_records)
    write_catalog(output_dir / "estados.jsonl", state_records)
    write_catalog(output_dir / "municipios.jsonl", municipality_records)

    report = {
        "datasets": counts,
        "catalogos": {
            "clusters": len(cluster_records),
            "estados": len(state_records),
            "municipios": len(municipality_records),
        },
        "archivos": {
            path.name: path.stat().st_size
            for path in sorted(output_dir.glob("*.jsonl"))
        },
    }

    with (output_dir / "reporte_transformacion.json").open(
        "w", encoding="utf-8"
    ) as target:
        json.dump(report, target, ensure_ascii=False, indent=2)
        target.write("\n")

    print("\nTransformación terminada.")
    print(f"Clusters:   {len(cluster_records):,}")
    print(f"Estados:    {len(state_records):,}")
    print(f"Municipios: {len(municipality_records):,}")
    print(f"Reporte:    {output_dir / 'reporte_transformacion.json'}")


if __name__ == "__main__":
    main()
