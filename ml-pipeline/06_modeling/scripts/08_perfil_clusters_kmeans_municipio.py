# -*- coding: utf-8 -*-
"""
Modeling 08 | Perfilado de clusters KMeans municipio-día

Este script perfila los clusters KMeans del flujo municipio-día.

Hace lo siguiente:
- Lee el dataset base de Modeling municipio-día por chunks.
- Lee los clusters por observación generados por SOM + KMeans por chunks.
- Valida consistencia de filas y llaves.
- Calcula resumen por cluster.
- Calcula perfil de variables por cluster.
- Calcula distribución por entidad.
- Calcula distribución por mes.
- Genera archivos de perfilado en results y resumen en reports.
"""

from pathlib import Path
import numpy as np
import pandas as pd


# ============================================================
# CONFIGURACIÓN
# ============================================================

BASE_DIR = Path(r"C:\Users\Hp\OneDrive\Documentos\PT_Analisis")

FLUJO = "municipio_dia"

CHUNKSIZE = 300_000

INPUT_BASE = BASE_DIR / "06_modeling" / "datasets" / FLUJO / f"modeling_{FLUJO}_base.csv"
INPUT_CLUSTERS = BASE_DIR / "06_modeling" / "results" / FLUJO / "som_kmeans" / "som_kmeans_observation_clusters.csv"
INPUT_DIAG = BASE_DIR / "06_modeling" / "reports" / f"modeling_01_diagnostico_{FLUJO}.csv"

OUT_RESULTS = BASE_DIR / "06_modeling" / "results" / FLUJO / "som_kmeans"
OUT_REPORTS = BASE_DIR / "06_modeling" / "reports"

OUT_RESULTS.mkdir(parents=True, exist_ok=True)
OUT_REPORTS.mkdir(parents=True, exist_ok=True)

OUT_CLUSTER_PROFILE = OUT_RESULTS / "som_kmeans_cluster_profile.csv"
OUT_FEATURE_PROFILE = OUT_RESULTS / "som_kmeans_feature_profile.csv"
OUT_ENTITY_DISTRIBUTION = OUT_RESULTS / "som_kmeans_cluster_entity_distribution.csv"
OUT_MONTH_DISTRIBUTION = OUT_RESULTS / "som_kmeans_cluster_month_distribution.csv"
OUT_REPORT_SUMMARY = OUT_REPORTS / f"modeling_08_resumen_perfil_clusters_{FLUJO}.csv"


KEY_COLS = ["cvegeo", "fecha"]

ID_COLS = [
    "cvegeo",
    "cve_ent",
    "cve_mun",
    "nom_ent",
    "nom_mun",
    "fecha",
]

PRIORITY_PROFILE_COLS = [
    "has_conafor",
    "has_firms",
    "has_smn",
    "es_temporada_incendios",
    "conafor_event_count",
    "conafor_event_count_log1p",
    "firms_count",
    "firms_count_log1p",
    "firms_frp_sum",
    "firms_frp_sum_log1p",
    "firms_frp_mean",
    "firms_brightness_mean",
    "firms_bright_t31_mean",
    "firms_confidence_mean",
    "firms_day_count",
    "firms_night_count",
    "smn_precip_mm_mean",
    "smn_evap_mm_mean",
    "smn_tmin_c_mean",
    "smn_tmax_c_mean",
    "smn_temp_media_c",
    "smn_amplitud_termica_c",
    "municipio_area_km2",
]


# ============================================================
# FUNCIONES AUXILIARES
# ============================================================

def ensure_file(path: Path, label: str) -> None:
    if not path.exists():
        raise FileNotFoundError(f"No existe {label}: {path}")


def ensure_columns(df: pd.DataFrame, required_cols: list[str], context: str) -> None:
    missing = [c for c in required_cols if c not in df.columns]
    if missing:
        raise ValueError(f"Faltan columnas en {context}: {missing}")


