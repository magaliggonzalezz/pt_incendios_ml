# -*- coding: utf-8 -*-
"""
SMN-CONAGUA | Data Preparation DP-01
Dataset maestro diario limpio 2001-2025

Objetivo:
- Preparar un único dataset diario limpio de SMN/CONAGUA.
- Usar solo archivos diarios: 01_raw-data/smn-conagua/*/diario/dia*.txt
- Aplicar reglas mínimas de limpieza necesarias para DP.
- Mantener trazabilidad con reportes globales y por estación.
- No imputar.
- No escalar.
- No generar variables derivadas.
- No seleccionar todavía subconjuntos CORE/EXTENDIDO para modelado.

Entradas:
- 01_raw-data/smn-conagua/*/diario/dia*.txt
- 02_data-understanding/smn/reports/smn_du02_diario_perfil.csv
- 02_data-understanding/smn/reports/smn_du02_diario_calidad.csv

Salidas:
- 03_data-preparation/smn/outputs/smn_dp01_diario_limpio_2001_2025.csv
- 03_data-preparation/smn/reports/smn_dp01_reporte_global.csv
- 03_data-preparation/smn/reports/smn_dp01_reporte_por_estacion.csv
"""

from __future__ import annotations

from pathlib import Path
from datetime import datetime
from collections import Counter
import re
import unicodedata
import pandas as pd


# =========================
# CONFIGURACIÓN
# =========================

BASE_DIR = Path(r"C:\Users\Hp\OneDrive\Documentos\PT_Analisis")

RAW_DIR = BASE_DIR / "01_raw-data" / "smn-conagua"
DU_DIR = BASE_DIR / "02_data-understanding" / "smn" / "reports"

OUT_DIR = BASE_DIR / "03_data-preparation" / "smn"
OUT_DATA_DIR = OUT_DIR / "datasets"
OUT_REPORT_DIR = OUT_DIR / "reports"

DU_PERFIL = DU_DIR / "smn_du02_diario_perfil.csv"
DU_CALIDAD = DU_DIR / "smn_du02_diario_calidad.csv"

YEAR_START = 2001
YEAR_END = 2025

PERIOD_START = datetime(YEAR_START, 1, 1).date()
PERIOD_END = datetime(YEAR_END, 12, 31).date()

OUT_DATASET = OUT_DATA_DIR / f"smn_dp01_diario_limpio_{YEAR_START}_{YEAR_END}.csv"
OUT_REPORT_GLOBAL = OUT_REPORT_DIR / "smn_dp01_reporte_global.csv"
OUT_REPORT_STATION = OUT_REPORT_DIR / "smn_dp01_reporte_por_estacion.csv"

OUT_DATA_DIR.mkdir(parents=True, exist_ok=True)
OUT_REPORT_DIR.mkdir(parents=True, exist_ok=True)

ENCODINGS = ["utf-8-sig", "utf-8", "latin-1", "cp1252"]

TEXT_SENTINELS = {
    "", "NULO", "NULL", "NA", "N/A", "ND", "S/D", "NR"
}

NUMERIC_SENTINELS = {
    -9999.0, -999.0, 9999.0, 99999.0, 99.99, 999.9, 8888.0, 7777.0
}


# =========================
# UTILIDADES
# =========================

def strip_accents(value: str) -> str:
    nfkd = unicodedata.normalize("NFKD", str(value))
    return "".join(c for c in nfkd if not unicodedata.combining(c))


def clean_text_value(value):
    if value is None:
        return None

    s = str(value)

    if s.lower() in {"none", "nan"}:
        return None

    s = "".join(ch for ch in s if ch.isprintable())
    s = unicodedata.normalize("NFC", s)
    s = re.sub(r"\s+", " ", s).strip()

    return s if s else None


def clean_float(value):
    s = str(value).strip()

    if s.upper() in TEXT_SENTINELS:
        return None

    s = s.replace(",", ".")

    try:
        num = float(s)
    except ValueError:
        return None

    if num in NUMERIC_SENTINELS:
        return None

    return num


def parse_date_any(value):
    s = str(value).strip()

    if not s:
        return None

    formats = [
        "%Y-%m-%d",
        "%d/%m/%Y",
        "%d-%m-%Y",
        "%Y/%m/%d",
        "%Y%m%d",
    ]

    for fmt in formats:
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue

    return None


