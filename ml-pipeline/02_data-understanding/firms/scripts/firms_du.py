# -*- coding: utf-8 -*-
"""
NASA FIRMS | Data Understanding (DU)

Objetivo
--------
Generar un reporte maestro de comprensión de datos para archivos CSV de NASA FIRMS.

Este script corresponde a Data Understanding bajo CRISP-DM.
No modifica datos originales.
No limpia, no filtra y no consolida datasets.
Solo inspecciona, perfila y documenta hallazgos.

Salida
------
02_data-understanding/firms/reports/firms_du_report.csv

Evalúa
------
- Inventario de archivos CSV
- Producto / familia satelital
- Modo del producto: archive, nrt o unknown
- Esquema / columnas por archivo
- Cobertura temporal observada
- Fechas fuera del periodo del proyecto 2001-2025
- Calidad básica de datos
- Duplicados exactos
- Coordenadas geográficas
- Dominios observados en variables clave
- Hallazgos globales
- Decisión DU preliminar por archivo
"""

from __future__ import annotations

import csv
import json
import re
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple


# =========================================================
# 1) CONFIGURACIÓN
# =========================================================

BASE_DIR = Path(r"C:\Users\Hp\OneDrive\Documentos\PT_ANALISIS")

ROOT_DIR = BASE_DIR / "01_raw-data" / "firms"
OUT_DIR = BASE_DIR / "02_data-understanding" / "firms" / "reports"

OUT_REPORT = OUT_DIR / "firms_du_report.csv"

OUT_DIR.mkdir(parents=True, exist_ok=True)

PROJECT_START = datetime(2001, 1, 1)
PROJECT_END = datetime(2025, 12, 31)

ENCODINGS = ["utf-8-sig", "utf-8", "latin-1", "cp1252"]
SAMPLE_ROWS = 5

# BBOX aproximado de México.
# Importante: esto NO sustituye una validación contra polígono nacional.
MEXICO_BBOX = {
    "lat_min": 14.0,
    "lat_max": 33.5,
    "lon_min": -118.5,
    "lon_max": -86.0,
}

KEY_COLUMNS = [
    "latitude",
    "longitude",
    "brightness",
    "scan",
    "track",
    "acq_date",
    "acq_time",
    "satellite",
    "instrument",
    "confidence",
    "version",
    "bright_t31",
    "frp",
    "daynight",
    "type",
]

CRITICAL_COLUMNS = [
    "latitude",
    "longitude",
    "acq_date",
    "acq_time",
]

MISSING_TOKENS = {
    "",
    " ",
    "NA",
    "N/A",
    "NULL",
    "NONE",
    "NULO",
    "nan",
    "NaN",
    "-",
    "--",
    "S/D",
    "SD",
    "SIN DATO",
}

DATE_FORMATS = [
    ("%Y-%m-%d", re.compile(r"^\d{4}-\d{2}-\d{2}$")),
    ("%Y/%m/%d", re.compile(r"^\d{4}/\d{2}/\d{2}$")),
    ("%d/%m/%Y", re.compile(r"^\d{2}/\d{2}/\d{4}$")),
    ("%d-%m-%Y", re.compile(r"^\d{2}-\d{2}-\d{4}$")),
    ("%Y%m%d", re.compile(r"^\d{8}$")),
]

TIME_PATTERNS = [
    re.compile(r"^\d{4}$"),
    re.compile(r"^\d{1,2}:\d{2}$"),
]


# =========================================================
# 2) UTILIDADES
# =========================================================

def try_open(path: Path):
    for enc in ENCODINGS:
        try:
            f = open(path, "r", newline="", encoding=enc)
            return f, enc
        except Exception:
            continue
    return None, None


def normalize_cell(v) -> str:
    if v is None:
        return ""
    return str(v).strip()


def is_missing(v) -> bool:
    s = normalize_cell(v)
    return s in MISSING_TOKENS


def safe_json(value) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def safe_ratio(num: int, den: int) -> float:
    return round((num / den) * 100.0, 4) if den else 0.0


def parse_float(v) -> Optional[float]:
    s = normalize_cell(v)
    if not s or s in MISSING_TOKENS:
        return None
    try:
        return float(s)
    except Exception:
        return None


