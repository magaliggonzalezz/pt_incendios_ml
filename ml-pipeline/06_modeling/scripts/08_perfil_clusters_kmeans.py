# -*- coding: utf-8 -*-
"""
Modeling 08 | Perfilado de clusters KMeans

Este script perfila los clusters generados por SOM + KMeans.

Hace lo siguiente:
- Lee el dataset base de Modeling.
- Lee las asignaciones de cluster por observación.
- Une ambos por posición/orden de filas.
- Calcula resumen por cluster.
- Usa CONAFOR como contraste/perfilado, no como predictor.
- Genera perfiles de FIRMS, SMN, temporalidad, INEGI e INFyS.
"""

from pathlib import Path
import pandas as pd
import numpy as np


# ============================================================
# CONFIGURACIÓN
# ============================================================

BASE_DIR = Path(r"C:\Users\Hp\OneDrive\Documentos\PT_Analisis")

FLUJO = "entidad_dia"

INPUT_BASE = BASE_DIR / "06_modeling" / "datasets" / FLUJO / f"modeling_{FLUJO}_base.csv"
INPUT_CLUSTERS = BASE_DIR / "06_modeling" / "results" / FLUJO / "som_kmeans" / "som_kmeans_observation_clusters.csv"
INPUT_DIAG = BASE_DIR / "06_modeling" / "reports" / f"modeling_01_diagnostico_{FLUJO}.csv"

OUT_RESULTS = BASE_DIR / "06_modeling" / "results" / FLUJO / "som_kmeans"
OUT_REPORTS = BASE_DIR / "06_modeling" / "reports"

OUT_PROFILE = OUT_RESULTS / "som_kmeans_cluster_profile.csv"
OUT_FEATURE_PROFILE = OUT_RESULTS / "som_kmeans_feature_profile.csv"
OUT_CLUSTER_ENTITY = OUT_RESULTS / "som_kmeans_cluster_entity_distribution.csv"
OUT_CLUSTER_MONTH = OUT_RESULTS / "som_kmeans_cluster_month_distribution.csv"
OUT_PROFILE_REPORT = OUT_REPORTS / f"modeling_08_resumen_perfil_clusters_{FLUJO}.csv"

OUT_RESULTS.mkdir(parents=True, exist_ok=True)
OUT_REPORTS.mkdir(parents=True, exist_ok=True)


# ============================================================
# COLUMNAS ID POR FLUJO
# ============================================================

ID_COLS_BY_FLOW = {
    "entidad_dia": [
        "cve_ent",
        "nom_ent",
        "fecha",
    ],
    "municipio_dia": [
        "cvegeo",
        "cve_ent",
        "cve_mun",
        "nom_ent",
        "nom_mun",
        "fecha",
    ],
}


# ============================================================
# VARIABLES PRINCIPALES PARA PERFILADO
# ============================================================

PREFERRED_PROFILE_COLS = [
    # Temporalidad
    "anio",
    "mes",
    "dia_del_anio",
    "semana_iso",
    "trimestre",
    "es_temporada_incendios",

    # CONAFOR como contraste
    "has_conafor",
    "conafor_event_count",
    "conafor_event_count_log1p",

    # FIRMS
    "has_firms",
    "firms_count",
    "firms_count_log1p",
    "firms_frp_sum",
    "firms_frp_sum_log1p",
    "firms_frp_mean",
    "firms_brightness_mean",
    "firms_confidence_mean",
    "firms_day_count",
    "firms_night_count",
    "firms_day_count_log1p",
    "firms_night_count_log1p",

    # SMN
    "has_smn",
    "smn_n_estaciones",
    "smn_precip_mm_mean",
    "smn_evap_mm_mean",
    "smn_tmin_c_mean",
    "smn_tmax_c_mean",
    "smn_temp_media_c",
    "smn_amplitud_termica_c",

    # INEGI principales
    "entidad_area_km2_sum",
    "inegi_hidrografia_longitud_total_km",
    "inegi_edafologia_area_total_km2",
    "inegi_fisiografia_area_total_km2",
    "inegi_uso_suelo_vegetacion_area_total_km2",

    # INFyS principales
    "infys_sup_c2015_2020_estatal_superficieforestaltotalha_mean_20152020",
    "infys_sup_c2015_2020_detalle_superficieha_mean_20152020",
    "infys_ind_estructura_mediaat_mean_20152020",
    "infys_ind_estructura_mediadn_mean_20152020",
    "infys_ind_estructura_maxat_mean_20152020",
    "infys_ind_estructura_maxdn_mean_20152020",
    "infys_ind_composicion_derivado_punto_totalespecies_mean_20152020",
    "infys_ind_dist_at_dn_alturatotal_mean_20152020",
    "infys_ind_dist_at_dn_diametronormal_mean_20152020",
]


# ============================================================
# FUNCIONES AUXILIARES
# ============================================================

def ensure_columns(df: pd.DataFrame, required_cols: list[str], context: str) -> None:
    missing = [c for c in required_cols if c not in df.columns]
    if missing:
        raise ValueError(f"Faltan columnas en {context}: {missing}")


