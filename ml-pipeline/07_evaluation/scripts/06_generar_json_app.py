# -*- coding: utf-8 -*-
"""
Evaluation 06 | JSON ligeros para app

Este script:
- Lee salidas validadas de 07_evaluation/datasets.
- Convierte catálogos, resúmenes y samples a JSON.
- Genera archivos ligeros listos para API/frontend.
- No convierte los datasets completos grandes a JSON.
"""

from pathlib import Path
import json
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]
EVALUATION_DIR = PROJECT_ROOT / "07_evaluation"

DATASETS_DIR = EVALUATION_DIR / "datasets"
REPORTS_DIR = EVALUATION_DIR / "reports"
APP_READY_DIR = EVALUATION_DIR / "app_ready"

REPORTS_DIR.mkdir(parents=True, exist_ok=True)
APP_READY_DIR.mkdir(parents=True, exist_ok=True)

OUTPUT_DIAGNOSTICO = REPORTS_DIR / "evaluation_06_diagnostico_json_app.csv"
OUTPUT_RESUMEN = REPORTS_DIR / "evaluation_06_resumen_json_app.json"


FLOWS = {
    "municipio_dia": {
        "input_dir": DATASETS_DIR / "municipio_dia",
        "output_dir": APP_READY_DIR / "municipio_dia",
        "files": {
            "clusters": "app_cluster_catalog.csv",
            "sample": "app_municipio_dia_sample.csv",
            "resumen_cluster": "app_resumen_cluster.csv",
            "resumen_mes": "app_resumen_mes.csv",
            "resumen_entidad": "app_resumen_entidad.csv",
            "resumen_municipio": "app_resumen_municipio.csv",
            "resumen_entidad_cluster": "app_resumen_entidad_cluster.csv",
            "resumen_municipio_cluster": "app_resumen_municipio_cluster.csv",
        },
    },
    "entidad_dia": {
        "input_dir": DATASETS_DIR / "entidad_dia",
        "output_dir": APP_READY_DIR / "entidad_dia",
        "files": {
            "clusters": "app_cluster_catalog.csv",
            "sample": "app_entidad_dia_sample.csv",
            "resumen_cluster": "app_resumen_cluster.csv",
            "resumen_mes": "app_resumen_mes.csv",
            "resumen_entidad": "app_resumen_entidad.csv",
            "resumen_entidad_cluster": "app_resumen_entidad_cluster.csv",
        },
    },
}


def add(rows, flujo, archivo, estado, detalle):
    rows.append({
        "flujo": flujo,
        "archivo": archivo,
        "estado": estado,
        "detalle": detalle,
    })


def normalize_df(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    df.columns = (
        df.columns
        .str.strip()
        .str.lower()
        .str.replace(" ", "_", regex=False)
    )

    df = df.where(pd.notna(df), None)

    return df


def csv_to_json(input_path: Path, output_path: Path) -> int:
    df = pd.read_csv(input_path, encoding="utf-8-sig", low_memory=False)
    df = normalize_df(df)

    records = df.to_dict(orient="records")

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(records, f, ensure_ascii=False, indent=2)

    return len(records)


def main():
    print("\nEvaluation 06 | JSON ligeros para app")

    rows = []
    resumen_flujos = {}

    for flujo, cfg in FLOWS.items():
        print(f"\nProcesando flujo: {flujo}")

        input_dir = cfg["input_dir"]
        output_dir = cfg["output_dir"]
        output_dir.mkdir(parents=True, exist_ok=True)

        flujo_info = {
            "input_dir": str(input_dir),
            "output_dir": str(output_dir),
            "archivos_generados": {},
        }

        for key, filename in cfg["files"].items():
            input_path = input_dir / filename
            output_path = output_dir / filename.replace(".csv", ".json")

            if not input_path.exists():
                add(rows, flujo, filename, "ERROR", f"No existe: {input_path}")
                continue

            print(f"  Convirtiendo {filename} -> {output_path.name}")

            n = csv_to_json(input_path, output_path)

            add(rows, flujo, output_path.name, "OK", f"Registros JSON: {n}")
            flujo_info["archivos_generados"][key] = {
                "archivo": str(output_path),
                "registros": int(n),
            }

        # Índice por flujo para que el backend/frontend sepa qué cargar
        index_path = output_dir / "index.json"

        with open(index_path, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "flujo": flujo,
                    "descripcion": (
                        "municipio-día principal" if flujo == "municipio_dia"
                        else "entidad-día complementario"
                    ),
                    "archivos": flujo_info["archivos_generados"],
                },
                f,
                ensure_ascii=False,
                indent=2,
            )

        add(rows, flujo, "index.json", "OK", str(index_path))
        flujo_info["index"] = str(index_path)

        resumen_flujos[flujo] = flujo_info

    diagnostico = pd.DataFrame(rows)
    diagnostico.to_csv(OUTPUT_DIAGNOSTICO, index=False, encoding="utf-8-sig")

    resumen = {
        "fase_crisp_dm": "Evaluation",
        "objetivo": "Generar JSON ligeros para consumo de API/frontend",
        "nota": "No se convierte el dataset completo grande a JSON; solo catálogos, resúmenes y samples.",
        "flujos": resumen_flujos,
        "resultado_general": {
            "validaciones_totales": int(len(diagnostico)),
            "ok": int((diagnostico["estado"] == "OK").sum()),
            "warnings": int((diagnostico["estado"] == "WARNING").sum()),
            "errores": int((diagnostico["estado"] == "ERROR").sum()),
        },
        "archivo_diagnostico": str(OUTPUT_DIAGNOSTICO),
    }

    with open(OUTPUT_RESUMEN, "w", encoding="utf-8") as f:
        json.dump(resumen, f, ensure_ascii=False, indent=2)

    print("\nArchivos generados:")
    print(f"- {OUTPUT_DIAGNOSTICO}")
    print(f"- {OUTPUT_RESUMEN}")

    print("\nResumen:")
    print(f"- Validaciones totales: {len(diagnostico)}")
    print(f"- OK: {(diagnostico['estado'] == 'OK').sum()}")
    print(f"- Warnings: {(diagnostico['estado'] == 'WARNING').sum()}")
    print(f"- Errores: {(diagnostico['estado'] == 'ERROR').sum()}")

    if (diagnostico["estado"] == "ERROR").any():
        print("\nProceso terminado con errores.")
    else:
        print("\nProceso terminado correctamente.")


if __name__ == "__main__":
    main()