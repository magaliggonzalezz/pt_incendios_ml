# -*- coding: utf-8 -*-
"""
SMN-CONAGUA | Data Understanding DU-01
Inventario maestro de productos meteorológicos

Objetivo:
- Inventariar archivos SMN por estado y producto.
- Identificar productos diarios, mensuales y extremos.
- Clasificar su uso metodológico dentro del proyecto.

Salida:
- smn_du01_inventario.csv
"""

from pathlib import Path
import re
import pandas as pd


# =========================
# CONFIGURACIÓN
# =========================

BASE_DIR = Path(r"C:\Users\Hp\OneDrive\Documentos\PT_Analisis")
RAW_DIR = BASE_DIR / "01_raw-data" / "smn-conagua"
OUT_DIR = BASE_DIR / "02_data-understanding" / "smn" / "reports"

OUT_FILE = OUT_DIR / "smn_du01_inventario.csv"

OUT_DIR.mkdir(parents=True, exist_ok=True)


# =========================
# REGLAS DE PRODUCTO
# =========================

PRODUCT_RULES = {
    "diario": {
        "expected_prefix": "dia",
        "producto_normalizado": "diario",
        "granularidad": "diaria",
        "uso_crisp_dm": "candidato_ml",
        "decision": "entra_a_du_dp_diario",
        "prioridad": "alta",
    },
    "mensual": {
        "expected_prefix": "mes",
        "producto_normalizado": "mensual",
        "granularidad": "mensual",
        "uso_crisp_dm": "visualizacion_contexto",
        "decision": "documentar_no_integrar_ml_base",
        "prioridad": "media_baja",
    },
    "ext": {
        "expected_prefix": "medex",
        "producto_normalizado": "extremos",
        "granularidad": "mensual_climatologica_extremos",
        "uso_crisp_dm": "visualizacion_contexto_validacion",
        "decision": "documentar_no_integrar_ml_base",
        "prioridad": "media_baja",
    },
}


# =========================
# FUNCIONES
# =========================

def normalize_text(value: str) -> str:
    return str(value).strip().lower()


def extract_station_id(filename: str) -> str | None:
    """
    Extrae el id de estación desde nombres como:
    - dia01001.txt
    - mes01001.txt
    - medex01001.txt
    """
    match = re.search(r"(\d+)", filename)
    if not match:
        return None
    return match.group(1).zfill(5)


def infer_product_from_folder(folder_name: str) -> dict:
    folder_key = normalize_text(folder_name)

    if folder_key in PRODUCT_RULES:
        return PRODUCT_RULES[folder_key]

    return {
        "expected_prefix": None,
        "producto_normalizado": folder_key,
        "granularidad": "desconocida",
        "uso_crisp_dm": "revisar",
        "decision": "producto_no_esperado",
        "prioridad": "revisar",
    }


def validate_filename(product_folder: str, filename: str) -> tuple[bool, str]:
    folder_key = normalize_text(product_folder)
    rule = PRODUCT_RULES.get(folder_key)

    if rule is None:
        return False, "producto_no_esperado"

    expected_prefix = rule["expected_prefix"]
    filename_lower = filename.lower()

    if not filename_lower.endswith(".txt"):
        return False, "extension_no_txt"

    if not filename_lower.startswith(expected_prefix):
        return False, "prefijo_no_esperado"

    if extract_station_id(filename) is None:
        return False, "sin_id_estacion_en_nombre"

    return True, "ok"


def build_inventory() -> pd.DataFrame:
    rows = []

    if not RAW_DIR.exists():
        raise FileNotFoundError(f"No existe RAW_DIR: {RAW_DIR}")

    for state_dir in sorted([p for p in RAW_DIR.iterdir() if p.is_dir()]):
        estado = state_dir.name

        product_dirs = sorted([p for p in state_dir.iterdir() if p.is_dir()])

        if not product_dirs:
            rows.append({
                "estado_ruta": estado,
                "producto_carpeta": None,
                "producto_normalizado": None,
                "granularidad": None,
                "archivo": None,
                "ruta_relativa": str(state_dir.relative_to(RAW_DIR)),
                "id_estacion_archivo": None,
                "extension": None,
                "nombre_archivo_valido": False,
                "validacion_nombre": "estado_sin_subcarpetas_producto",
                "uso_crisp_dm": "revisar",
                "decision": "revisar_estructura",
                "prioridad": "revisar",
            })
            continue

        for product_dir in product_dirs:
            producto_carpeta = product_dir.name
            rule = infer_product_from_folder(producto_carpeta)

            files = sorted([p for p in product_dir.iterdir() if p.is_file()])

            if not files:
                rows.append({
                    "estado_ruta": estado,
                    "producto_carpeta": producto_carpeta,
                    "producto_normalizado": rule["producto_normalizado"],
                    "granularidad": rule["granularidad"],
                    "archivo": None,
                    "ruta_relativa": str(product_dir.relative_to(RAW_DIR)),
                    "id_estacion_archivo": None,
                    "extension": None,
                    "nombre_archivo_valido": False,
                    "validacion_nombre": "carpeta_producto_sin_archivos",
                    "uso_crisp_dm": rule["uso_crisp_dm"],
                    "decision": rule["decision"],
                    "prioridad": rule["prioridad"],
                })
                continue

            for file_path in files:
                is_valid, validation_note = validate_filename(producto_carpeta, file_path.name)

                rows.append({
                    "estado_ruta": estado,
                    "producto_carpeta": producto_carpeta,
                    "producto_normalizado": rule["producto_normalizado"],
                    "granularidad": rule["granularidad"],
                    "archivo": file_path.name,
                    "ruta_relativa": str(file_path.relative_to(RAW_DIR)),
                    "id_estacion_archivo": extract_station_id(file_path.name),
                    "extension": file_path.suffix.lower(),
                    "nombre_archivo_valido": is_valid,
                    "validacion_nombre": validation_note,
                    "uso_crisp_dm": rule["uso_crisp_dm"],
                    "decision": rule["decision"],
                    "prioridad": rule["prioridad"],
                })

    return pd.DataFrame(rows)


def build_console_summary(df: pd.DataFrame) -> None:
    print("\nSMN-CONAGUA | DU-01 Inventario maestro\n")
    print(f"RAW_DIR: {RAW_DIR}")
    print(f"Total de registros inventariados: {len(df):,}")

    print("\nArchivos por producto:")
    print(
        df[df["archivo"].notna()]
        .groupby("producto_normalizado")["archivo"]
        .count()
        .sort_values(ascending=False)
        .to_string()
    )

    print("\nEstados detectados:")
    print(df["estado_ruta"].nunique())

    print("\nValidación de nombres:")
    print(df["validacion_nombre"].value_counts(dropna=False).to_string())

    print("\nDecisiones metodológicas:")
    print(df["decision"].value_counts(dropna=False).to_string())

    print(f"\nArchivo generado:\n- {OUT_FILE}\n")


def main() -> None:
    df = build_inventory()

    df.to_csv(OUT_FILE, index=False, encoding="utf-8-sig")

    build_console_summary(df)


if __name__ == "__main__":
    main()