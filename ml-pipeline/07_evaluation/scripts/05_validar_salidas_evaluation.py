# -*- coding: utf-8 -*-
"""
Evaluation 05 | Validación final de salidas para app

Este script:
- Valida salidas generadas en 07_evaluation para municipio-día y entidad-día.
- Confirma existencia de datasets, resúmenes y reports.
- Verifica conteos principales y clusters esperados.
- No modifica Modeling, Feature Engineering, Integration ni Data Preparation.
"""

from pathlib import Path
import json
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]
EVALUATION_DIR = PROJECT_ROOT / "07_evaluation"

REPORTS_DIR = EVALUATION_DIR / "reports"
REPORTS_DIR.mkdir(parents=True, exist_ok=True)

OUTPUT_VALIDACION = REPORTS_DIR / "evaluation_05_validacion_final_outputs_app.csv"
OUTPUT_RESUMEN = REPORTS_DIR / "evaluation_05_resumen_final_outputs_app.json"


FLOWS = {
    "municipio_dia": {
        "datasets_dir": EVALUATION_DIR / "datasets" / "municipio_dia",
        "reports_dir": EVALUATION_DIR / "reports" / "municipio_dia",
        "dataset": "app_municipio_dia.csv",
        "sample": "app_municipio_dia_sample.csv",
        "catalog": "app_cluster_catalog.csv",
        "expected_rows": 11_154_221,
        "expected_clusters": 11,
        "required_datasets": [
            "app_cluster_catalog.csv",
            "app_municipio_dia.csv",
            "app_municipio_dia_sample.csv",
            "app_resumen_cluster.csv",
            "app_resumen_mes.csv",
            "app_resumen_entidad.csv",
            "app_resumen_municipio.csv",
            "app_resumen_entidad_cluster.csv",
            "app_resumen_municipio_cluster.csv",
        ],
        "required_reports": [
            "evaluation_01_diagnostico_modelo_final.csv",
            "evaluation_01_resumen_catalogo_clusters.json",
            "evaluation_02_diagnostico_dataset_app.csv",
            "evaluation_02_resumen_dataset_app.json",
            "evaluation_03_diagnostico_resumenes_app.csv",
            "evaluation_03_resumen_resumenes_app.json",
        ],
    },
    "entidad_dia": {
        "datasets_dir": EVALUATION_DIR / "datasets" / "entidad_dia",
        "reports_dir": EVALUATION_DIR / "reports" / "entidad_dia",
        "dataset": "app_entidad_dia.csv",
        "sample": "app_entidad_dia_sample.csv",
        "catalog": "app_cluster_catalog.csv",
        "expected_rows": 292_146,
        "expected_clusters": 9,
        "required_datasets": [
            "app_cluster_catalog.csv",
            "app_entidad_dia.csv",
            "app_entidad_dia_sample.csv",
            "app_resumen_cluster.csv",
            "app_resumen_mes.csv",
            "app_resumen_entidad.csv",
            "app_resumen_entidad_cluster.csv",
        ],
        "required_reports": [
            "evaluation_04_diagnostico_outputs_entidad_dia.csv",
            "evaluation_04_resumen_outputs_entidad_dia.json",
        ],
    },
}


def add(rows, flujo, validacion, estado, detalle):
    rows.append({
        "flujo": flujo,
        "validacion": validacion,
        "estado": estado,
        "detalle": detalle,
    })


def count_rows_csv(path: Path) -> int:
    total = 0
    for chunk in pd.read_csv(path, chunksize=500_000, encoding="utf-8-sig", low_memory=False):
        total += len(chunk)
    return total


def get_cluster_count(path: Path) -> int:
    clusters = set()

    for chunk in pd.read_csv(
        path,
        usecols=lambda c: c.strip().lower() in ["cluster_id"],
        chunksize=500_000,
        encoding="utf-8-sig",
        low_memory=False,
    ):
        chunk.columns = chunk.columns.str.strip().str.lower()
        clusters.update(pd.to_numeric(chunk["cluster_id"], errors="coerce").dropna().astype(int).unique().tolist())

    return len(clusters)