def read_text_robust(path: Path):
    for enc in ENCODINGS:
        try:
            return path.read_text(encoding=enc), enc, ""
        except Exception:
            continue

    try:
        return path.read_text(encoding="latin-1", errors="replace"), "latin-1/replace", "lectura_con_reemplazo"
    except Exception as exc:
        return None, None, f"error_lectura: {exc}"


def extract_station_id(filename: str):
    match = re.search(r"(\d+)", filename)

    if not match:
        return None

    return match.group(1).zfill(5)


def infer_estado_from_path(path: Path):
    try:
        return path.relative_to(RAW_DIR).parts[0]
    except Exception:
        return None


def parse_station_header(lines: list[str], path: Path):
    meta = {
        "id_estacion": None,
        "nombre_estacion": None,
        "estado": None,
        "municipio": None,
        "situacion_operativa": None,
        "cve_omm": None,
        "latitud": None,
        "longitud": None,
        "altitud_msnm": None,
    }

    table_idx = None
    header_tokens = []

    for i, line in enumerate(lines):
        raw = line.strip()

        if not raw:
            continue

        upper = strip_accents(raw.upper())

        if upper.startswith("FECHA"):
            table_idx = i
            header_tokens = re.split(r"\s+", raw)
            break

        if upper.startswith("ESTACION") and ":" in raw:
            value = raw.split(":", 1)[1].strip()
            digits = "".join(c for c in value if c.isdigit())
            meta["id_estacion"] = digits.zfill(5) if digits else None

        elif upper.startswith("NOMBRE") and ":" in raw:
            meta["nombre_estacion"] = clean_text_value(raw.split(":", 1)[1])

        elif upper.startswith("ESTADO") and ":" in raw:
            meta["estado"] = clean_text_value(raw.split(":", 1)[1])

        elif upper.startswith("MUNICIPIO") and ":" in raw:
            meta["municipio"] = clean_text_value(raw.split(":", 1)[1])

        elif upper.startswith("SITUACION") and ":" in raw:
            meta["situacion_operativa"] = clean_text_value(raw.split(":", 1)[1])

        elif "CVE-OMM" in upper and ":" in raw:
            meta["cve_omm"] = clean_text_value(raw.split(":", 1)[1])

        elif upper.startswith("LATITUD") and ":" in raw:
            value = raw.split(":", 1)[1].replace("°", " ").replace("º", " ").strip()
            meta["latitud"] = clean_float(value.split()[0] if value.split() else "")

        elif upper.startswith("LONGITUD") and ":" in raw:
            value = raw.split(":", 1)[1].replace("°", " ").replace("º", " ").strip()
            meta["longitud"] = clean_float(value.split()[0] if value.split() else "")

        elif upper.startswith("ALTITUD") and ":" in raw:
            value = (
                raw.split(":", 1)[1]
                .replace("msnm", " ")
                .replace("MSNM", " ")
                .replace("m.s.n.m.", " ")
                .strip()
            )
            meta["altitud_msnm"] = clean_float(value.split()[0] if value.split() else "")

    if meta["id_estacion"] is None:
        meta["id_estacion"] = extract_station_id(path.name)

    return meta, table_idx, header_tokens


def load_du_reference():
    """
    Carga DU reducido para conservar trazabilidad.
    No usa clasificación CORE/EXTENDIDO.
    """
    if not DU_PERFIL.exists():
        raise FileNotFoundError(f"No se encontró DU_PERFIL: {DU_PERFIL}")

    if not DU_CALIDAD.exists():
        raise FileNotFoundError(f"No se encontró DU_CALIDAD: {DU_CALIDAD}")

    perfil = pd.read_csv(DU_PERFIL, dtype={"id_estacion_archivo": "string", "id_estacion_cabecera": "string"})
    calidad = pd.read_csv(DU_CALIDAD, dtype={"id_estacion": "string"})

    perfil["id_estacion_archivo"] = perfil["id_estacion_archivo"].astype("string").str.zfill(5)
    perfil["id_estacion_cabecera"] = perfil["id_estacion_cabecera"].astype("string").str.zfill(5)
    calidad["id_estacion"] = calidad["id_estacion"].astype("string").str.zfill(5)

    estaciones_con_datos_periodo = set(
        perfil.loc[perfil["registros_en_periodo"] > 0, "id_estacion_cabecera"].dropna().astype(str)
    )

    return perfil, calidad, estaciones_con_datos_periodo