def classify_as_date(value: str):
    s = normalize_cell(value)
    if not s or s in MISSING_TOKENS:
        return False, None, None

    for fmt, rgx in DATE_FORMATS:
        if rgx.match(s):
            try:
                dt = datetime.strptime(s, fmt)
                return True, fmt, dt
            except Exception:
                pass

    return False, None, None


def detect_date_column_from_samples(header: List[str], samples: List[Dict[str, str]]):
    best_col = None
    best_ok = 0
    best_fmt = None
    total = len(samples)

    for col in header:
        ok_count = 0
        fmt_count = defaultdict(int)

        for row_map in samples:
            ok, fmt, _dt = classify_as_date(row_map.get(col, ""))
            if ok:
                ok_count += 1
                fmt_count[fmt] += 1

        if ok_count > best_ok:
            best_ok = ok_count
            best_col = col
            best_fmt = max(fmt_count.items(), key=lambda x: x[1])[0] if fmt_count else None

    if best_ok == 0:
        return None, None, 0, total

    return best_col, best_fmt, best_ok, total


def sample_preview(reader, header: List[str], k: int) -> List[Dict[str, str]]:
    out = []

    for _ in range(k):
        try:
            row = next(reader)
        except StopIteration:
            break

        if len(row) < len(header):
            row = row + [""] * (len(header) - len(row))
        elif len(row) > len(header):
            row = row[:len(header)]

        out.append({header[i]: row[i] for i in range(len(header))})

    return out


def detect_product_mode(path: Path) -> str:
    p = str(path).lower()

    if "archive" in p:
        return "ARCHIVE"

    if "nrt" in p:
        return "NRT"

    return "UNKNOWN_MODE"


def infer_product_family(path: Path, header: List[str]) -> str:
    p = str(path).lower()
    mode = detect_product_mode(path)

    if "m-c61" in p or "modis" in p:
        base = "MODIS"
    elif "sv-c2" in p or "snpp" in p or "suomi" in p:
        base = "SUOMI_VIIRS"
    elif "j1v-c2" in p or "j1" in p:
        base = "J1_VIIRS"
    elif "j2v-c2" in p or "j2" in p:
        base = "J2_VIIRS"
    elif "viirs" in p:
        base = "VIIRS"
    else:
        base = "UNKNOWN"

    return f"{base}_{mode}"


def classify_du_usage(producto: str, modo_producto: str) -> Tuple[str, str]:
    """
    Clasificación preliminar para DU.
    No filtra ni modifica archivos.
    Solo documenta la decisión metodológica inicial.
    """

    producto = producto or ""
    modo_producto = modo_producto or ""

    if modo_producto == "ARCHIVE" and "UNKNOWN" not in producto:
        return (
            "ml_candidato_principal_archive",
            "Producto archive consolidado; candidato principal para Data Preparation y posterior integración/ML."
        )

    if modo_producto == "NRT":
        return (
            "visualizacion_contexto_o_respaldo",
            "Producto NRT; no debe mezclarse automáticamente con archive. Revisar solo si falta cobertura archive."
        )

    return (
        "revisar_manual",
        "Producto o modo no clasificado automáticamente; requiere revisión manual antes de DP."
    )


def valid_time_basic(v: str) -> bool:
    s = normalize_cell(v)
    if not s or s in MISSING_TOKENS:
        return False

    for pat in TIME_PATTERNS:
        if pat.match(s):
            if len(s) == 4 and s.isdigit():
                hh = int(s[:2])
                mm = int(s[2:])
                return 0 <= hh <= 23 and 0 <= mm <= 59

            if ":" in s:
                hh, mm = s.split(":")
                return (
                    hh.isdigit()
                    and mm.isdigit()
                    and 0 <= int(hh) <= 23
                    and 0 <= int(mm) <= 59
                )

    return False


def row_to_tuple(row: List[str], width: int) -> Tuple[str, ...]:
    if len(row) < width:
        row = row + [""] * (width - len(row))
    elif len(row) > width:
        row = row[:width]

    return tuple(normalize_cell(x) for x in row)


def within_bbox_mexico_aprox(lat: Optional[float], lon: Optional[float]) -> Optional[bool]:
    if lat is None or lon is None:
        return None

    return (
        MEXICO_BBOX["lat_min"] <= lat <= MEXICO_BBOX["lat_max"]
        and MEXICO_BBOX["lon_min"] <= lon <= MEXICO_BBOX["lon_max"]
    )


def top_n(counter: Counter, n: int = 10):
    return counter.most_common(n)


