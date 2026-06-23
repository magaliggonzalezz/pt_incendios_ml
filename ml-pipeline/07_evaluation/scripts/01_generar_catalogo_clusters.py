# -*- coding: utf-8 -*-
"""
Evaluation 01 | Catálogo interpretable de clusters

Este script:
- Lee salidas cerradas de Modeling para municipio-día.
- Genera un catálogo interpretable de clusters para la app.
- Genera un diagnóstico técnico mínimo del modelo final.
- No reentrena modelos.
- No modifica archivos de Modeling.
"""

from pathlib import Path
import json
import pandas as pd
import numpy as np


# ============================================================
# Configuración de rutas
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

MODELING_DIR = PROJECT_ROOT / "06_modeling"
EVALUATION_DIR = PROJECT_ROOT / "07_evaluation"

MODELING_RESULTS_DIR = MODELING_DIR / "results" / "municipio_dia" / "som_kmeans"
MODELING_REPORTS_DIR = MODELING_DIR / "reports"

EVAL_DATASETS_DIR = EVALUATION_DIR / "datasets"
EVAL_REPORTS_DIR = EVALUATION_DIR / "reports"

EVAL_DATASETS_DIR.mkdir(parents=True, exist_ok=True)
EVAL_REPORTS_DIR.mkdir(parents=True, exist_ok=True)

INPUT_CLUSTER_PROFILE = MODELING_RESULTS_DIR / "som_kmeans_cluster_profile.csv"
INPUT_FEATURE_PROFILE = MODELING_RESULTS_DIR / "som_kmeans_feature_profile.csv"
INPUT_ENTITY_DISTRIBUTION = MODELING_RESULTS_DIR / "som_kmeans_cluster_entity_distribution.csv"
INPUT_MONTH_DISTRIBUTION = MODELING_RESULTS_DIR / "som_kmeans_cluster_month_distribution.csv"
INPUT_DECISION_JSON = MODELING_REPORTS_DIR / "modeling_10_decision_modelo_candidato_municipio_dia.json"

OUTPUT_CLUSTER_CATALOG = EVAL_DATASETS_DIR / "app_cluster_catalog.csv"
OUTPUT_DIAGNOSTICO = EVAL_REPORTS_DIR / "evaluation_01_diagnostico_modelo_final.csv"
OUTPUT_RESUMEN_JSON = EVAL_REPORTS_DIR / "evaluation_01_resumen_catalogo_clusters.json"


# ============================================================
# Utilidades
# ============================================================

def read_csv_required(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"No existe el archivo requerido: {path}")
    return pd.read_csv(path, encoding="utf-8-sig")


def read_json_optional(path: Path) -> dict:
    if not path.exists():
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = (
        df.columns
        .str.strip()
        .str.lower()
        .str.replace(" ", "_", regex=False)
    )
    return df


def find_cluster_column(df: pd.DataFrame) -> str:
    candidates = [
        "cluster_id",
        "cluster",
        "kmeans_cluster",
        "som_kmeans_cluster",
        "cluster_kmeans",
    ]

    for col in candidates:
        if col in df.columns:
            return col

    possible = [c for c in df.columns if "cluster" in c]
    if possible:
        return possible[0]

    raise ValueError(
        "No se encontró columna de cluster. Columnas disponibles: "
        + ", ".join(df.columns)
    )


def find_metric_column(df: pd.DataFrame, candidates: list[str]) -> str | None:
    for col in candidates:
        if col in df.columns:
            return col
    return None


def safe_rate(value) -> float:
    try:
        if pd.isna(value):
            return 0.0
        return float(value)
    except Exception:
        return 0.0


def classify_level(value: float, q_low: float, q_high: float) -> str:
    if value >= q_high:
        return "Alta"
    if value >= q_low:
        return "Media"
    return "Baja"


def make_cluster_name(
    cluster_id: int,
    firms_level: str,
    conafor_level: str,
    smn_level: str,
) -> str:
    if firms_level == "Alta" and conafor_level == "Alta":
        return "Alta actividad térmica con mayor asociación a incendios registrados"

    if firms_level == "Alta" and conafor_level != "Alta":
        return "Alta actividad térmica con baja confirmación histórica"

    if firms_level == "Media" and conafor_level == "Alta":
        return "Actividad térmica media con incendios registrados relevantes"

    if firms_level == "Media":
        return "Actividad térmica intermedia"

    if firms_level == "Baja" and smn_level == "Alta":
        return "Baja actividad térmica con alta cobertura meteorológica"

    return "Baja actividad térmica"