def init_station_report(station_id, meta, estado_ruta):
    return {
        "id_estacion": station_id,
        "estado_ruta": estado_ruta,
        "nombre_estacion": meta.get("nombre_estacion"),
        "estado": meta.get("estado"),
        "municipio": meta.get("municipio"),
        "situacion_operativa": meta.get("situacion_operativa"),
        "latitud": meta.get("latitud"),
        "longitud": meta.get("longitud"),
        "altitud_msnm": meta.get("altitud_msnm"),
        "registros_leidos_en_periodo": 0,
        "registros_fuera_periodo": 0,
        "fechas_invalidas": 0,
        "filas_4_variables_faltantes_eliminadas": 0,
        "filas_inconsistencias_eliminadas": 0,
        "filas_coord_fuera_rango_eliminadas": 0,
        "duplicados_fecha_detectados": 0,
        "registros_finales": 0,
        "fecha_min_final": None,
        "fecha_max_final": None,
    }


def update_date_bounds(report, fecha):
    if report["fecha_min_final"] is None or fecha < report["fecha_min_final"]:
        report["fecha_min_final"] = fecha

    if report["fecha_max_final"] is None or fecha > report["fecha_max_final"]:
        report["fecha_max_final"] = fecha


def is_coord_invalid(lat, lon):
    if lat is None or lon is None:
        return True

    if not (-90 <= lat <= 90):
        return True

    if not (-180 <= lon <= 180):
        return True

    # BBox aproximado México usado en DU.
    if not (14.0 <= lat <= 33.5 and -119.0 <= lon <= -86.0):
        return True

    return False


def process_one_file(path: Path):
    estado_ruta = infer_estado_from_path(path)

    text, encoding_used, read_note = read_text_robust(path)

    if text is None:
        return [], None, {
            "archivo": str(path.relative_to(RAW_DIR)),
            "error": read_note,
        }

    lines = text.splitlines()
    meta, table_idx, header_tokens = parse_station_header(lines, path)

    station_id = meta["id_estacion"]
    station_id_file = extract_station_id(path.name)

    station_report = init_station_report(station_id, meta, estado_ruta)

    if table_idx is None:
        return [], station_report, {
            "archivo": str(path.relative_to(RAW_DIR)),
            "error": "tabla_no_detectada",
        }

    header_norm = [strip_accents(x.upper()) for x in header_tokens]
    expected_header = header_norm[:5] == ["FECHA", "PRECIP", "EVAP", "TMAX", "TMIN"]

    if not expected_header:
        return [], station_report, {
            "archivo": str(path.relative_to(RAW_DIR)),
            "error": f"encabezado_no_esperado: {' '.join(header_tokens)}",
        }

    if station_id != station_id_file:
        return [], station_report, {
            "archivo": str(path.relative_to(RAW_DIR)),
            "error": f"id_archivo_vs_cabecera_no_coincide: {station_id_file} vs {station_id}",
        }

    records = []
    fecha_counter = Counter()

    data_lines = lines[table_idx + 2:]

    for line in data_lines:
        raw = line.strip()

        if not raw:
            continue

        parts = re.split(r"\s+", raw)

        if not parts:
            continue

        fecha = parse_date_any(parts[0])

        if fecha is None:
            station_report["fechas_invalidas"] += 1
            continue

        if fecha < PERIOD_START or fecha > PERIOD_END:
            station_report["registros_fuera_periodo"] += 1
            continue

        station_report["registros_leidos_en_periodo"] += 1
        fecha_counter[fecha] += 1

        values = [
            parts[1] if len(parts) > 1 else "",
            parts[2] if len(parts) > 2 else "",
            parts[3] if len(parts) > 3 else "",
            parts[4] if len(parts) > 4 else "",
        ]

        precipitacion_mm = clean_float(values[0])
        evaporacion_mm = clean_float(values[1])
        tmax_c = clean_float(values[2])
        tmin_c = clean_float(values[3])

        meteo_values = [precipitacion_mm, evaporacion_mm, tmax_c, tmin_c]

        # Regla DP-01: eliminar filas sin ninguna variable meteorológica útil.
        if all(v is None for v in meteo_values):
            station_report["filas_4_variables_faltantes_eliminadas"] += 1
            continue

        # Regla DP-02: eliminar inconsistencias físicas básicas.
        inconsistente = False

        if precipitacion_mm is not None and precipitacion_mm < 0:
            inconsistente = True

        if evaporacion_mm is not None and evaporacion_mm < 0:
            inconsistente = True

        if tmax_c is not None and tmin_c is not None and tmax_c < tmin_c:
            inconsistente = True

        if inconsistente:
            station_report["filas_inconsistencias_eliminadas"] += 1
            continue

        # Regla DP-03: eliminar coordenadas inválidas.
        lat = meta["latitud"]
        lon = meta["longitud"]

        if is_coord_invalid(lat, lon):
            station_report["filas_coord_fuera_rango_eliminadas"] += 1
            continue

        record = {
            "id_estacion": station_id,
            "nombre_estacion": meta["nombre_estacion"],
            "estado": meta["estado"],
            "municipio": meta["municipio"],
            "situacion_operativa": meta["situacion_operativa"],
            "cve_omm": meta["cve_omm"],
            "latitud": lat,
            "longitud": lon,
            "altitud_msnm": meta["altitud_msnm"],
            "fecha": fecha.isoformat(),
            "precipitacion_mm": precipitacion_mm,
            "evaporacion_mm": evaporacion_mm,
            "tmax_c": tmax_c,
            "tmin_c": tmin_c,
            "source_file": str(path.relative_to(RAW_DIR)),
            "source_product": "smn_diario",
        }

        records.append(record)
        station_report["registros_finales"] += 1
        update_date_bounds(station_report, fecha)

    station_report["duplicados_fecha_detectados"] = sum(
        count - 1 for count in fecha_counter.values() if count > 1
    )

    return records, station_report, None


