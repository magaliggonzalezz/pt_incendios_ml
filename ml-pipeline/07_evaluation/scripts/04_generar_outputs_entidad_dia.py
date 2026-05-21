# -*- coding: utf-8 -*-
"""
Evaluation 04 | Outputs app entidad-día

Este script:
- Lee salidas cerradas de Modeling para entidad-día.
- Genera catálogo interpretable de clusters.
- Genera dataset app_entidad_dia.csv.
- Genera sample ligero.
- Genera resúmenes por cluster, mes, entidad y entidad-cluster.
- Guarda todo separado en datasets/entidad_dia y reports/entidad_dia.
"""

from pathlib import Path
import json
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]

MODELING_DIR = PROJECT_ROOT / "06_modeling"
EVALUATION_DIR = PROJECT_ROOT / "07_evaluation"

FLOW = "entidad_dia"

MODELING_DATASETS_DIR = MODELING_DIR / "datasets" / FLOW
MODELING_RESULTS_DIR = MODELING_DIR / "results" / FLOW / "som_kmeans"
MODELING_REPORTS_DIR = MODELING_DIR / "reports"

EVAL_DATASETS_DIR = EVALUATION_DIR / "datasets" / FLOW
EVAL_REPORTS_DIR = EVALUATION_DIR / "reports" / FLOW

EVAL_DATASETS_DIR.mkdir(parents=True, exist_ok=True)
EVAL_REPORTS_DIR.mkdir(parents=True, exist_ok=True)

INPUT_BASE = MODELING_DATASETS_DIR / "modeling_entidad_dia_base.csv"
INPUT_IDS = MODELING_DATASETS_DIR / "modeling_entidad_dia_ids.csv"
INPUT_CLUSTERS = MODELING_RESULTS_DIR / "som_kmeans_observation_clusters.csv"
INPUT_CLUSTER_PROFILE = MODELING_RESULTS_DIR / "som_kmeans_cluster_profile.csv"
INPUT_DECISION_JSON = MODELING_REPORTS_DIR / "modeling_10_decision_modelo_candidato_entidad_dia.json"

OUTPUT_CATALOG = EVAL_DATASETS_DIR / "app_cluster_catalog.csv"
OUTPUT_DATASET = EVAL_DATASETS_DIR / "app_entidad_dia.csv"
OUTPUT_SAMPLE = EVAL_DATASETS_DIR / "app_entidad_dia_sample.csv"

OUTPUT_RESUMEN_CLUSTER = EVAL_DATASETS_DIR / "app_resumen_cluster.csv"
OUTPUT_RESUMEN_MES = EVAL_DATASETS_DIR / "app_resumen_mes.csv"
OUTPUT_RESUMEN_ENTIDAD = EVAL_DATASETS_DIR / "app_resumen_entidad.csv"
OUTPUT_RESUMEN_ENTIDAD_CLUSTER = EVAL_DATASETS_DIR / "app_resumen_entidad_cluster.csv"

OUTPUT_DIAGNOSTICO = EVAL_REPORTS_DIR / "evaluation_04_diagnostico_outputs_entidad_dia.csv"
OUTPUT_RESUMEN_JSON = EVAL_REPORTS_DIR / "evaluation_04_resumen_outputs_entidad_dia.json"

CHUNKSIZE = 500_000
SAMPLE_MAX_ROWS = 20_000
RANDOM_STATE = 42


def norm_cols(cols):
    return (
        pd.Series(cols)
        .str.strip()
        .str.lower()
        .str.replace(" ", "_", regex=False)
        .tolist()
    )


def normalize(df):
    df = df.copy()
    df.columns = norm_cols(df.columns.tolist())
    return df


def read_header(path):
    if not path.exists():
        raise FileNotFoundError(f"No existe archivo requerido: {path}")
    return pd.read_csv(path, nrows=0, encoding="utf-8-sig").columns.tolist()


def find_cluster_col(cols):
    for c in ["cluster_id", "cluster_kmeans", "kmeans_cluster", "som_kmeans_cluster", "cluster"]:
        if c in cols:
            return c
    possible = [c for c in cols if "cluster" in c]
    if possible:
        return possible[0]
    raise ValueError(f"No se encontró columna de cluster. Columnas: {cols}")


