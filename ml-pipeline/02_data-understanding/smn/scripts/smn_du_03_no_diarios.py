# -*- coding: utf-8 -*-
"""
SMN-CONAGUA | Data Understanding DU-03
Resumen de productos no diarios: mensual y extremos

Objetivo:
- Revisar archivos mensuales y extremos.
- Identificar estructura general por secciones.
- Documentar su uso metodológico.

Entrada:
- 01_raw-data/smn-conagua/*/mensual/mes*.txt
- 01_raw-data/smn-conagua/*/ext/medex*.txt

Salida:
- smn_du03_no_diarios_resumen.csv
"""

from pathlib import Path
import re
import unicodedata
import pandas as pd


# =========================
# CONFIGURACIÓN
# =========================

BASE_DIR = Path(r"C:\Users\Hp\OneDrive\Documentos\PT_Analisis")

RAW_DIR = BASE_DIR / "01_raw-data" / "smn-conagua"
OUT_DIR = BASE_DIR / "02_data-understanding" / "smn" / "reports"

OUT_FILE = OUT_DIR / "smn_du03_no_diarios_resumen.csv"

OUT_DIR.mkdir(parents=True, exist_ok=True)

ENCODINGS = ["utf-8-sig", "utf-8", "latin-1", "cp1252"]


# =========================
# SECCIONES ESPERADAS
# =========================

SECCIONES_MENSUAL = [
    "LLUVIA MÁXIMA 24 H.",
    "LLUVIA TOTAL MENSUAL",
    "EVAPORACIÓN MENSUAL",
    "TEMPERATURA MÁXIMA PROMEDIO",
    "TEMPERATURA MÁXIMA EXTREMA",
    "TEMPERATURA MÍNIMA PROMEDIO",
    "TEMPERATURA MÍNIMA EXTREMA",
    "TEMPERATURA MEDIA MENSUAL",
]

SECCIONES_EXTREMOS = [
    "TEMPERATURA MÁXIMA",
    "TEMPERATURA MÍNIMA",
    "PRECIPITACIÓN",
    "EVAPORACIÓN",
]


# =========================
# UTILIDADES
# =========================

def strip_accents(value: str) -> str:
    nfkd = unicodedata.normalize("NFKD", str(value))
    return "".join(c for c in nfkd if not unicodedata.combining(c))


def normalize_for_match(value: str) -> str:
    value = strip_accents(value.upper().strip())
    value = re.sub(r"\s+", " ", value)
    return value


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


def parse_header_metadata(lines: list[str], path: Path):
    meta = {
        "id_estacion_cabecera": None,
        "nombre_estacion": None,
        "estado_cabecera": None,
        "municipio": None,
        "situacion_operativa": None,
        "cve_omm": None,
        "latitud": None,
        "longitud": None,
        "altitud_msnm": None,
    }

    for line in lines:
        raw = line.strip()
        if not raw:
            continue

        upper = normalize_for_match(raw)

        if upper.startswith("ESTACION") and ":" in raw:
            value = raw.split(":", 1)[1].strip()
            digits = "".join(c for c in value if c.isdigit())
            meta["id_estacion_cabecera"] = digits.zfill(5) if digits else None

        elif upper.startswith("NOMBRE") and ":" in raw:
            meta["nombre_estacion"] = raw.split(":", 1)[1].strip() or None

        elif upper.startswith("ESTADO") and ":" in raw:
            meta["estado_cabecera"] = raw.split(":", 1)[1].strip() or None

        elif upper.startswith("MUNICIPIO") and ":" in raw:
            meta["municipio"] = raw.split(":", 1)[1].strip() or None

        elif upper.startswith("SITUACION") and ":" in raw:
            meta["situacion_operativa"] = raw.split(":", 1)[1].strip() or None

        elif "CVE-OMM" in upper and ":" in raw:
            meta["cve_omm"] = raw.split(":", 1)[1].strip() or None

        elif upper.startswith("LATITUD") and ":" in raw:
            meta["latitud"] = raw.split(":", 1)[1].strip()

        elif upper.startswith("LONGITUD") and ":" in raw:
            meta["longitud"] = raw.split(":", 1)[1].strip()

        elif upper.startswith("ALTITUD") and ":" in raw:
            meta["altitud_msnm"] = raw.split(":", 1)[1].strip()

    if meta["id_estacion_cabecera"] is None:
        meta["id_estacion_cabecera"] = extract_station_id(path.name)

    return meta


def count_detected_sections(lines: list[str], expected_sections: list[str]):
    expected_norm = [normalize_for_match(s) for s in expected_sections]

    detected = []
    for line in lines:
        line_norm = normalize_for_match(line)

        for section_original, section_norm in zip(expected_sections, expected_norm):
            if line_norm == section_norm:
                detected.append(section_original)

    detected_unique = sorted(set(detected), key=detected.index)

    return detected_unique


def detect_year_rows(lines: list[str]):
    count = 0

    for line in lines:
        raw = line.strip()
        if re.match(r"^(18|19|20)\d{2}\s+", raw):
            count += 1

    return count