# =========================================================
# 3) PERFILADO POR ARCHIVO
# =========================================================

def analyze_file(path: Path) -> Dict[str, object]:
    result = {
        "tipo_fila": "archivo",
        "archivo": path.name,
        "ruta": str(path),
        "producto": None,
        "modo_producto": None,
        "uso_du_preliminar": None,
        "decision_du": None,
        "encoding": None,
        "registros": 0,
        "num_campos": 0,
        "columnas_presentes": [],
        "fecha_columna": None,
        "fecha_formato": None,
        "periodo_inicio": None,
        "periodo_fin": None,
        "fecha_parse_ok": 0,
        "fecha_parse_fail": 0,
        "fecha_parse_ok_pct": 0.0,
        "fechas_fuera_periodo_proyecto": 0,
        "faltantes_totales": 0,
        "filas_header_short": 0,
        "filas_header_long": 0,
        "filas_vacias": 0,
        "duplicados_exactos": 0,
        "latitud_min": None,
        "latitud_max": None,
        "longitud_min": None,
        "longitud_max": None,
        "latlon_missing_rows": 0,
        "lat_fuera_rango": 0,
        "lon_fuera_rango": 0,
        "coords_fuera_bbox_mexico_aprox": 0,
        "time_invalid_rows": 0,
        "faltantes_columnas_criticas": {},
        "dominios_clave": {},
        "columnas_faltantes_vs_union": [],
        "columnas_extra_vs_interseccion": [],
        "nota": "",
    }

    f, enc = try_open(path)

    if f is None:
        result["nota"] = "No se pudo abrir con encodings conocidos"
        return result

    result["encoding"] = enc

    with f:
        reader = csv.reader(f)

        try:
            header = next(reader)
        except StopIteration:
            result["nota"] = "Archivo vacío"
            result["columnas_presentes"] = []
            return result

        header = [normalize_cell(h) for h in header]

        result["columnas_presentes"] = header
        result["num_campos"] = len(header)
        result["modo_producto"] = detect_product_mode(path)
        result["producto"] = infer_product_family(path, header)

        uso, decision = classify_du_usage(
            producto=str(result["producto"]),
            modo_producto=str(result["modo_producto"]),
        )

        result["uso_du_preliminar"] = uso
        result["decision_du"] = decision

        samples = sample_preview(reader, header, SAMPLE_ROWS)
        date_col, date_fmt, _ok, _total = detect_date_column_from_samples(header, samples)

        result["fecha_columna"] = date_col
        result["fecha_formato"] = date_fmt

    f, _enc = try_open(path)

    if f is None:
        result["nota"] = "No se pudo reabrir para análisis completo"
        return result

    missing_by_col = Counter()
    domain_counters = {c: Counter() for c in KEY_COLUMNS if c in header}
    exact_rows_seen = set()

    lat_min = None
    lat_max = None
    lon_min = None
    lon_max = None

    lat_exists = "latitude" in header
    lon_exists = "longitude" in header
    time_exists = "acq_time" in header

    with f:
        reader = csv.reader(f)
        next(reader, None)

        idx_map = {col: i for i, col in enumerate(header)}
        idx_date = idx_map.get(result["fecha_columna"]) if result["fecha_columna"] in idx_map else None
        idx_lat = idx_map.get("latitude")
        idx_lon = idx_map.get("longitude")
        idx_time = idx_map.get("acq_time")

        min_dt = None
        max_dt = None
        date_ok = 0
        date_fail = 0

        for row in reader:
            result["registros"] += 1

            if len(row) == 0:
                result["filas_vacias"] += 1
                continue

            if len(row) < len(header):
                result["filas_header_short"] += 1
                row = row + [""] * (len(header) - len(row))
            elif len(row) > len(header):
                result["filas_header_long"] += 1
                row = row[:len(header)]

            row_key = row_to_tuple(row, len(header))

            if row_key in exact_rows_seen:
                result["duplicados_exactos"] += 1
            else:
                exact_rows_seen.add(row_key)

            row_map = {header[i]: row[i] for i in range(len(header))}

            row_missing = 0

            for col in header:
                if is_missing(row_map[col]):
                    missing_by_col[col] += 1
                    row_missing += 1

            result["faltantes_totales"] += row_missing

            for col in domain_counters:
                val = normalize_cell(row_map.get(col, ""))
                if val and val not in MISSING_TOKENS:
                    domain_counters[col][val] += 1

            if idx_date is not None:
                raw_date = row[idx_date]
                s = normalize_cell(raw_date)

                if not s or s in MISSING_TOKENS:
                    date_fail += 1
                else:
                    parsed = None

                    if result["fecha_formato"] is not None:
                        try:
                            parsed = datetime.strptime(s, result["fecha_formato"])
                        except Exception:
                            parsed = None

                    if parsed is None:
                        ok, _fmt2, dt2 = classify_as_date(s)
                        if ok:
                            parsed = dt2

                    if parsed is None:
                        date_fail += 1
                    else:
                        date_ok += 1

                        if min_dt is None or parsed < min_dt:
                            min_dt = parsed

                        if max_dt is None or parsed > max_dt:
                            max_dt = parsed

                        if parsed < PROJECT_START or parsed > PROJECT_END:
                            result["fechas_fuera_periodo_proyecto"] += 1

            lat = parse_float(row[idx_lat]) if idx_lat is not None else None
            lon = parse_float(row[idx_lon]) if idx_lon is not None else None

            if lat_exists or lon_exists:
                if lat is None or lon is None:
                    result["latlon_missing_rows"] += 1

            if lat is not None:
                lat_min = lat if lat_min is None else min(lat_min, lat)
                lat_max = lat if lat_max is None else max(lat_max, lat)

                if not (-90 <= lat <= 90):
                    result["lat_fuera_rango"] += 1

            if lon is not None:
                lon_min = lon if lon_min is None else min(lon_min, lon)
                lon_max = lon if lon_max is None else max(lon_max, lon)

                if not (-180 <= lon <= 180):
                    result["lon_fuera_rango"] += 1

            in_mx_bbox = within_bbox_mexico_aprox(lat, lon)

            if in_mx_bbox is False:
                result["coords_fuera_bbox_mexico_aprox"] += 1

            if time_exists and idx_time is not None:
                val_time = row[idx_time]

                if not is_missing(val_time) and not valid_time_basic(val_time):
                    result["time_invalid_rows"] += 1

        result["fecha_parse_ok"] = date_ok
        result["fecha_parse_fail"] = date_fail
        result["fecha_parse_ok_pct"] = safe_ratio(date_ok, date_ok + date_fail)
        result["periodo_inicio"] = min_dt.strftime("%Y-%m-%d") if min_dt else None
        result["periodo_fin"] = max_dt.strftime("%Y-%m-%d") if max_dt else None

        result["latitud_min"] = lat_min
        result["latitud_max"] = lat_max
        result["longitud_min"] = lon_min
        result["longitud_max"] = lon_max

        crit = {}

        for c in CRITICAL_COLUMNS:
            if c in header:
                crit[c] = {
                    "faltantes": int(missing_by_col[c]),
                    "faltantes_pct": safe_ratio(int(missing_by_col[c]), result["registros"]),
                }

        result["faltantes_columnas_criticas"] = crit

        dominios = {}

        for c, counter in domain_counters.items():
            dominios[c] = {
                "n_unicos": len(counter),
                "top": top_n(counter, 10),
            }

        result["dominios_clave"] = dominios

        notes = []

        if result["modo_producto"] != "ARCHIVE":
            notes.append(f"modo_no_archive={result['modo_producto']}")

        if result["filas_header_short"] > 0:
            notes.append(f"filas_cortas={result['filas_header_short']}")

        if result["filas_header_long"] > 0:
            notes.append(f"filas_largas={result['filas_header_long']}")

        if result["duplicados_exactos"] > 0:
            notes.append(f"duplicados_exactos={result['duplicados_exactos']}")

        if result["lat_fuera_rango"] > 0 or result["lon_fuera_rango"] > 0:
            notes.append("coords_fuera_rango_global")

        if result["coords_fuera_bbox_mexico_aprox"] > 0:
            notes.append(f"coords_fuera_bbox_mexico_aprox={result['coords_fuera_bbox_mexico_aprox']}")

        if result["time_invalid_rows"] > 0:
            notes.append(f"acq_time_invalid={result['time_invalid_rows']}")

        if result["fechas_fuera_periodo_proyecto"] > 0:
            notes.append(f"fechas_fuera_periodo_proyecto={result['fechas_fuera_periodo_proyecto']}")

        result["nota"] = "; ".join(notes)

    return result