def find_col(cols, candidates):
    for c in candidates:
        if c in cols:
            return c
    return None


def select_existing(cols, candidates):
    return [c for c in candidates if c in cols]


def add_validation(rows, name, status, detail):
    rows.append({"validacion": name, "estado": status, "detalle": detail})


def classify_level(value, q_low, q_high):
    if value >= q_high:
        return "Alta"
    if value >= q_low:
        return "Media"
    return "Baja"


def make_cluster_name(firms_level, conafor_level, smn_level):
    if firms_level == "Alta" and conafor_level == "Alta":
        return "Alta actividad térmica con mayor asociación a incendios registrados"
    if firms_level == "Alta":
        return "Alta actividad térmica con baja confirmación histórica"
    if firms_level == "Media" and conafor_level == "Alta":
        return "Actividad térmica media con incendios registrados relevantes"
    if firms_level == "Media":
        return "Actividad térmica intermedia"
    if smn_level == "Alta":
        return "Baja actividad térmica con alta cobertura meteorológica"
    return "Baja actividad térmica"


def color_order(firms_level, conafor_level):
    if firms_level == "Alta" and conafor_level == "Alta":
        return "#B91C1C", 1
    if firms_level == "Alta":
        return "#EA580C", 2
    if firms_level == "Media":
        return "#D97706", 3
    return "#2563EB", 4


def safe_num(s):
    return pd.to_numeric(s, errors="coerce")


def generate_catalog(validations):
    print("\nGenerando catálogo entidad-día...")

    profile = normalize(pd.read_csv(INPUT_CLUSTER_PROFILE, encoding="utf-8-sig"))
    cluster_col = find_cluster_col(profile.columns.tolist())

    profile[cluster_col] = safe_num(profile[cluster_col])
    profile = profile.dropna(subset=[cluster_col]).copy()
    profile[cluster_col] = profile[cluster_col].astype(int)

    firms_col = find_col(profile.columns.tolist(), ["has_firms_rate", "firms_rate", "mean_has_firms"])
    conafor_col = find_col(profile.columns.tolist(), ["has_conafor_rate", "conafor_rate", "mean_has_conafor"])
    smn_col = find_col(profile.columns.tolist(), ["has_smn_rate", "smn_rate", "mean_has_smn"])

    if firms_col is None or conafor_col is None or smn_col is None:
        raise ValueError("Faltan métricas has_firms_rate / has_conafor_rate / has_smn_rate en cluster_profile.")

    firms = safe_num(profile[firms_col]).fillna(0)
    conafor = safe_num(profile[conafor_col]).fillna(0)
    smn = safe_num(profile[smn_col]).fillna(0)

    fq1, fq2 = firms.quantile(0.33), firms.quantile(0.66)
    cq1, cq2 = conafor.quantile(0.33), conafor.quantile(0.66)
    sq1, sq2 = smn.quantile(0.33), smn.quantile(0.66)

    rows = []

    for _, r in profile.iterrows():
        cid = int(r[cluster_col])
        f_rate = float(r[firms_col]) if pd.notna(r[firms_col]) else 0
        c_rate = float(r[conafor_col]) if pd.notna(r[conafor_col]) else 0
        s_rate = float(r[smn_col]) if pd.notna(r[smn_col]) else 0

        f_level = classify_level(f_rate, fq1, fq2)
        c_level = classify_level(c_rate, cq1, cq2)
        s_level = classify_level(s_rate, sq1, sq2)

        color, order = color_order(f_level, c_level)
        name = make_cluster_name(f_level, c_level, s_level)

        rows.append({
            "cluster_id": cid,
            "cluster_label": f"Cluster {cid}",
            "cluster_name": name,
            "descripcion_corta": (
                f"Cluster {cid} entidad-día con actividad FIRMS {f_level.lower()}, "
                f"presencia CONAFOR {c_level.lower()} y cobertura SMN {s_level.lower()} "
                f"(FIRMS={f_rate:.4f}, CONAFOR={c_rate:.4f}, SMN={s_rate:.4f})."
            ),
            "interpretacion_tecnica": (
                f"Patrón estatal diario generado mediante PCA + SOM + KMeans. "
                f"No representa predicción directa ni confirmación individual de incendio."
            ),
            "nivel_actividad_firms": f_level,
            "nivel_confirmacion_conafor": c_level,
            "nivel_cobertura_smn": s_level,
            "has_firms_rate": round(f_rate, 6),
            "has_conafor_rate": round(c_rate, 6),
            "has_smn_rate": round(s_rate, 6),
            "color_sugerido": color,
            "orden_visualizacion": order,
            "flujo_modelo": FLOW,
            "modelo_final": "PCA + SOM + KMeans",
        })

    catalog = pd.DataFrame(rows).sort_values(
        ["orden_visualizacion", "has_firms_rate", "has_conafor_rate", "cluster_id"],
        ascending=[True, False, False, True],
    )

    catalog.to_csv(OUTPUT_CATALOG, index=False, encoding="utf-8-sig")

    add_validation(validations, "catalogo_entidad_dia_generado", "OK", str(OUTPUT_CATALOG))
    add_validation(
        validations,
        "clusters_catalogo_entidad_dia",
        "OK" if catalog["cluster_id"].nunique() == 9 else "WARNING",
        f"Clusters detectados: {catalog['cluster_id'].nunique()}; esperado entidad-día: 9",
    )

    return catalog