def main():
    print("\nEvaluation 05 | Validación final de outputs para app")

    rows = []
    resumen_flujos = {}

    for flujo, cfg in FLOWS.items():
        print(f"\nValidando flujo: {flujo}")

        datasets_dir = cfg["datasets_dir"]
        reports_dir = cfg["reports_dir"]

        add(
            rows,
            flujo,
            "existe_carpeta_datasets",
            "OK" if datasets_dir.exists() else "ERROR",
            str(datasets_dir),
        )

        add(
            rows,
            flujo,
            "existe_carpeta_reports",
            "OK" if reports_dir.exists() else "ERROR",
            str(reports_dir),
        )

        for filename in cfg["required_datasets"]:
            path = datasets_dir / filename
            add(
                rows,
                flujo,
                f"existe_dataset_{filename}",
                "OK" if path.exists() else "ERROR",
                str(path),
            )

        for filename in cfg["required_reports"]:
            path = reports_dir / filename
            add(
                rows,
                flujo,
                f"existe_report_{filename}",
                "OK" if path.exists() else "ERROR",
                str(path),
            )

        dataset_path = datasets_dir / cfg["dataset"]
        catalog_path = datasets_dir / cfg["catalog"]
        sample_path = datasets_dir / cfg["sample"]

        row_count = None
        cluster_count = None
        catalog_cluster_count = None
        sample_rows = None

        if dataset_path.exists():
            print(f"  Contando filas dataset principal: {dataset_path.name}")
            row_count = count_rows_csv(dataset_path)

            add(
                rows,
                flujo,
                "conteo_filas_dataset_principal",
                "OK" if row_count == cfg["expected_rows"] else "WARNING",
                f"Filas detectadas: {row_count:,}; esperadas: {cfg['expected_rows']:,}",
            )

            cluster_count = get_cluster_count(dataset_path)

            add(
                rows,
                flujo,
                "clusters_dataset_principal",
                "OK" if cluster_count == cfg["expected_clusters"] else "WARNING",
                f"Clusters detectados: {cluster_count}; esperados: {cfg['expected_clusters']}",
            )

        if catalog_path.exists():
            catalog = pd.read_csv(catalog_path, encoding="utf-8-sig")
            catalog.columns = catalog.columns.str.strip().str.lower()
            catalog_cluster_count = catalog["cluster_id"].nunique() if "cluster_id" in catalog.columns else None

            add(
                rows,
                flujo,
                "clusters_catalogo",
                "OK" if catalog_cluster_count == cfg["expected_clusters"] else "WARNING",
                f"Clusters catálogo: {catalog_cluster_count}; esperados: {cfg['expected_clusters']}",
            )

        if sample_path.exists():
            sample_rows = count_rows_csv(sample_path)

            add(
                rows,
                flujo,
                "sample_con_filas",
                "OK" if sample_rows > 0 else "WARNING",
                f"Filas sample: {sample_rows:,}",
            )

        resumen_flujos[flujo] = {
            "dataset_principal": str(dataset_path),
            "filas_dataset": row_count,
            "filas_esperadas": cfg["expected_rows"],
            "clusters_dataset": cluster_count,
            "clusters_catalogo": catalog_cluster_count,
            "clusters_esperados": cfg["expected_clusters"],
            "filas_sample": sample_rows,
        }

    df = pd.DataFrame(rows)
    df.to_csv(OUTPUT_VALIDACION, index=False, encoding="utf-8-sig")

    resumen = {
        "fase_crisp_dm": "Evaluation",
        "objetivo": "Validación final de salidas para aplicación web",
        "flujos_validados": list(FLOWS.keys()),
        "resultado_general": {
            "validaciones_totales": int(len(df)),
            "ok": int((df["estado"] == "OK").sum()),
            "warnings": int((df["estado"] == "WARNING").sum()),
            "errores": int((df["estado"] == "ERROR").sum()),
        },
        "flujos": resumen_flujos,
        "archivo_validacion": str(OUTPUT_VALIDACION),
    }

    with open(OUTPUT_RESUMEN, "w", encoding="utf-8") as f:
        json.dump(resumen, f, ensure_ascii=False, indent=2)

    print("\nArchivos generados:")
    print(f"- {OUTPUT_VALIDACION}")
    print(f"- {OUTPUT_RESUMEN}")

    print("\nResumen final:")
    print(f"- Validaciones totales: {len(df)}")
    print(f"- OK: {(df['estado'] == 'OK').sum()}")
    print(f"- Warnings: {(df['estado'] == 'WARNING').sum()}")
    print(f"- Errores: {(df['estado'] == 'ERROR').sum()}")

    if (df["estado"] == "ERROR").any():
        print("\nProceso terminado con errores.")
    else:
        print("\nProceso terminado correctamente.")


if __name__ == "__main__":
    main()