def inspect_file(path: Path, producto: str):
    text, encoding_used, read_note = read_text_robust(path)

    estado_ruta = infer_estado_from_path(path)
    id_archivo = extract_station_id(path.name)

    row = {
        "estado_ruta": estado_ruta,
        "producto": producto,
        "archivo": path.name,
        "ruta_relativa": str(path.relative_to(RAW_DIR)),
        "id_estacion_archivo": id_archivo,
        "id_estacion_cabecera": None,
        "id_archivo_vs_cabecera_ok": None,
        "nombre_estacion": None,
        "estado_cabecera": None,
        "municipio": None,
        "situacion_operativa": None,
        "cve_omm": None,
        "encoding": encoding_used,
        "archivo_leido": text is not None,
        "secciones_esperadas": 0,
        "secciones_detectadas": 0,
        "secciones_faltantes": None,
        "lista_secciones_detectadas": None,
        "filas_anio_detectadas": 0,
        "granularidad": None,
        "uso_crisp_dm": None,
        "decision": None,
        "nota": read_note,
    }

    if text is None:
        row["decision"] = "revisar_error_lectura"
        row["uso_crisp_dm"] = "revisar"
        return row

    lines = text.splitlines()
    meta = parse_header_metadata(lines, path)

    row.update({
        "id_estacion_cabecera": meta["id_estacion_cabecera"],
        "id_archivo_vs_cabecera_ok": id_archivo == meta["id_estacion_cabecera"],
        "nombre_estacion": meta["nombre_estacion"],
        "estado_cabecera": meta["estado_cabecera"],
        "municipio": meta["municipio"],
        "situacion_operativa": meta["situacion_operativa"],
        "cve_omm": meta["cve_omm"],
    })

    if producto == "mensual":
        expected = SECCIONES_MENSUAL
        row["granularidad"] = "mensual"
        row["uso_crisp_dm"] = "visualizacion_contexto_descriptivo"
        row["decision"] = "documentar_no_integrar_ml_base_diario"

    elif producto == "extremos":
        expected = SECCIONES_EXTREMOS
        row["granularidad"] = "mensual_climatologica_extremos"
        row["uso_crisp_dm"] = "visualizacion_contexto_validacion"
        row["decision"] = "documentar_no_integrar_ml_base_diario"

    else:
        expected = []
        row["granularidad"] = "desconocida"
        row["uso_crisp_dm"] = "revisar"
        row["decision"] = "producto_no_esperado"

    detected = count_detected_sections(lines, expected)
    missing = [s for s in expected if s not in detected]

    row["secciones_esperadas"] = len(expected)
    row["secciones_detectadas"] = len(detected)
    row["secciones_faltantes"] = " | ".join(missing) if missing else ""
    row["lista_secciones_detectadas"] = " | ".join(detected)
    row["filas_anio_detectadas"] = detect_year_rows(lines)

    if missing:
        row["nota"] = (row["nota"] + " | " if row["nota"] else "") + "secciones_faltantes"

    return row


def main():
    mensual_files = sorted(RAW_DIR.glob("*/mensual/mes*.txt"))
    extremos_files = sorted(RAW_DIR.glob("*/ext/medex*.txt"))

    rows = []

    print("\nSMN-CONAGUA | DU-03 Productos no diarios\n")
    print(f"Mensuales detectados: {len(mensual_files):,}")
    print(f"Extremos detectados: {len(extremos_files):,}")

    for i, path in enumerate(mensual_files, start=1):
        print(f"[MENSUAL {i:,}/{len(mensual_files):,}] {path.relative_to(RAW_DIR)}", flush=True)
        rows.append(inspect_file(path, "mensual"))

    for i, path in enumerate(extremos_files, start=1):
        print(f"[EXTREMOS {i:,}/{len(extremos_files):,}] {path.relative_to(RAW_DIR)}", flush=True)
        rows.append(inspect_file(path, "extremos"))

    df = pd.DataFrame(rows)
    df.to_csv(OUT_FILE, index=False, encoding="utf-8-sig")

    print("\nResumen:")
    print(f"- Archivos no diarios procesados: {len(df):,}")
    print(f"- Estados detectados: {df['estado_ruta'].nunique():,}")

    print("\nPor producto:")
    print(df.groupby("producto")["archivo"].count().to_string())

    print("\nLectura:")
    print(df["archivo_leido"].value_counts(dropna=False).to_string())

    print("\nID archivo vs cabecera:")
    print(df["id_archivo_vs_cabecera_ok"].value_counts(dropna=False).to_string())

    print("\nSecciones detectadas por producto:")
    print(
        df.groupby("producto")["secciones_detectadas"]
        .value_counts()
        .sort_index()
        .to_string()
    )

    print("\nDecisiones metodológicas:")
    print(df["decision"].value_counts(dropna=False).to_string())

    print(f"\nArchivo generado:\n- {OUT_FILE}\n")


if __name__ == "__main__":
    main()