def generate_dataset(validations):
    print("\nGenerando dataset app_entidad_dia por chunks...")

    base_original = read_header(INPUT_BASE)
    ids_original = read_header(INPUT_IDS)
    clusters_original = read_header(INPUT_CLUSTERS)

    base_cols = norm_cols(base_original)
    ids_cols = norm_cols(ids_original)
    clusters_cols = norm_cols(clusters_original)

    base_rename = dict(zip(base_original, base_cols))
    ids_rename = dict(zip(ids_original, ids_cols))
    clusters_rename = dict(zip(clusters_original, clusters_cols))

    ids_candidates = [
        "fecha", "anio", "año", "mes", "dia",
        "entidad", "estado", "cve_ent",
        "latitud_centroide", "longitud_centroide",
        "lat_centroide", "lon_centroide",
    ]

    base_candidates = [
        "has_firms", "has_conafor", "has_smn",
        "firms_count", "conafor_count", "smn_count",
        "frp_sum", "frp_mean",
        "brightness_mean", "bright_t31_mean",
        "tmin_c_mean", "tmax_c_mean",
        "precip_mm_sum", "precip_mm_mean",
        "evap_mm_sum", "evap_mm_mean",
        "total_hectareas_sum", "total_hectáreas_sum",
        "hectareas_total", "hectáreas_total",
    ]

    selected_ids = select_existing(ids_cols, ids_candidates)
    selected_base = select_existing(base_cols, base_candidates)
    cluster_col = find_cluster_col(clusters_cols)

    ids_usecols = [o for o, n in ids_rename.items() if n in selected_ids]
    base_usecols = [o for o, n in base_rename.items() if n in selected_base]
    cluster_usecols = [o for o, n in clusters_rename.items() if n == cluster_col]

    print(f"- IDs: {len(selected_ids)} {selected_ids}")
    print(f"- Base: {len(selected_base)} {selected_base}")
    print(f"- Cluster: {cluster_col}")

    catalog = normalize(pd.read_csv(OUTPUT_CATALOG, encoding="utf-8-sig"))
    catalog["cluster_id"] = safe_num(catalog["cluster_id"]).astype(int)

    catalog_cols = [
        c for c in [
            "cluster_id", "cluster_label", "cluster_name", "descripcion_corta",
            "nivel_actividad_firms", "nivel_confirmacion_conafor",
            "nivel_cobertura_smn", "color_sugerido", "orden_visualizacion",
        ]
        if c in catalog.columns
    ]
    catalog = catalog[catalog_cols]

    if OUTPUT_DATASET.exists():
        OUTPUT_DATASET.unlink()

    ids_iter = pd.read_csv(INPUT_IDS, usecols=ids_usecols, chunksize=CHUNKSIZE, encoding="utf-8-sig", low_memory=False)
    base_iter = pd.read_csv(INPUT_BASE, usecols=base_usecols, chunksize=CHUNKSIZE, encoding="utf-8-sig", low_memory=False)
    cluster_iter = pd.read_csv(INPUT_CLUSTERS, usecols=cluster_usecols, chunksize=CHUNKSIZE, encoding="utf-8-sig", low_memory=False)

    total_rows = 0
    cluster_counts = {}
    sample_parts = []
    first = True
    chunk_id = 0

    for ids_chunk, base_chunk, cluster_chunk in zip(ids_iter, base_iter, cluster_iter):
        chunk_id += 1

        ids_chunk = normalize(ids_chunk)
        base_chunk = normalize(base_chunk)
        cluster_chunk = normalize(cluster_chunk)

        df = pd.concat(
            [ids_chunk.reset_index(drop=True), base_chunk.reset_index(drop=True), cluster_chunk.reset_index(drop=True)],
            axis=1,
        )

        if cluster_col != "cluster_id":
            df = df.rename(columns={cluster_col: "cluster_id"})

        df = df.rename(columns={
            "año": "anio",
            "estado": "entidad",
            "lat_centroide": "latitud_centroide",
            "lon_centroide": "longitud_centroide",
            "total_hectáreas_sum": "total_hectareas_sum",
            "hectáreas_total": "total_hectareas_sum",
            "hectareas_total": "total_hectareas_sum",
        })

        df["cluster_id"] = safe_num(df["cluster_id"]).astype(int)
        df.insert(0, "id_observacion", range(total_rows + 1, total_rows + len(df) + 1))

        if "fecha" in df.columns:
            fecha = pd.to_datetime(df["fecha"], errors="coerce")
            if "anio" not in df.columns:
                df["anio"] = fecha.dt.year
            if "mes" not in df.columns:
                df["mes"] = fecha.dt.month

        for flag in ["has_firms", "has_conafor", "has_smn"]:
            if flag in df.columns:
                df[flag] = safe_num(df[flag]).fillna(0).astype("int8")

        df = df.merge(catalog, on="cluster_id", how="left")
        df["flujo_modelo"] = FLOW
        df["modelo_final"] = "PCA + SOM + KMeans"

        order = [
            "id_observacion", "fecha", "anio", "mes",
            "cve_ent", "entidad",
            "latitud_centroide", "longitud_centroide",
            "cluster_id", "cluster_label", "cluster_name", "descripcion_corta",
            "nivel_actividad_firms", "nivel_confirmacion_conafor", "nivel_cobertura_smn",
            "has_firms", "has_conafor", "has_smn",
            "firms_count", "conafor_count", "smn_count",
            "frp_sum", "frp_mean", "brightness_mean", "bright_t31_mean",
            "tmin_c_mean", "tmax_c_mean", "precip_mm_sum", "precip_mm_mean",
            "evap_mm_sum", "evap_mm_mean", "total_hectareas_sum",
            "color_sugerido", "orden_visualizacion",
            "flujo_modelo", "modelo_final",
        ]

        cols = [c for c in order if c in df.columns] + [c for c in df.columns if c not in order]
        df = df[cols]

        df.to_csv(OUTPUT_DATASET, mode="w" if first else "a", header=first, index=False, encoding="utf-8-sig")
        first = False

        for k, v in df["cluster_id"].value_counts().to_dict().items():
            cluster_counts[int(k)] = cluster_counts.get(int(k), 0) + int(v)

        frac = min(1.0, SAMPLE_MAX_ROWS / max(1, 292_500))
        sample_parts.append(df.sample(frac=frac, random_state=RANDOM_STATE + chunk_id))

        total_rows += len(df)
        print(f"  Chunk {chunk_id} procesado | filas acumuladas: {total_rows:,}")

    sample = pd.concat(sample_parts, ignore_index=True) if sample_parts else pd.DataFrame()

    if len(sample) > SAMPLE_MAX_ROWS:
        sample = sample.sample(SAMPLE_MAX_ROWS, random_state=RANDOM_STATE)

    sample.to_csv(OUTPUT_SAMPLE, index=False, encoding="utf-8-sig")

    add_validation(validations, "dataset_entidad_dia_generado", "OK", str(OUTPUT_DATASET))
    add_validation(validations, "sample_entidad_dia_generado", "OK", str(OUTPUT_SAMPLE))
    add_validation(validations, "filas_dataset_entidad_dia", "OK" if total_rows > 0 else "ERROR", str(total_rows))
    add_validation(
        validations,
        "clusters_dataset_entidad_dia",
        "OK" if len(cluster_counts) == 9 else "WARNING",
        f"{sorted(cluster_counts.keys())}",
    )

    return total_rows, cluster_counts