def safe_numeric(df: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
    for col in cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


def get_available_profile_cols(df: pd.DataFrame) -> list[str]:
    return [c for c in PREFERRED_PROFILE_COLS if c in df.columns]


def build_cluster_profile(df: pd.DataFrame, profile_cols: list[str]) -> pd.DataFrame:
    rows = []

    total_rows = len(df)

    for cluster, g in df.groupby("cluster_kmeans"):
        row = {
            "cluster_kmeans": int(cluster),
            "n_observaciones": int(len(g)),
            "pct_observaciones": len(g) / total_rows,
            "n_entidades": int(g["cve_ent"].nunique()) if "cve_ent" in g.columns else np.nan,
            "fecha_min": g["fecha"].min() if "fecha" in g.columns else None,
            "fecha_max": g["fecha"].max() if "fecha" in g.columns else None,
        }

        if "has_conafor" in g.columns:
            row["has_conafor_rate"] = g["has_conafor"].mean()

        if "has_firms" in g.columns:
            row["has_firms_rate"] = g["has_firms"].mean()

        if "has_smn" in g.columns:
            row["has_smn_rate"] = g["has_smn"].mean()

        if "es_temporada_incendios" in g.columns:
            row["temporada_incendios_rate"] = g["es_temporada_incendios"].mean()

        for col in profile_cols:
            if col in {
                "has_conafor",
                "has_firms",
                "has_smn",
                "es_temporada_incendios",
            }:
                continue

            s = pd.to_numeric(g[col], errors="coerce")

            row[f"{col}_mean"] = s.mean()
            row[f"{col}_median"] = s.median()

        rows.append(row)

    return pd.DataFrame(rows).sort_values("cluster_kmeans")


def build_feature_profile(df: pd.DataFrame, profile_cols: list[str]) -> pd.DataFrame:
    rows = []

    global_stats = {}

    for col in profile_cols:
        s_global = pd.to_numeric(df[col], errors="coerce")
        global_stats[col] = {
            "global_mean": s_global.mean(),
            "global_median": s_global.median(),
            "global_std": s_global.std(),
        }

    for cluster, g in df.groupby("cluster_kmeans"):
        for col in profile_cols:
            s = pd.to_numeric(g[col], errors="coerce")
            gs = global_stats[col]

            cluster_mean = s.mean()
            cluster_median = s.median()

            std = gs["global_std"]
            z_mean = np.nan
            if pd.notna(std) and std != 0:
                z_mean = (cluster_mean - gs["global_mean"]) / std

            rows.append({
                "cluster_kmeans": int(cluster),
                "feature": col,
                "cluster_mean": cluster_mean,
                "cluster_median": cluster_median,
                "global_mean": gs["global_mean"],
                "global_median": gs["global_median"],
                "z_mean_vs_global": z_mean,
                "abs_z_mean_vs_global": abs(z_mean) if pd.notna(z_mean) else np.nan,
            })

    out = pd.DataFrame(rows)
    out = out.sort_values(
        by=["cluster_kmeans", "abs_z_mean_vs_global"],
        ascending=[True, False],
    )

    return out


def build_cluster_entity_distribution(df: pd.DataFrame) -> pd.DataFrame:
    if "nom_ent" not in df.columns:
        return pd.DataFrame()

    out = (
        df.groupby(["cluster_kmeans", "cve_ent", "nom_ent"], as_index=False)
        .size()
        .rename(columns={"size": "n_observaciones"})
    )

    total_cluster = (
        out.groupby("cluster_kmeans")["n_observaciones"]
        .transform("sum")
    )

    out["pct_dentro_cluster"] = out["n_observaciones"] / total_cluster

    return out.sort_values(
        by=["cluster_kmeans", "n_observaciones"],
        ascending=[True, False],
    )


def build_cluster_month_distribution(df: pd.DataFrame) -> pd.DataFrame:
    if "mes" not in df.columns:
        return pd.DataFrame()

    out = (
        df.groupby(["cluster_kmeans", "mes"], as_index=False)
        .size()
        .rename(columns={"size": "n_observaciones"})
    )

    total_cluster = (
        out.groupby("cluster_kmeans")["n_observaciones"]
        .transform("sum")
    )

    out["pct_dentro_cluster"] = out["n_observaciones"] / total_cluster

    return out.sort_values(["cluster_kmeans", "mes"])


def build_profile_report(cluster_profile: pd.DataFrame, feature_profile: pd.DataFrame) -> pd.DataFrame:
    rows = []

    for cluster in sorted(cluster_profile["cluster_kmeans"].unique()):
        cp = cluster_profile[cluster_profile["cluster_kmeans"] == cluster].iloc[0]

        top_features = (
            feature_profile[feature_profile["cluster_kmeans"] == cluster]
            .head(8)["feature"]
            .tolist()
        )

        rows.append({
            "cluster_kmeans": int(cluster),
            "n_observaciones": int(cp["n_observaciones"]),
            "pct_observaciones": cp["pct_observaciones"],
            "has_conafor_rate": cp.get("has_conafor_rate", np.nan),
            "has_firms_rate": cp.get("has_firms_rate", np.nan),
            "temporada_incendios_rate": cp.get("temporada_incendios_rate", np.nan),
            "variables_mas_distintivas": "; ".join(top_features),
        })

    return pd.DataFrame(rows)


# ============================================================
# PIPELINE PRINCIPAL
# ============================================================

def main():
    print("\nModeling 08 | Perfilado de clusters KMeans")
    print(f"Flujo: {FLUJO}")

    for path in [INPUT_BASE, INPUT_CLUSTERS, INPUT_DIAG]:
        if not path.exists():
            raise FileNotFoundError(f"No existe archivo requerido: {path}")

    print("\nLeyendo dataset base:")
    print(f"- {INPUT_BASE}")
    base = pd.read_csv(INPUT_BASE, encoding="utf-8-sig", low_memory=False)

    print("\nLeyendo clusters por observación:")
    print(f"- {INPUT_CLUSTERS}")
    clusters = pd.read_csv(INPUT_CLUSTERS, encoding="utf-8-sig", low_memory=False)

    if len(base) != len(clusters):
        raise ValueError(
            f"Base y clusters no tienen la misma cantidad de filas: "
            f"{len(base):,} vs {len(clusters):,}"
        )

    id_cols = ID_COLS_BY_FLOW[FLUJO]
    ensure_columns(base, id_cols, "dataset base")
    ensure_columns(clusters, id_cols + ["cluster_kmeans"], "clusters por observación")

    # Validar que el orden coincida
    for col in id_cols:
        left = base[col].astype(str).reset_index(drop=True)
        right = clusters[col].astype(str).reset_index(drop=True)

        if not left.equals(right):
            raise ValueError(
                f"El orden o contenido de la columna ID '{col}' no coincide "
                "entre dataset base y clusters."
            )

    df = base.copy()
    df["cluster_kmeans"] = clusters["cluster_kmeans"].astype(int)

    df["fecha"] = pd.to_datetime(df["fecha"], errors="coerce").dt.strftime("%Y-%m-%d")

    # Derivar flags de disponibilidad para perfilado si no vienen en el dataset base
    if "has_firms" not in df.columns and "firms_count" in df.columns:
        df["has_firms"] = (pd.to_numeric(df["firms_count"], errors="coerce").fillna(0) > 0).astype(int)

    if "has_smn" not in df.columns and "smn_n_estaciones" in df.columns:
        df["has_smn"] = (pd.to_numeric(df["smn_n_estaciones"], errors="coerce").fillna(0) > 0).astype(int)

    if "has_conafor" not in df.columns and "conafor_event_count" in df.columns:
        df["has_conafor"] = (pd.to_numeric(df["conafor_event_count"], errors="coerce").fillna(0) > 0).astype(int)

    if "mes" not in df.columns:
        df["mes"] = pd.to_datetime(df["fecha"], errors="coerce").dt.month

    profile_cols = get_available_profile_cols(df)

    print(f"\nFilas perfiladas: {len(df):,}")
    print(f"Clusters detectados: {df['cluster_kmeans'].nunique():,}")
    print(f"Variables usadas para perfilado: {len(profile_cols):,}")

    df = safe_numeric(df, profile_cols)

    cluster_profile = build_cluster_profile(df, profile_cols)
    feature_profile = build_feature_profile(df, profile_cols)
    cluster_entity = build_cluster_entity_distribution(df)
    cluster_month = build_cluster_month_distribution(df)
    profile_report = build_profile_report(cluster_profile, feature_profile)

    cluster_profile.to_csv(OUT_PROFILE, index=False, encoding="utf-8-sig")
    feature_profile.to_csv(OUT_FEATURE_PROFILE, index=False, encoding="utf-8-sig")
    cluster_entity.to_csv(OUT_CLUSTER_ENTITY, index=False, encoding="utf-8-sig")
    cluster_month.to_csv(OUT_CLUSTER_MONTH, index=False, encoding="utf-8-sig")
    profile_report.to_csv(OUT_PROFILE_REPORT, index=False, encoding="utf-8-sig")

    print(f"\nArchivos generados:")
    print(f"- {OUT_PROFILE}")
    print(f"- {OUT_FEATURE_PROFILE}")
    print(f"- {OUT_CLUSTER_ENTITY}")
    print(f"- {OUT_CLUSTER_MONTH}")
    print(f"- {OUT_PROFILE_REPORT}")

    print("\nResumen de clusters:")
    cols_show = [
        "cluster_kmeans",
        "n_observaciones",
        "pct_observaciones",
        "has_conafor_rate",
        "has_firms_rate",
        "temporada_incendios_rate",
    ]

    cols_show = [c for c in cols_show if c in profile_report.columns]
    print(profile_report[cols_show].to_string(index=False))

    print("\nProceso terminado.")


if __name__ == "__main__":
    main()