def build_global_report(df_final, station_reports, error_rows, du_perfil, du_calidad):
    total_final = len(df_final)

    rows = [
        {"metrica": "fuente", "valor": "SMN-CONAGUA"},
        {"metrica": "producto", "valor": "diario"},
        {"metrica": "periodo_objetivo", "valor": f"{YEAR_START}-01-01 a {YEAR_END}-12-31"},
        {"metrica": "archivos_diarios_esperados_du", "valor": int(len(du_perfil))},
        {"metrica": "archivos_diarios_procesados", "valor": int(len(station_reports) + len(error_rows))},
        {"metrica": "archivos_con_error_bloqueante", "valor": int(len(error_rows))},
        {"metrica": "estaciones_du_con_registros_en_periodo", "valor": int((du_perfil["registros_en_periodo"] > 0).sum())},
        {"metrica": "estaciones_finales_dp", "valor": int(df_final["id_estacion"].nunique()) if total_final else 0},
        {"metrica": "registros_du_en_periodo", "valor": int(du_perfil["registros_en_periodo"].sum())},
        {"metrica": "registros_leidos_en_periodo", "valor": int(sum(r["registros_leidos_en_periodo"] for r in station_reports))},
        {"metrica": "registros_fuera_periodo", "valor": int(sum(r["registros_fuera_periodo"] for r in station_reports))},
        {"metrica": "fechas_invalidas", "valor": int(sum(r["fechas_invalidas"] for r in station_reports))},
        {"metrica": "filas_4_variables_faltantes_eliminadas", "valor": int(sum(r["filas_4_variables_faltantes_eliminadas"] for r in station_reports))},
        {"metrica": "filas_inconsistencias_eliminadas", "valor": int(sum(r["filas_inconsistencias_eliminadas"] for r in station_reports))},
        {"metrica": "filas_coord_fuera_rango_eliminadas", "valor": int(sum(r["filas_coord_fuera_rango_eliminadas"] for r in station_reports))},
        {"metrica": "duplicados_fecha_detectados_pre_dedupe", "valor": int(sum(r["duplicados_fecha_detectados"] for r in station_reports))},
        {"metrica": "registros_finales", "valor": int(total_final)},
        {"metrica": "fecha_min_final", "valor": str(df_final["fecha"].min()) if total_final else None},
        {"metrica": "fecha_max_final", "valor": str(df_final["fecha"].max()) if total_final else None},
        {"metrica": "faltantes_precipitacion_mm_final", "valor": int(df_final["precipitacion_mm"].isna().sum()) if total_final else 0},
        {"metrica": "faltantes_evaporacion_mm_final", "valor": int(df_final["evaporacion_mm"].isna().sum()) if total_final else 0},
        {"metrica": "faltantes_tmax_c_final", "valor": int(df_final["tmax_c"].isna().sum()) if total_final else 0},
        {"metrica": "faltantes_tmin_c_final", "valor": int(df_final["tmin_c"].isna().sum()) if total_final else 0},
    ]

    return pd.DataFrame(rows)