def aggregate(input_path, group_cols, output_path, name, validations):
    print(f"\nGenerando {name}...")

    partials = []
    chunk_id = 0

    for chunk in pd.read_csv(input_path, chunksize=CHUNKSIZE, encoding="utf-8-sig", low_memory=False):
        chunk_id += 1
        chunk = normalize(chunk)

        for c in chunk.columns:
            if c not in ["fecha", "entidad", "cluster_label", "cluster_name", "descripcion_corta",
                         "nivel_actividad_firms", "nivel_confirmacion_conafor",
                         "nivel_cobertura_smn", "color_sugerido", "flujo_modelo", "modelo_final"]:
                chunk[c] = pd.to_numeric(chunk[c], errors="ignore")

        agg = {"id_observacion": "count"}

        for c in ["has_firms", "has_conafor", "has_smn", "firms_count", "conafor_count", "smn_count",
                  "frp_sum", "precip_mm_sum", "evap_mm_sum", "total_hectareas_sum"]:
            if c in chunk.columns:
                agg[c] = "sum"

        for c in ["frp_mean", "brightness_mean", "bright_t31_mean", "tmin_c_mean", "tmax_c_mean",
                  "precip_mm_mean", "evap_mm_mean"]:
            if c in chunk.columns:
                agg[c] = "mean"

        for c in ["cluster_label", "cluster_name", "nivel_actividad_firms", "nivel_confirmacion_conafor",
                  "nivel_cobertura_smn", "color_sugerido", "orden_visualizacion"]:
            if c in chunk.columns:
                agg[c] = "first"

        grouped = chunk.groupby(group_cols, dropna=False, as_index=False).agg(agg)
        partials.append(grouped)

        print(f"  Chunk {chunk_id} agregado")

    combined = pd.concat(partials, ignore_index=True)

    final_agg = {}
    for c in combined.columns:
        if c in group_cols:
            continue
        if c in ["cluster_label", "cluster_name", "nivel_actividad_firms", "nivel_confirmacion_conafor",
                 "nivel_cobertura_smn", "color_sugerido", "orden_visualizacion"]:
            final_agg[c] = "first"
        elif c in ["frp_mean", "brightness_mean", "bright_t31_mean", "tmin_c_mean", "tmax_c_mean",
                   "precip_mm_mean", "evap_mm_mean"]:
            final_agg[c] = "mean"
        else:
            final_agg[c] = "sum"

    final = combined.groupby(group_cols, dropna=False, as_index=False).agg(final_agg)

    final = final.rename(columns={
        "id_observacion": "n_observaciones",
        "has_firms": "dias_con_firms",
        "has_conafor": "dias_con_conafor",
        "has_smn": "dias_con_smn",
        "firms_count": "firms_total",
        "conafor_count": "conafor_total",
        "smn_count": "smn_total",
        "frp_sum": "frp_total",
        "frp_mean": "frp_promedio",
        "brightness_mean": "brightness_promedio",
        "bright_t31_mean": "bright_t31_promedio",
        "tmin_c_mean": "tmin_promedio",
        "tmax_c_mean": "tmax_promedio",
        "precip_mm_sum": "precip_total",
        "precip_mm_mean": "precip_promedio",
        "evap_mm_sum": "evap_total",
        "evap_mm_mean": "evap_promedio",
        "total_hectareas_sum": "hectareas_total",
    })

    final.to_csv(output_path, index=False, encoding="utf-8-sig")
    add_validation(validations, f"generado_{name}", "OK", f"{output_path} | filas={len(final)}")
    return len(final)