def make_short_description(
    cluster_id: int,
    has_firms_rate: float,
    has_conafor_rate: float,
    has_smn_rate: float,
    firms_level: str,
    conafor_level: str,
    smn_level: str,
) -> str:
    return (
        f"Cluster {cluster_id} con actividad FIRMS {firms_level.lower()}, "
        f"presencia CONAFOR {conafor_level.lower()} y cobertura SMN "
        f"{smn_level.lower()} "
        f"(FIRMS={has_firms_rate:.4f}, CONAFOR={has_conafor_rate:.4f}, "
        f"SMN={has_smn_rate:.4f})."
    )


def make_technical_interpretation(
    cluster_id: int,
    firms_level: str,
    conafor_level: str,
    smn_level: str,
) -> str:
    return (
        f"El cluster {cluster_id} agrupa observaciones municipio-día con "
        f"nivel {firms_level.lower()} de detección satelital, "
        f"nivel {conafor_level.lower()} de coincidencia con registros históricos "
        f"de incendios y nivel {smn_level.lower()} de disponibilidad meteorológica. "
        f"Debe interpretarse como un patrón multivariable generado por PCA + SOM + KMeans, "
        f"no como una predicción directa de incendio."
    )


def make_app_usage(firms_level: str, conafor_level: str) -> str:
    if firms_level == "Alta" or conafor_level == "Alta":
        return "Priorizar en mapas, filtros y panel de detalle."
    if firms_level == "Media":
        return "Mostrar como patrón intermedio para comparación espacial y temporal."
    return "Usar como contexto base o zona de baja actividad relativa."


def choose_color_order(firms_level: str, conafor_level: str) -> tuple[str, int]:
    if firms_level == "Alta" and conafor_level == "Alta":
        return "#B91C1C", 1
    if firms_level == "Alta":
        return "#EA580C", 2
    if firms_level == "Media":
        return "#D97706", 3
    return "#2563EB", 4


def get_top_value(
    df: pd.DataFrame,
    cluster_col: str,
    cluster_id: int,
    value_candidates: list[str],
    label_candidates: list[str],
) -> str:
    if df.empty:
        return ""

    value_col = find_metric_column(df, value_candidates)
    label_col = find_metric_column(df, label_candidates)

    if value_col is None or label_col is None:
        return ""

    tmp = df[df[cluster_col] == cluster_id].copy()
    if tmp.empty:
        return ""

    tmp[value_col] = pd.to_numeric(tmp[value_col], errors="coerce")
    tmp = tmp.sort_values(value_col, ascending=False)

    if tmp.empty:
        return ""

    return str(tmp.iloc[0][label_col])


# ============================================================
# Proceso principal
# ============================================================