def main():
    print("\nSMN-CONAGUA | DP-01 Diario limpio 2001-2025\n")

    du_perfil, du_calidad, estaciones_con_datos_periodo = load_du_reference()

    files = sorted(RAW_DIR.glob("*/diario/dia*.txt"))

    if not files:
        raise FileNotFoundError(f"No se encontraron archivos diarios en: {RAW_DIR}")

    all_records = []
    station_reports = []
    error_rows = []

    for i, path in enumerate(files, start=1):
        print(f"[{i:,}/{len(files):,}] {path.relative_to(RAW_DIR)}", flush=True)

        records, station_report, error = process_one_file(path)

        if error is not None:
            error_rows.append(error)

        if station_report is not None:
            station_reports.append(station_report)

        if records:
            all_records.extend(records)

    if not all_records:
        raise RuntimeError("No se generaron registros finales. Revisar reglas de DP.")

    df = pd.DataFrame(all_records)

    # Tipos y orden
    df["id_estacion"] = df["id_estacion"].astype("string").str.zfill(5)
    df["fecha"] = pd.to_datetime(df["fecha"], errors="coerce").dt.strftime("%Y-%m-%d")

    text_cols = [
        "nombre_estacion",
        "estado",
        "municipio",
        "situacion_operativa",
        "cve_omm",
        "source_file",
        "source_product",
    ]

    for col in text_cols:
        df[col] = df[col].astype("string")

    numeric_cols = [
        "latitud",
        "longitud",
        "altitud_msnm",
        "precipitacion_mm",
        "evaporacion_mm",
        "tmax_c",
        "tmin_c",
    ]

    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    # Dedupe defensivo, aunque DU indicó 0 duplicados.
    duplicados_finales = int(df.duplicated(subset=["id_estacion", "fecha"], keep="first").sum())
    df = df.drop_duplicates(subset=["id_estacion", "fecha"], keep="first")

    df = df.sort_values(by=["fecha", "id_estacion"], kind="mergesort").reset_index(drop=True)

    final_cols = [
        "id_estacion",
        "nombre_estacion",
        "estado",
        "municipio",
        "situacion_operativa",
        "cve_omm",
        "latitud",
        "longitud",
        "altitud_msnm",
        "fecha",
        "precipitacion_mm",
        "evaporacion_mm",
        "tmax_c",
        "tmin_c",
        "source_file",
        "source_product",
    ]

    df = df[final_cols]

    # Reporte por estación
    station_report_df = pd.DataFrame(station_reports)

    for col in ["fecha_min_final", "fecha_max_final"]:
        station_report_df[col] = station_report_df[col].apply(
            lambda x: x.isoformat() if hasattr(x, "isoformat") else x
        )

    # Marcar estaciones con registros finales
    station_report_df["tiene_registros_finales"] = station_report_df["registros_finales"] > 0

    # Agregar duplicados finales eliminados al reporte global
    global_report = build_global_report(df, station_reports, error_rows, du_perfil, du_calidad)

    global_report = pd.concat([
        global_report,
        pd.DataFrame([
            {"metrica": "duplicados_eliminados_final", "valor": duplicados_finales},
        ])
    ], ignore_index=True)

    # Guardado
    df.to_csv(OUT_DATASET, index=False, encoding="utf-8-sig")
    global_report.to_csv(OUT_REPORT_GLOBAL, index=False, encoding="utf-8-sig")
    station_report_df.to_csv(OUT_REPORT_STATION, index=False, encoding="utf-8-sig")

    print("\nResumen DP-01:")
    print(f"- Archivos diarios procesados: {len(files):,}")
    print(f"- Errores bloqueantes de archivo: {len(error_rows):,}")
    print(f"- Registros finales: {len(df):,}")
    print(f"- Estaciones finales: {df['id_estacion'].nunique():,}")
    print(f"- Fecha mínima final: {df['fecha'].min()}")
    print(f"- Fecha máxima final: {df['fecha'].max()}")
    print(f"- Duplicados eliminados final: {duplicados_finales:,}")

    print("\nArchivos generados:")
    print(f"- {OUT_DATASET}")
    print(f"- {OUT_REPORT_GLOBAL}")
    print(f"- {OUT_REPORT_STATION}\n")


if __name__ == "__main__":
    main()