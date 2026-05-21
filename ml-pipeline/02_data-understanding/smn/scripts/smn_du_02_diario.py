# -*- coding: utf-8 -*-
"""
SMN-CONAGUA | Data Understanding DU-02
Perfil estructural y calidad base del producto diario

Objetivo:
- Revisar solo archivos diarios dia*.txt.
- Caracterizar estructura, cobertura temporal, metadatos y calidad base.

Entradas:
- 01_raw-data/smn-conagua/*/diario/dia*.txt

Salidas:
- smn_du02_diario_perfil.csv
- smn_du02_diario_calidad.csv
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
OUT_DIR = BASE_DIR / "02_data-understanding" / "smn" / "reports"

OUT_PERFIL = OUT_DIR / "smn_du02_diario_perfil.csv"
OUT_CALIDAD = OUT_DIR / "smn_du02_diario_calidad.csv"

OUT_DIR.mkdir(parents=True, exist_ok=True)

YEAR_START = 2001
YEAR_END = 2025

PERIOD_START = datetime(YEAR_START, 1, 1).date()
PERIOD_END = datetime(YEAR_END, 12, 31).date()
DIAS_ESPERADOS_PERIODO = (PERIOD_END - PERIOD_START).days + 1

ENCODINGS = ["utf-8-sig", "utf-8", "latin-1", "cp1252"]

VARIABLES_METEO = ["precip_mm", "evap_mm", "tmax_c", "tmin_c"]

TEXT_SENTINELS = {
    "NULO", "NULL", "NA", "N/A", "ND", "S/D", "NR", ""
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


def clean_float(value: str):
    s = str(value).strip()

    if not s or s.upper() in TEXT_SENTINELS:
        return None

    s = s.replace(",", ".")

    try:
        return float(s)
    except ValueError:
        return None


def parse_date_any(value: str):
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
        rel = path.relative_to(RAW_DIR)
        return rel.parts[0]
    except Exception:
        return None


def parse_station_header(lines: list[str], path: Path):
    meta = {
        "id_estacion": None,
        "nombre_estacion": None,
        "estado_cabecera": None,
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
            continue

        if upper.startswith("NOMBRE") and ":" in raw:
            meta["nombre_estacion"] = raw.split(":", 1)[1].strip() or None
            continue

        if upper.startswith("ESTADO") and ":" in raw:
            meta["estado_cabecera"] = raw.split(":", 1)[1].strip() or None
            continue

        if upper.startswith("MUNICIPIO") and ":" in raw:
            meta["municipio"] = raw.split(":", 1)[1].strip() or None
            continue

        if upper.startswith("SITUACION") and ":" in raw:
            meta["situacion_operativa"] = raw.split(":", 1)[1].strip() or None
            continue

        if "CVE-OMM" in upper and ":" in raw:
            meta["cve_omm"] = raw.split(":", 1)[1].strip() or None
            continue

        if upper.startswith("LATITUD") and ":" in raw:
            value = raw.split(":", 1)[1].replace("°", " ").replace("º", " ").strip()
            meta["latitud"] = clean_float(value.split()[0] if value.split() else "")
            continue

        if upper.startswith("LONGITUD") and ":" in raw:
            value = raw.split(":", 1)[1].replace("°", " ").replace("º", " ").strip()
            meta["longitud"] = clean_float(value.split()[0] if value.split() else "")
            continue

        if upper.startswith("ALTITUD") and ":" in raw:
            value = (
                raw.split(":", 1)[1]
                .replace("msnm", " ")
                .replace("MSNM", " ")
                .replace("m.s.n.m.", " ")
                .strip()
            )
            meta["altitud_msnm"] = clean_float(value.split()[0] if value.split() else "")
            continue

    if not meta["id_estacion"]:
        meta["id_estacion"] = extract_station_id(path.name)

    return meta, table_idx, header_tokens


def classify_raw_token(raw_token: str):
    s = str(raw_token).strip()
    s_upper = s.upper()

    if s_upper in TEXT_SENTINELS:
        return "text_sentinel"

    s_num = s.replace(",", ".")

    try:
        value = float(s_num)
        if value in NUMERIC_SENTINELS:
            return "numeric_sentinel"
        return "numeric"
    except ValueError:
        return "not_numeric"


def inspect_daily_file(path: Path):
    estado_ruta = infer_estado_from_path(path)

    perfil = {
        "estado_ruta": estado_ruta,
        "archivo": path.name,
        "ruta_relativa": str(path.relative_to(RAW_DIR)),
        "id_estacion_archivo": extract_station_id(path.name),
        "id_estacion_cabecera": None,
        "nombre_estacion": None,
        "estado_cabecera": None,
        "municipio": None,
        "situacion_operativa": None,
        "cve_omm": None,
        "latitud": None,
        "longitud": None,
        "altitud_msnm": None,
        "encoding": None,
        "cabecera_detectada": False,
        "tabla_detectada": False,
        "header_tokens": None,
        "orden_esperado": False,
        "id_archivo_vs_cabecera_ok": False,
        "coord_dentro_bbox_mexico_aprox": None,
        "fecha_min_historica": None,
        "fecha_max_historica": None,
        "fecha_min_periodo": None,
        "fecha_max_periodo": None,
        "registros_historicos": 0,
        "registros_en_periodo": 0,
        "fechas_invalidas": 0,
        "registros_fuera_periodo": 0,
        "dias_unicos_en_periodo": 0,
        "duplicados_fecha_en_periodo": 0,
        "nota": "",
    }

    calidad = {
        "estado_ruta": estado_ruta,
        "archivo": path.name,
        "id_estacion": extract_station_id(path.name),
        "registros_en_periodo": 0,
        "faltantes_precip_mm": 0,
        "faltantes_evap_mm": 0,
        "faltantes_tmax_c": 0,
        "faltantes_tmin_c": 0,
        "sentinelas_texto_precip_mm": 0,
        "sentinelas_texto_evap_mm": 0,
        "sentinelas_texto_tmax_c": 0,
        "sentinelas_texto_tmin_c": 0,
        "sentinelas_numericos_precip_mm": 0,
        "sentinelas_numericos_evap_mm": 0,
        "sentinelas_numericos_tmax_c": 0,
        "sentinelas_numericos_tmin_c": 0,
        "no_numericos_precip_mm": 0,
        "no_numericos_evap_mm": 0,
        "no_numericos_tmax_c": 0,
        "no_numericos_tmin_c": 0,
        "filas_todas_variables_faltantes": 0,
        "inconsistencias_precip_negativa": 0,
        "inconsistencias_evap_negativa": 0,
        "inconsistencias_tmax_menor_tmin": 0,
    }

    text, encoding_used, read_note = read_text_robust(path)

    perfil["encoding"] = encoding_used

    if text is None:
        perfil["nota"] = read_note
        return perfil, calidad

    lines = text.splitlines()
    meta, table_idx, header_tokens = parse_station_header(lines, path)

    perfil.update({
        "id_estacion_cabecera": meta["id_estacion"],
        "nombre_estacion": meta["nombre_estacion"],
        "estado_cabecera": meta["estado_cabecera"],
        "municipio": meta["municipio"],
        "situacion_operativa": meta["situacion_operativa"],
        "cve_omm": meta["cve_omm"],
        "latitud": meta["latitud"],
        "longitud": meta["longitud"],
        "altitud_msnm": meta["altitud_msnm"],
        "cabecera_detectada": True,
        "id_archivo_vs_cabecera_ok": meta["id_estacion"] == perfil["id_estacion_archivo"],
    })

    calidad["id_estacion"] = meta["id_estacion"]

    if meta["latitud"] is not None and meta["longitud"] is not None:
        perfil["coord_dentro_bbox_mexico_aprox"] = (
            14.0 <= meta["latitud"] <= 33.5
            and -119.0 <= meta["longitud"] <= -86.0
        )

    if table_idx is None:
        perfil["nota"] = "tabla_no_detectada"
        return perfil, calidad

    perfil["tabla_detectada"] = True
    perfil["header_tokens"] = " | ".join(header_tokens)

    header_norm = [strip_accents(x.upper()) for x in header_tokens]
    perfil["orden_esperado"] = header_norm[:5] == ["FECHA", "PRECIP", "EVAP", "TMAX", "TMIN"]

    if not perfil["orden_esperado"]:
        perfil["nota"] = f"encabezado_no_esperado: {' '.join(header_tokens)}"

    fechas_en_periodo = Counter()

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
            perfil["fechas_invalidas"] += 1
            continue

        perfil["registros_historicos"] += 1

        if perfil["fecha_min_historica"] is None or fecha < perfil["fecha_min_historica"]:
            perfil["fecha_min_historica"] = fecha

        if perfil["fecha_max_historica"] is None or fecha > perfil["fecha_max_historica"]:
            perfil["fecha_max_historica"] = fecha

        if fecha < PERIOD_START or fecha > PERIOD_END:
            perfil["registros_fuera_periodo"] += 1
            continue

        perfil["registros_en_periodo"] += 1
        calidad["registros_en_periodo"] += 1
        fechas_en_periodo[fecha] += 1

        if perfil["fecha_min_periodo"] is None or fecha < perfil["fecha_min_periodo"]:
            perfil["fecha_min_periodo"] = fecha

        if perfil["fecha_max_periodo"] is None or fecha > perfil["fecha_max_periodo"]:
            perfil["fecha_max_periodo"] = fecha

        values = [
            parts[1] if len(parts) > 1 else "",
            parts[2] if len(parts) > 2 else "",
            parts[3] if len(parts) > 3 else "",
            parts[4] if len(parts) > 4 else "",
        ]

        numeric_values = []

        for var_name, raw_value in zip(VARIABLES_METEO, values):
            token_type = classify_raw_token(raw_value)
            value = clean_float(raw_value)
            numeric_values.append(value)

            if value is None:
                calidad[f"faltantes_{var_name}"] += 1

            if token_type == "text_sentinel":
                calidad[f"sentinelas_texto_{var_name}"] += 1

            elif token_type == "numeric_sentinel":
                calidad[f"sentinelas_numericos_{var_name}"] += 1

            elif token_type == "not_numeric":
                calidad[f"no_numericos_{var_name}"] += 1

        precip, evap, tmax, tmin = numeric_values

        if all(v is None for v in numeric_values):
            calidad["filas_todas_variables_faltantes"] += 1

        if precip is not None and precip < 0:
            calidad["inconsistencias_precip_negativa"] += 1

        if evap is not None and evap < 0:
            calidad["inconsistencias_evap_negativa"] += 1

        if tmax is not None and tmin is not None and tmax < tmin:
            calidad["inconsistencias_tmax_menor_tmin"] += 1

    perfil["dias_unicos_en_periodo"] = len(fechas_en_periodo)
    perfil["duplicados_fecha_en_periodo"] = sum(
        count - 1 for count in fechas_en_periodo.values() if count > 1
    )

    for col in [
        "fecha_min_historica",
        "fecha_max_historica",
        "fecha_min_periodo",
        "fecha_max_periodo",
    ]:
        if perfil[col] is not None:
            perfil[col] = perfil[col].isoformat()

    return perfil, calidad


def build_global_console_summary(df_perfil: pd.DataFrame, df_calidad: pd.DataFrame):
    print("\nSMN-CONAGUA | DU-02 Diario perfil/calidad\n")

    print(f"Archivos diarios procesados: {len(df_perfil):,}")
    print(f"Estados detectados: {df_perfil['estado_ruta'].nunique():,}")

    print("\nEstructura:")
    print(f"- Cabeceras detectadas: {int(df_perfil['cabecera_detectada'].sum()):,}")
    print(f"- Tablas detectadas: {int(df_perfil['tabla_detectada'].sum()):,}")
    print(f"- Orden esperado FECHA/PRECIP/EVAP/TMAX/TMIN: {int(df_perfil['orden_esperado'].sum()):,}")
    print(f"- ID archivo vs cabecera OK: {int(df_perfil['id_archivo_vs_cabecera_ok'].sum()):,}")

    print("\nCobertura:")
    print(f"- Registros históricos: {int(df_perfil['registros_historicos'].sum()):,}")
    print(f"- Registros en periodo {YEAR_START}-{YEAR_END}: {int(df_perfil['registros_en_periodo'].sum()):,}")
    print(f"- Fechas inválidas: {int(df_perfil['fechas_invalidas'].sum()):,}")
    print(f"- Duplicados fecha en periodo: {int(df_perfil['duplicados_fecha_en_periodo'].sum()):,}")

    print("\nCalidad:")
    metricas_calidad = [
        "faltantes_precip_mm",
        "faltantes_evap_mm",
        "faltantes_tmax_c",
        "faltantes_tmin_c",
        "filas_todas_variables_faltantes",
        "inconsistencias_precip_negativa",
        "inconsistencias_evap_negativa",
        "inconsistencias_tmax_menor_tmin",
    ]

    for col in metricas_calidad:
        print(f"- {col}: {int(df_calidad[col].sum()):,}")

    print("\nArchivos generados:")
    print(f"- {OUT_PERFIL}")
    print(f"- {OUT_CALIDAD}\n")


def main():
    files = sorted(RAW_DIR.glob("*/diario/dia*.txt"))

    if not files:
        raise FileNotFoundError(f"No se encontraron archivos diarios en: {RAW_DIR}")

    perfiles = []
    calidades = []

    for i, path in enumerate(files, start=1):
        print(f"[{i:,}/{len(files):,}] {path.relative_to(RAW_DIR)}", flush=True)

        perfil, calidad = inspect_daily_file(path)

        perfiles.append(perfil)
        calidades.append(calidad)

    df_perfil = pd.DataFrame(perfiles)
    df_calidad = pd.DataFrame(calidades)

    df_perfil.to_csv(OUT_PERFIL, index=False, encoding="utf-8-sig")
    df_calidad.to_csv(OUT_CALIDAD, index=False, encoding="utf-8-sig")

    build_global_console_summary(df_perfil, df_calidad)


if __name__ == "__main__":
    main()