# =========================================================
# 4) RESUMEN GLOBAL
# =========================================================

def build_global_rows(rows: List[Dict[str, object]]) -> List[Dict[str, object]]:
    if not rows:
        return []

    total_files = len(rows)
    total_records = sum(int(r["registros"]) for r in rows)

    union_cols = set()
    intersection_cols = None
    products = Counter()
    modes = Counter()

    total_duplicates = 0
    total_lat_bad = 0
    total_lon_bad = 0
    total_bbox_out = 0
    total_time_bad = 0
    total_date_fail = 0
    total_date_ok = 0
    total_missing = 0
    total_short = 0
    total_long = 0
    total_empty = 0
    total_latlon_missing = 0
    total_fechas_fuera_periodo = 0

    file_with_type = 0
    file_without_type = 0

    period_starts = []
    period_ends = []

    for r in rows:
        cols = set(r["columnas_presentes"])
        union_cols |= cols
        intersection_cols = cols if intersection_cols is None else (intersection_cols & cols)

        products[str(r["producto"])] += 1
        modes[str(r["modo_producto"])] += 1

        total_duplicates += int(r["duplicados_exactos"])
        total_lat_bad += int(r["lat_fuera_rango"])
        total_lon_bad += int(r["lon_fuera_rango"])
        total_bbox_out += int(r["coords_fuera_bbox_mexico_aprox"])
        total_time_bad += int(r["time_invalid_rows"])
        total_date_fail += int(r["fecha_parse_fail"])
        total_date_ok += int(r["fecha_parse_ok"])
        total_missing += int(r["faltantes_totales"])
        total_short += int(r["filas_header_short"])
        total_long += int(r["filas_header_long"])
        total_empty += int(r["filas_vacias"])
        total_latlon_missing += int(r["latlon_missing_rows"])
        total_fechas_fuera_periodo += int(r["fechas_fuera_periodo_proyecto"])

        if "type" in cols:
            file_with_type += 1
        else:
            file_without_type += 1

        if r["periodo_inicio"]:
            period_starts.append(r["periodo_inicio"])

        if r["periodo_fin"]:
            period_ends.append(r["periodo_fin"])

    global_start = min(period_starts) if period_starts else None
    global_end = max(period_ends) if period_ends else None

    findings = []

    if modes.get("NRT", 0) == 0:
        findings.append("No se detectaron archivos NRT en el inventario actual.")

    if modes.get("ARCHIVE", 0) == total_files:
        findings.append("Todos los archivos detectados corresponden a productos archive.")

    if file_without_type > 0 and file_with_type > 0:
        findings.append(
            f"Heterogeneidad estructural: {file_without_type} archivo(s) no incluyen 'type', mientras {file_with_type} sí."
        )

    if total_duplicates == 0:
        findings.append("No se detectaron duplicados exactos dentro de los archivos.")
    else:
        findings.append(f"Se detectaron {total_duplicates:,} duplicados exactos dentro de archivos.")

    if total_lat_bad == 0 and total_lon_bad == 0:
        findings.append("No se detectaron coordenadas fuera del rango geográfico global válido.")
    else:
        findings.append(
            f"Inconsistencias geográficas globales: latitudes fuera de rango={total_lat_bad:,}, longitudes fuera de rango={total_lon_bad:,}."
        )

    if total_bbox_out == 0:
        findings.append("No se detectaron coordenadas fuera del bbox aproximado de México.")
    else:
        findings.append(
            f"Se detectaron {total_bbox_out:,} registros fuera del bbox aproximado de México. Esto no equivale a validación por polígono nacional."
        )

    if total_time_bad == 0:
        findings.append("No se detectaron inconsistencias básicas en 'acq_time'.")
    else:
        findings.append(f"Se detectaron {total_time_bad:,} registros con 'acq_time' no válido.")

    if total_date_fail == 0:
        findings.append("Todas las fechas detectadas fueron interpretables.")
    else:
        findings.append(f"Se detectaron {total_date_fail:,} fechas no interpretables.")

    if total_fechas_fuera_periodo == 0:
        findings.append("No se detectaron fechas fuera del periodo del proyecto 2001-2025.")
    else:
        findings.append(
            f"Se detectaron {total_fechas_fuera_periodo:,} registros con fechas fuera del periodo del proyecto 2001-2025."
        )

    summary_row = {
        "tipo_fila": "resumen_global",
        "archivo": "__GLOBAL__",
        "ruta": str(ROOT_DIR),
        "producto": safe_json(dict(products)),
        "modo_producto": safe_json(dict(modes)),
        "uso_du_preliminar": None,
        "decision_du": None,
        "encoding": None,
        "registros": total_records,
        "num_campos": len(union_cols),
        "columnas_presentes": safe_json(sorted(union_cols)),
        "columnas_faltantes_vs_union": safe_json([]),
        "columnas_extra_vs_interseccion": safe_json(sorted(union_cols - (intersection_cols or set()))),
        "fecha_columna": "GLOBAL",
        "fecha_formato": "MIXED_OR_DETECTED",
        "periodo_inicio": global_start,
        "periodo_fin": global_end,
        "fecha_parse_ok": total_date_ok,
        "fecha_parse_fail": total_date_fail,
        "fecha_parse_ok_pct": safe_ratio(total_date_ok, total_date_ok + total_date_fail),
        "fechas_fuera_periodo_proyecto": total_fechas_fuera_periodo,
        "faltantes_totales": total_missing,
        "filas_header_short": total_short,
        "filas_header_long": total_long,
        "filas_vacias": total_empty,
        "duplicados_exactos": total_duplicates,
        "latitud_min": None,
        "latitud_max": None,
        "longitud_min": None,
        "longitud_max": None,
        "latlon_missing_rows": total_latlon_missing,
        "lat_fuera_rango": total_lat_bad,
        "lon_fuera_rango": total_lon_bad,
        "coords_fuera_bbox_mexico_aprox": total_bbox_out,
        "time_invalid_rows": total_time_bad,
        "faltantes_columnas_criticas": None,
        "dominios_clave": None,
        "nota": (
            f"archivos={total_files}; "
            f"con_type={file_with_type}; "
            f"sin_type={file_without_type}; "
            f"interseccion_cols={len(intersection_cols or set())}"
        ),
    }

    findings_row = {
        "tipo_fila": "hallazgos_globales",
        "archivo": "__FINDINGS__",
        "ruta": None,
        "producto": None,
        "modo_producto": None,
        "uso_du_preliminar": None,
        "decision_du": None,
        "encoding": None,
        "registros": None,
        "num_campos": None,
        "columnas_presentes": None,
        "columnas_faltantes_vs_union": None,
        "columnas_extra_vs_interseccion": None,
        "fecha_columna": None,
        "fecha_formato": None,
        "periodo_inicio": None,
        "periodo_fin": None,
        "fecha_parse_ok": None,
        "fecha_parse_fail": None,
        "fecha_parse_ok_pct": None,
        "fechas_fuera_periodo_proyecto": None,
        "faltantes_totales": None,
        "filas_header_short": None,
        "filas_header_long": None,
        "filas_vacias": None,
        "duplicados_exactos": None,
        "latitud_min": None,
        "latitud_max": None,
        "longitud_min": None,
        "longitud_max": None,
        "latlon_missing_rows": None,
        "lat_fuera_rango": None,
        "lon_fuera_rango": None,
        "coords_fuera_bbox_mexico_aprox": None,
        "time_invalid_rows": None,
        "faltantes_columnas_criticas": None,
        "dominios_clave": None,
        "nota": " | ".join(findings),
    }

    return [summary_row, findings_row]