def normalize_keys(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    if "cve_ent" in df.columns:
        df["cve_ent"] = (
            df["cve_ent"]
            .astype(str)
            .str.replace(r"\.0$", "", regex=True)
            .str.zfill(2)
        )

    if "cve_mun" in df.columns:
        df["cve_mun"] = (
            df["cve_mun"]
            .astype(str)
            .str.replace(r"\.0$", "", regex=True)
            .str.zfill(3)
        )

    if "cvegeo" in df.columns:
        df["cvegeo"] = (
            df["cvegeo"]
            .astype(str)
            .str.replace(r"\.0$", "", regex=True)
            .str.zfill(5)
        )

    if "fecha" in df.columns:
        df["fecha"] = pd.to_datetime(df["fecha"], errors="coerce").dt.strftime("%Y-%m-%d")

    return df


def get_candidate_and_profile_cols() -> tuple[list[str], list[str]]:
    diag = pd.read_csv(INPUT_DIAG, encoding="utf-8-sig")

    ensure_columns(diag, ["columna", "uso_sugerido"], "diagnóstico Modeling 01")

    candidate_cols = (
        diag.loc[diag["uso_sugerido"] == "candidata_modelado", "columna"]
        .dropna()
        .astype(str)
        .tolist()
    )

    profiling_cols = (
        diag.loc[diag["uso_sugerido"] == "perfilado", "columna"]
        .dropna()
        .astype(str)
        .tolist()
    )

    return candidate_cols, profiling_cols


def choose_profile_variables(base_header: list[str], candidate_cols: list[str], profiling_cols: list[str]) -> list[str]:
    selected = []

    for col in PRIORITY_PROFILE_COLS:
        if col in base_header:
            selected.append(col)

    # Agrega variables de perfilado explícitas si no están en prioridad.
    for col in profiling_cols:
        if col in base_header and col not in selected:
            selected.append(col)

    # Agrega algunas variables contextuales candidatas, sin meter todas las INFyS.
    for col in candidate_cols:
        c = col.lower()

        keep = (
            c.startswith("inegi_")
            or c == "municipio_area_km2"
            or c.endswith("_n_registros_20152020")
            or c.endswith("_superficieha_mean_20152020")
            or c.endswith("_superficieforestaltotalha_mean_20152020")
        )

        if keep and col in base_header and col not in selected:
            selected.append(col)

    return selected


def validate_key_alignment(base_chunk: pd.DataFrame, cluster_chunk: pd.DataFrame, chunk_id: int) -> None:
    base_keys = base_chunk[KEY_COLS].astype(str).reset_index(drop=True)
    cluster_keys = cluster_chunk[KEY_COLS].astype(str).reset_index(drop=True)

    mismatch = (base_keys != cluster_keys).any(axis=1)

    if mismatch.any():
        n = int(mismatch.sum())
        raise ValueError(f"Chunk {chunk_id}: {n:,} filas no coinciden entre base y clusters.")


def init_agg_dict():
    return {}


def update_numeric_aggregates(agg: dict, df: pd.DataFrame, cluster_col: str, variables: list[str]) -> dict:
    for col in variables:
        if col not in df.columns:
            continue

        df[col] = pd.to_numeric(df[col], errors="coerce")

        grouped = df.groupby(cluster_col)[col].agg(["count", "sum", "mean", "min", "max"])

        for cluster, row in grouped.iterrows():
            key = (int(cluster), col)

            if key not in agg:
                agg[key] = {
                    "cluster_kmeans": int(cluster),
                    "feature": col,
                    "count": 0,
                    "sum": 0.0,
                    "min": np.nan,
                    "max": np.nan,
                }

            agg[key]["count"] += int(row["count"])
            agg[key]["sum"] += float(row["sum"]) if pd.notna(row["sum"]) else 0.0

            if pd.notna(row["min"]):
                if pd.isna(agg[key]["min"]):
                    agg[key]["min"] = float(row["min"])
                else:
                    agg[key]["min"] = min(agg[key]["min"], float(row["min"]))

            if pd.notna(row["max"]):
                if pd.isna(agg[key]["max"]):
                    agg[key]["max"] = float(row["max"])
                else:
                    agg[key]["max"] = max(agg[key]["max"], float(row["max"]))

    return agg


def finalize_feature_profile(agg: dict) -> pd.DataFrame:
    rows = []

    for _, item in agg.items():
        count = item["count"]
        total_sum = item["sum"]

        mean = total_sum / count if count > 0 else np.nan

        rows.append({
            "cluster_kmeans": item["cluster_kmeans"],
            "feature": item["feature"],
            "count_non_null": count,
            "mean": mean,
            "min": item["min"],
            "max": item["max"],
        })

    out = pd.DataFrame(rows)

    if out.empty:
        return out

    global_means = (
        out.groupby("feature")
        .apply(lambda g: np.average(g["mean"], weights=g["count_non_null"]))
        .rename("global_weighted_mean")
        .reset_index()
    )

    out = out.merge(global_means, on="feature", how="left")

    out["difference_vs_global"] = out["mean"] - out["global_weighted_mean"]

    out["ratio_vs_global"] = np.where(
        out["global_weighted_mean"] != 0,
        out["mean"] / out["global_weighted_mean"],
        np.nan,
    )

    out = out.sort_values(["cluster_kmeans", "feature"]).reset_index(drop=True)

    return out


def update_cluster_counts(cluster_counts: dict, df: pd.DataFrame) -> dict:
    counts = df["cluster_kmeans"].value_counts(dropna=False)

    for cluster, n in counts.items():
        cluster = int(cluster)
        cluster_counts[cluster] = cluster_counts.get(cluster, 0) + int(n)

    return cluster_counts


def update_entity_distribution(entity_rows: list, df: pd.DataFrame) -> None:
    cols = ["cluster_kmeans", "cve_ent", "nom_ent"]

    grouped = (
        df.groupby(cols, dropna=False)
        .size()
        .reset_index(name="n_observaciones")
    )

    entity_rows.append(grouped)


def update_month_distribution(month_rows: list, df: pd.DataFrame) -> None:
    cols = ["cluster_kmeans", "mes"]

    grouped = (
        df.groupby(cols, dropna=False)
        .size()
        .reset_index(name="n_observaciones")
    )

    month_rows.append(grouped)


def build_distribution(rows: list, group_cols: list[str]) -> pd.DataFrame:
    if not rows:
        return pd.DataFrame(columns=group_cols + ["n_observaciones", "pct_dentro_cluster"])

    out = pd.concat(rows, ignore_index=True)

    out = (
        out.groupby(group_cols, dropna=False, as_index=False)
        .agg(n_observaciones=("n_observaciones", "sum"))
    )

    cluster_totals = (
        out.groupby("cluster_kmeans", as_index=False)
        .agg(total_cluster=("n_observaciones", "sum"))
    )

    out = out.merge(cluster_totals, on="cluster_kmeans", how="left")
    out["pct_dentro_cluster"] = out["n_observaciones"] / out["total_cluster"]

    out = out.sort_values(["cluster_kmeans", "n_observaciones"], ascending=[True, False])

    return out


def build_cluster_profile(cluster_counts: dict, feature_profile: pd.DataFrame) -> pd.DataFrame:
    rows = []

    total = sum(cluster_counts.values())

    for cluster, n in sorted(cluster_counts.items()):
        rows.append({
            "cluster_kmeans": cluster,
            "n_observaciones": n,
            "pct_observaciones": n / total if total > 0 else np.nan,
        })

    profile = pd.DataFrame(rows)

    key_features = [
        "has_conafor",
        "has_firms",
        "has_smn",
        "es_temporada_incendios",
        "conafor_event_count",
        "firms_count",
        "firms_frp_sum",
        "smn_precip_mm_mean",
        "smn_temp_media_c",
        "municipio_area_km2",
    ]

    if not feature_profile.empty:
        pivot = feature_profile[
            feature_profile["feature"].isin(key_features)
        ].pivot(
            index="cluster_kmeans",
            columns="feature",
            values="mean",
        ).reset_index()

        rename_map = {
            "has_conafor": "has_conafor_rate",
            "has_firms": "has_firms_rate",
            "has_smn": "has_smn_rate",
            "es_temporada_incendios": "temporada_incendios_rate",
        }

        pivot = pivot.rename(columns=rename_map)

        profile = profile.merge(pivot, on="cluster_kmeans", how="left")

    return profile.sort_values("cluster_kmeans").reset_index(drop=True)


# ============================================================
# PIPELINE PRINCIPAL
# ============================================================

def main():
    print("\nModeling 08 | Perfilado de clusters KMeans")
    print(f"Flujo: {FLUJO}")

    ensure_file(INPUT_BASE, "dataset base")
    ensure_file(INPUT_CLUSTERS, "clusters KMeans por observación")
    ensure_file(INPUT_DIAG, "diagnóstico Modeling 01")

    print("\nLeyendo encabezados...")

    base_header = pd.read_csv(INPUT_BASE, encoding="utf-8-sig", nrows=0)
    cluster_header = pd.read_csv(INPUT_CLUSTERS, encoding="utf-8-sig", nrows=0)

    ensure_columns(base_header, KEY_COLS + ID_COLS, "dataset base")
    ensure_columns(cluster_header, KEY_COLS + ["cluster_kmeans"], "clusters por observación")

    candidate_cols, profiling_cols = get_candidate_and_profile_cols()

    profile_variables = choose_profile_variables(
        base_header=list(base_header.columns),
        candidate_cols=candidate_cols,
        profiling_cols=profiling_cols,
    )

    usecols_base = list(dict.fromkeys(ID_COLS + ["mes"] + profile_variables))
    usecols_base = [c for c in usecols_base if c in base_header.columns]

    usecols_clusters = list(dict.fromkeys(KEY_COLS + ["cluster_kmeans"]))

    print(f"Variables usadas para perfilado: {len(profile_variables):,}")
    print(f"Columnas leídas de base: {len(usecols_base):,}")

    numeric_agg = init_agg_dict()
    cluster_counts = {}
    entity_rows = []
    month_rows = []

    total_rows = 0

    print("\nProcesando por chunks...")

    base_iter = pd.read_csv(
        INPUT_BASE,
        encoding="utf-8-sig",
        usecols=usecols_base,
        chunksize=CHUNKSIZE,
        low_memory=False,
    )

    cluster_iter = pd.read_csv(
        INPUT_CLUSTERS,
        encoding="utf-8-sig",
        usecols=usecols_clusters,
        chunksize=CHUNKSIZE,
        low_memory=False,
    )

    for i, (base_chunk, cluster_chunk) in enumerate(zip(base_iter, cluster_iter), start=1):
        if len(base_chunk) != len(cluster_chunk):
            raise ValueError(
                f"Chunk {i}: base y clusters tienen distinto tamaño: "
                f"{len(base_chunk):,} vs {len(cluster_chunk):,}"
            )

        base_chunk = normalize_keys(base_chunk)
        cluster_chunk = normalize_keys(cluster_chunk)

        validate_key_alignment(base_chunk, cluster_chunk, i)

        df = base_chunk.copy()
        df["cluster_kmeans"] = pd.to_numeric(
            cluster_chunk["cluster_kmeans"],
            errors="coerce",
        )

        if df["cluster_kmeans"].isna().any():
            n = int(df["cluster_kmeans"].isna().sum())
            raise ValueError(f"Chunk {i}: {n:,} filas sin cluster_kmeans.")

        df["cluster_kmeans"] = df["cluster_kmeans"].astype(int)

        numeric_agg = update_numeric_aggregates(
            agg=numeric_agg,
            df=df,
            cluster_col="cluster_kmeans",
            variables=profile_variables,
        )

        cluster_counts = update_cluster_counts(cluster_counts, df)

        update_entity_distribution(entity_rows, df)

        if "mes" in df.columns:
            df["mes"] = pd.to_numeric(df["mes"], errors="coerce").astype("Int64")
            update_month_distribution(month_rows, df)

        total_rows += len(df)

        print(f"- chunk {i:,}: filas acumuladas {total_rows:,}")

    feature_profile = finalize_feature_profile(numeric_agg)
    cluster_profile = build_cluster_profile(cluster_counts, feature_profile)
    entity_distribution = build_distribution(
        entity_rows,
        ["cluster_kmeans", "cve_ent", "nom_ent"],
    )
    month_distribution = build_distribution(
        month_rows,
        ["cluster_kmeans", "mes"],
    )

    cluster_profile.to_csv(OUT_CLUSTER_PROFILE, index=False, encoding="utf-8-sig")
    feature_profile.to_csv(OUT_FEATURE_PROFILE, index=False, encoding="utf-8-sig")
    entity_distribution.to_csv(OUT_ENTITY_DISTRIBUTION, index=False, encoding="utf-8-sig")
    month_distribution.to_csv(OUT_MONTH_DISTRIBUTION, index=False, encoding="utf-8-sig")

    summary_cols = [
        "cluster_kmeans",
        "n_observaciones",
        "pct_observaciones",
        "has_conafor_rate",
        "has_firms_rate",
        "has_smn_rate",
        "temporada_incendios_rate",
    ]

    summary_cols = [c for c in summary_cols if c in cluster_profile.columns]

    summary = cluster_profile[summary_cols].copy()
    summary.to_csv(OUT_REPORT_SUMMARY, index=False, encoding="utf-8-sig")

    print("\nArchivos generados:")
    print(f"- {OUT_CLUSTER_PROFILE}")
    print(f"- {OUT_FEATURE_PROFILE}")
    print(f"- {OUT_ENTITY_DISTRIBUTION}")
    print(f"- {OUT_MONTH_DISTRIBUTION}")
    print(f"- {OUT_REPORT_SUMMARY}")

    print("\nResumen de clusters:")
    print(summary.to_string(index=False))

    print(f"\nFilas perfiladas: {total_rows:,}")
    print(f"Clusters detectados: {cluster_profile['cluster_kmeans'].nunique():,}")
    print(f"Variables usadas para perfilado: {len(profile_variables):,}")

    print("\nProceso terminado.")


if __name__ == "__main__":
    main()