def main():
    print("\nEvaluation 01 | Catálogo interpretable de clusters")
    print("Flujo: municipio_dia")
    print("\nLeyendo archivos de Modeling...")

    cluster_profile = normalize_columns(read_csv_required(INPUT_CLUSTER_PROFILE))
    feature_profile = normalize_columns(read_csv_required(INPUT_FEATURE_PROFILE))
    entity_distribution = normalize_columns(read_csv_required(INPUT_ENTITY_DISTRIBUTION))
    month_distribution = normalize_columns(read_csv_required(INPUT_MONTH_DISTRIBUTION))
    decision_json = read_json_optional(INPUT_DECISION_JSON)

    cluster_col = find_cluster_column(cluster_profile)

    for df_name, df in [
        ("feature_profile", feature_profile),
        ("entity_distribution", entity_distribution),
        ("month_distribution", month_distribution),
    ]:
        try:
            _ = find_cluster_column(df)
        except ValueError:
            print(f"Advertencia: {df_name} no tiene columna clara de cluster.")

    feature_cluster_col = find_cluster_column(feature_profile)
    entity_cluster_col = find_cluster_column(entity_distribution)
    month_cluster_col = find_cluster_column(month_distribution)

    cluster_profile[cluster_col] = pd.to_numeric(cluster_profile[cluster_col], errors="coerce")
    cluster_profile = cluster_profile.dropna(subset=[cluster_col]).copy()
    cluster_profile[cluster_col] = cluster_profile[cluster_col].astype(int)

    clusters = sorted(cluster_profile[cluster_col].unique().tolist())

    print(f"Clusters detectados: {len(clusters)}")
    print(f"IDs: {clusters}")

    has_firms_col = find_metric_column(
        cluster_profile,
        ["has_firms_rate", "firms_rate", "rate_has_firms", "mean_has_firms"],
    )
    has_conafor_col = find_metric_column(
        cluster_profile,
        ["has_conafor_rate", "conafor_rate", "rate_has_conafor", "mean_has_conafor"],
    )
    has_smn_col = find_metric_column(
        cluster_profile,
        ["has_smn_rate", "smn_rate", "rate_has_smn", "mean_has_smn"],
    )

    if has_firms_col is None:
        raise ValueError("No se encontró métrica has_firms_rate o equivalente en cluster_profile.")

    if has_conafor_col is None:
        raise ValueError("No se encontró métrica has_conafor_rate o equivalente en cluster_profile.")

    if has_smn_col is None:
        raise ValueError("No se encontró métrica has_smn_rate o equivalente en cluster_profile.")

    firms_values = pd.to_numeric(cluster_profile[has_firms_col], errors="coerce").fillna(0)
    conafor_values = pd.to_numeric(cluster_profile[has_conafor_col], errors="coerce").fillna(0)
    smn_values = pd.to_numeric(cluster_profile[has_smn_col], errors="coerce").fillna(0)

    firms_q_low = firms_values.quantile(0.33)
    firms_q_high = firms_values.quantile(0.66)

    conafor_q_low = conafor_values.quantile(0.33)
    conafor_q_high = conafor_values.quantile(0.66)

    smn_q_low = smn_values.quantile(0.33)
    smn_q_high = smn_values.quantile(0.66)

    catalog_rows = []

    for cluster_id in clusters:
        row = cluster_profile[cluster_profile[cluster_col] == cluster_id].iloc[0]

        has_firms_rate = safe_rate(row.get(has_firms_col))
        has_conafor_rate = safe_rate(row.get(has_conafor_col))
        has_smn_rate = safe_rate(row.get(has_smn_col))

        firms_level = classify_level(has_firms_rate, firms_q_low, firms_q_high)
        conafor_level = classify_level(has_conafor_rate, conafor_q_low, conafor_q_high)
        smn_level = classify_level(has_smn_rate, smn_q_low, smn_q_high)

        cluster_name = make_cluster_name(
            cluster_id=cluster_id,
            firms_level=firms_level,
            conafor_level=conafor_level,
            smn_level=smn_level,
        )

        descripcion_corta = make_short_description(
            cluster_id=cluster_id,
            has_firms_rate=has_firms_rate,
            has_conafor_rate=has_conafor_rate,
            has_smn_rate=has_smn_rate,
            firms_level=firms_level,
            conafor_level=conafor_level,
            smn_level=smn_level,
        )

        interpretacion_tecnica = make_technical_interpretation(
            cluster_id=cluster_id,
            firms_level=firms_level,
            conafor_level=conafor_level,
            smn_level=smn_level,
        )

        perfil_espacial = get_top_value(
            entity_distribution,
            entity_cluster_col,
            cluster_id,
            value_candidates=[
                "pct_cluster",
                "porcentaje",
                "share",
                "proporcion",
                "n_observaciones",
                "count",
            ],
            label_candidates=[
                "entidad",
                "estado",
                "nombre_entidad",
                "cve_ent",
            ],
        )

        perfil_temporal = get_top_value(
            month_distribution,
            month_cluster_col,
            cluster_id,
            value_candidates=[
                "pct_cluster",
                "porcentaje",
                "share",
                "proporcion",
                "n_observaciones",
                "count",
            ],
            label_candidates=[
                "mes",
                "month",
                "mes_num",
                "periodo",
            ],
        )

        color, orden = choose_color_order(firms_level, conafor_level)

        catalog_rows.append({
            "cluster_id": cluster_id,
            "cluster_label": f"Cluster {cluster_id}",
            "cluster_name": cluster_name,
            "descripcion_corta": descripcion_corta,
            "interpretacion_tecnica": interpretacion_tecnica,
            "nivel_actividad_firms": firms_level,
            "nivel_confirmacion_conafor": conafor_level,
            "nivel_cobertura_smn": smn_level,
            "has_firms_rate": round(has_firms_rate, 6),
            "has_conafor_rate": round(has_conafor_rate, 6),
            "has_smn_rate": round(has_smn_rate, 6),
            "perfil_temporal": perfil_temporal,
            "perfil_espacial": perfil_espacial,
            "uso_en_app": make_app_usage(firms_level, conafor_level),
            "color_sugerido": color,
            "orden_visualizacion": orden,
            "flujo_modelo": "municipio_dia",
            "modelo_final": "PCA + SOM + KMeans",
            "nota_interpretacion": (
                "Cluster interpretativo no supervisado; no representa predicción "
                "ni confirmación individual de incendio."
            ),
        })

    catalog = pd.DataFrame(catalog_rows)
    catalog = catalog.sort_values(
        by=[
            "orden_visualizacion",
            "has_firms_rate",
            "has_conafor_rate",
            "cluster_id",
        ],
        ascending=[True, False, False, True],
    )

    print("\nGenerando catálogo de clusters...")
    catalog.to_csv(OUTPUT_CLUSTER_CATALOG, index=False, encoding="utf-8-sig")

    diagnostico_rows = []

    def add_check(nombre, estado, detalle):
        diagnostico_rows.append({
            "validacion": nombre,
            "estado": estado,
            "detalle": detalle,
        })

    add_check(
        "existe_cluster_profile",
        "OK" if INPUT_CLUSTER_PROFILE.exists() else "ERROR",
        str(INPUT_CLUSTER_PROFILE),
    )
    add_check(
        "existe_feature_profile",
        "OK" if INPUT_FEATURE_PROFILE.exists() else "ERROR",
        str(INPUT_FEATURE_PROFILE),
    )
    add_check(
        "existe_entity_distribution",
        "OK" if INPUT_ENTITY_DISTRIBUTION.exists() else "ERROR",
        str(INPUT_ENTITY_DISTRIBUTION),
    )
    add_check(
        "existe_month_distribution",
        "OK" if INPUT_MONTH_DISTRIBUTION.exists() else "ERROR",
        str(INPUT_MONTH_DISTRIBUTION),
    )
    add_check(
        "existe_decision_modelo",
        "OK" if INPUT_DECISION_JSON.exists() else "WARNING",
        str(INPUT_DECISION_JSON),
    )
    add_check(
        "clusters_detectados",
        "OK" if len(clusters) == 11 else "WARNING",
        f"Clusters detectados: {len(clusters)}; esperados: 11",
    )
    add_check(
        "catalogo_generado",
        "OK" if OUTPUT_CLUSTER_CATALOG.exists() else "ERROR",
        str(OUTPUT_CLUSTER_CATALOG),
    )
    add_check(
        "catalogo_sin_cluster_nulo",
        "OK" if catalog["cluster_id"].notna().all() else "ERROR",
        "cluster_id sin nulos",
    )
    add_check(
        "catalogo_sin_nombre_nulo",
        "OK" if catalog["cluster_name"].notna().all() else "ERROR",
        "cluster_name sin nulos",
    )

    diagnostico = pd.DataFrame(diagnostico_rows)
    diagnostico.to_csv(OUTPUT_DIAGNOSTICO, index=False, encoding="utf-8-sig")

    resumen = {
        "fase_crisp_dm": "Evaluation",
        "flujo_principal": "municipio_dia",
        "modelo_final": "PCA + SOM + KMeans",
        "objetivo": "Generar catálogo interpretable de clusters para app web",
        "clusters_detectados": int(len(clusters)),
        "clusters_esperados": 11,
        "archivo_catalogo": str(OUTPUT_CLUSTER_CATALOG),
        "archivo_diagnostico": str(OUTPUT_DIAGNOSTICO),
        "archivo_decision_modeling": str(INPUT_DECISION_JSON),
        "decision_modeling_disponible": bool(INPUT_DECISION_JSON.exists()),
        "modelo_decision_json": decision_json,
        "validaciones_ok": int((diagnostico["estado"] == "OK").sum()),
        "warnings": int((diagnostico["estado"] == "WARNING").sum()),
        "errores": int((diagnostico["estado"] == "ERROR").sum()),
    }

    with open(OUTPUT_RESUMEN_JSON, "w", encoding="utf-8") as f:
        json.dump(resumen, f, ensure_ascii=False, indent=2)

    print("\nArchivos generados:")
    print(f"- {OUTPUT_CLUSTER_CATALOG}")
    print(f"- {OUTPUT_DIAGNOSTICO}")
    print(f"- {OUTPUT_RESUMEN_JSON}")

    print("\nResumen:")
    print(f"- Clusters detectados: {len(clusters)}")
    print(f"- Validaciones OK: {(diagnostico['estado'] == 'OK').sum()}")
    print(f"- Warnings: {(diagnostico['estado'] == 'WARNING').sum()}")
    print(f"- Errores: {(diagnostico['estado'] == 'ERROR').sum()}")

    if (diagnostico["estado"] == "ERROR").any():
        print("\nProceso terminado con errores. Revisa el archivo de diagnóstico.")
    else:
        print("\nProceso terminado correctamente.")


if __name__ == "__main__":
    main()