def flatten_rows_for_csv(
    rows: List[Dict[str, object]],
    all_columns_union: List[str],
    all_columns_intersection: List[str],
) -> List[Dict[str, object]]:
    flat_rows = []

    for r in rows:
        cols_present = set(r["columnas_presentes"])

        r["columnas_faltantes_vs_union"] = sorted(set(all_columns_union) - cols_present)
        r["columnas_extra_vs_interseccion"] = sorted(cols_present - set(all_columns_intersection))

        row = {
            "tipo_fila": r["tipo_fila"],
            "archivo": r["archivo"],
            "ruta": r["ruta"],
            "producto": r["producto"],
            "modo_producto": r["modo_producto"],
            "uso_du_preliminar": r["uso_du_preliminar"],
            "decision_du": r["decision_du"],
            "encoding": r["encoding"],
            "registros": r["registros"],
            "num_campos": r["num_campos"],
            "columnas_presentes": safe_json(r["columnas_presentes"]),
            "columnas_faltantes_vs_union": safe_json(r["columnas_faltantes_vs_union"]),
            "columnas_extra_vs_interseccion": safe_json(r["columnas_extra_vs_interseccion"]),
            "fecha_columna": r["fecha_columna"],
            "fecha_formato": r["fecha_formato"],
            "periodo_inicio": r["periodo_inicio"],
            "periodo_fin": r["periodo_fin"],
            "fecha_parse_ok": r["fecha_parse_ok"],
            "fecha_parse_fail": r["fecha_parse_fail"],
            "fecha_parse_ok_pct": r["fecha_parse_ok_pct"],
            "fechas_fuera_periodo_proyecto": r["fechas_fuera_periodo_proyecto"],
            "faltantes_totales": r["faltantes_totales"],
            "filas_header_short": r["filas_header_short"],
            "filas_header_long": r["filas_header_long"],
            "filas_vacias": r["filas_vacias"],
            "duplicados_exactos": r["duplicados_exactos"],
            "latitud_min": r["latitud_min"],
            "latitud_max": r["latitud_max"],
            "longitud_min": r["longitud_min"],
            "longitud_max": r["longitud_max"],
            "latlon_missing_rows": r["latlon_missing_rows"],
            "lat_fuera_rango": r["lat_fuera_rango"],
            "lon_fuera_rango": r["lon_fuera_rango"],
            "coords_fuera_bbox_mexico_aprox": r["coords_fuera_bbox_mexico_aprox"],
            "time_invalid_rows": r["time_invalid_rows"],
            "faltantes_columnas_criticas": safe_json(r["faltantes_columnas_criticas"]),
            "dominios_clave": safe_json(r["dominios_clave"]),
            "nota": r["nota"],
        }

        flat_rows.append(row)

    return flat_rows