def main():
    print("\nEvaluation 04 | Outputs app entidad-día")

    validations = []

    for name, path in [
        ("base", INPUT_BASE),
        ("ids", INPUT_IDS),
        ("clusters", INPUT_CLUSTERS),
        ("cluster_profile", INPUT_CLUSTER_PROFILE),
    ]:
        add_validation(validations, f"existe_{name}", "OK" if path.exists() else "ERROR", str(path))
        if not path.exists():
            raise FileNotFoundError(path)

    catalog = generate_catalog(validations)
    total_rows, cluster_counts = generate_dataset(validations)

    cols = norm_cols(pd.read_csv(OUTPUT_DATASET, nrows=0, encoding="utf-8-sig").columns.tolist())

    aggregate(OUTPUT_DATASET, ["cluster_id"], OUTPUT_RESUMEN_CLUSTER, "app_resumen_cluster", validations)

    if "anio" in cols and "mes" in cols:
        aggregate(OUTPUT_DATASET, ["anio", "mes"], OUTPUT_RESUMEN_MES, "app_resumen_mes", validations)

    if "cve_ent" in cols:
        aggregate(OUTPUT_DATASET, ["cve_ent"], OUTPUT_RESUMEN_ENTIDAD, "app_resumen_entidad", validations)
        aggregate(OUTPUT_DATASET, ["cve_ent", "cluster_id"], OUTPUT_RESUMEN_ENTIDAD_CLUSTER, "app_resumen_entidad_cluster", validations)

    diagnostico = pd.DataFrame(validations)
    diagnostico.to_csv(OUTPUT_DIAGNOSTICO, index=False, encoding="utf-8-sig")

    decision = {}
    if INPUT_DECISION_JSON.exists():
        with open(INPUT_DECISION_JSON, "r", encoding="utf-8") as f:
            decision = json.load(f)

    resumen = {
        "fase_crisp_dm": "Evaluation",
        "flujo": FLOW,
        "modelo_final": "PCA + SOM + KMeans",
        "filas_generadas": int(total_rows),
        "clusters_detectados": sorted([int(k) for k in cluster_counts.keys()]),
        "conteo_por_cluster": {str(k): int(v) for k, v in sorted(cluster_counts.items())},
        "archivos": {
            "catalogo": str(OUTPUT_CATALOG),
            "dataset": str(OUTPUT_DATASET),
            "sample": str(OUTPUT_SAMPLE),
            "resumen_cluster": str(OUTPUT_RESUMEN_CLUSTER),
            "resumen_mes": str(OUTPUT_RESUMEN_MES),
            "resumen_entidad": str(OUTPUT_RESUMEN_ENTIDAD),
            "resumen_entidad_cluster": str(OUTPUT_RESUMEN_ENTIDAD_CLUSTER),
            "diagnostico": str(OUTPUT_DIAGNOSTICO),
        },
        "decision_modeling": decision,
        "validaciones_ok": int((diagnostico["estado"] == "OK").sum()),
        "warnings": int((diagnostico["estado"] == "WARNING").sum()),
        "errores": int((diagnostico["estado"] == "ERROR").sum()),
    }

    with open(OUTPUT_RESUMEN_JSON, "w", encoding="utf-8") as f:
        json.dump(resumen, f, ensure_ascii=False, indent=2)

    print("\nArchivos principales generados:")
    print(f"- {OUTPUT_CATALOG}")
    print(f"- {OUTPUT_DATASET}")
    print(f"- {OUTPUT_SAMPLE}")
    print(f"- {OUTPUT_RESUMEN_CLUSTER}")
    print(f"- {OUTPUT_RESUMEN_MES}")
    print(f"- {OUTPUT_RESUMEN_ENTIDAD}")
    print(f"- {OUTPUT_RESUMEN_ENTIDAD_CLUSTER}")
    print(f"- {OUTPUT_DIAGNOSTICO}")
    print(f"- {OUTPUT_RESUMEN_JSON}")

    print("\nResumen:")
    print(f"- Filas generadas: {total_rows:,}")
    print(f"- Clusters detectados: {sorted(cluster_counts.keys())}")
    print(f"- Validaciones OK: {(diagnostico['estado'] == 'OK').sum()}")
    print(f"- Warnings: {(diagnostico['estado'] == 'WARNING').sum()}")
    print(f"- Errores: {(diagnostico['estado'] == 'ERROR').sum()}")

    if (diagnostico["estado"] == "ERROR").any():
        print("\nProceso terminado con errores.")
    else:
        print("\nProceso terminado correctamente.")


if __name__ == "__main__":
    main()