# =========================================================
# 5) PIPELINE PRINCIPAL
# =========================================================

def main():
    print("\nNASA FIRMS | Data Understanding")
    print(f"Directorio raíz: {ROOT_DIR}")
    print(f"Directorio de salida: {OUT_DIR}")

    if not ROOT_DIR.exists():
        raise FileNotFoundError(f"No existe ROOT_DIR: {ROOT_DIR}")

    csv_files = sorted([p for p in ROOT_DIR.rglob("*.csv") if p.is_file()])

    if not csv_files:
        print("No se encontraron archivos CSV.")
        return

    results = []
    all_cols_union = set()
    all_cols_intersection = None

    for path in csv_files:
        print(f"\nAnalizando: {path.name}")

        r = analyze_file(path)
        results.append(r)

        cols = set(r["columnas_presentes"])
        all_cols_union |= cols
        all_cols_intersection = cols if all_cols_intersection is None else (all_cols_intersection & cols)

        print(f"  Registros: {int(r['registros']):,}")
        print(f"  Campos: {r['num_campos']}")
        print(f"  Producto: {r['producto']}")
        print(f"  Modo: {r['modo_producto']}")
        print(f"  Uso DU preliminar: {r['uso_du_preliminar']}")
        print(f"  Periodo: {r['periodo_inicio']} -> {r['periodo_fin']}")
        print(f"  Fechas fuera periodo proyecto: {int(r['fechas_fuera_periodo_proyecto']):,}")
        print(f"  Duplicados exactos: {int(r['duplicados_exactos']):,}")
        print(f"  Lat/lon fuera rango: {int(r['lat_fuera_rango']):,} / {int(r['lon_fuera_rango']):,}")
        print(f"  Fuera bbox México aprox: {int(r['coords_fuera_bbox_mexico_aprox']):,}")

    all_cols_union = sorted(all_cols_union)
    all_cols_intersection = sorted(all_cols_intersection or [])

    flat_rows = flatten_rows_for_csv(results, all_cols_union, all_cols_intersection)
    global_rows = build_global_rows(results)

    final_rows = flat_rows + global_rows

    if final_rows:
        fieldnames = list(final_rows[0].keys())

        with open(OUT_REPORT, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(final_rows)

    total_global = sum(int(r["registros"]) for r in results)

    print("\n=== RESUMEN GLOBAL ===")
    print(f"Archivos analizados: {len(results)}")
    print(f"Registros totales: {total_global:,}")
    print(f"Columnas unión: {len(all_cols_union)}")
    print(f"Columnas intersección: {len(all_cols_intersection)}")

    print("\nArchivo generado:")
    print(f"- {OUT_REPORT}")


if __name__ == "__main__":
    main()