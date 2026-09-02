from __future__ import annotations

import argparse
import os
from pathlib import Path

import boto3
from botocore.exceptions import ClientError
from dotenv import load_dotenv


PREFIX = "exportaciones/municipio_dia_detalle"
EXPECTED_YEARS = list(range(2001, 2026))


def encontrar_raiz(inicio: Path) -> Path:
    for candidato in [inicio.resolve(), *inicio.resolve().parents]:
        carpeta = candidato / "data_deploy" / "exportaciones" / "municipio_dia_detalle"
        if carpeta.exists():
            return candidato
    raise FileNotFoundError(
        "No se encontró data_deploy/exportaciones/municipio_dia_detalle"
    )


def cargar_configuracion(raiz: Path) -> tuple[str, str, str, str]:
    env_path = raiz / "backend" / "api-rest" / ".env"
    if not env_path.is_file():
        raise FileNotFoundError(f"No existe el archivo .env esperado: {env_path}")

    load_dotenv(env_path)

    endpoint = os.getenv("R2_ENDPOINT", "").strip().rstrip("/")
    bucket = os.getenv("R2_BUCKET", "").strip()
    access_key = os.getenv("R2_ACCESS_KEY_ID", "").strip()
    secret_key = os.getenv("R2_SECRET_ACCESS_KEY", "").strip()

    if endpoint.endswith(f"/{bucket}"):
        endpoint = endpoint[: -(len(bucket) + 1)]

    if not all([endpoint, bucket, access_key, secret_key]):
        raise RuntimeError("Falta configuración R2 en backend/api-rest/.env")

    return endpoint, bucket, access_key, secret_key


def archivos_exportacion(carpeta: Path) -> list[Path]:
    archivos = sorted(carpeta.glob("app_municipio_dia_detalle_exportacion_*.parquet"))
    encontrados = []

    for path in archivos:
        try:
            encontrados.append(int(path.stem.rsplit("_", 1)[-1]))
        except ValueError as exc:
            raise RuntimeError(f"Nombre de archivo inesperado: {path.name}") from exc

    if encontrados != EXPECTED_YEARS:
        faltantes = sorted(set(EXPECTED_YEARS) - set(encontrados))
        extras = sorted(set(encontrados) - set(EXPECTED_YEARS))
        raise RuntimeError(
            "Se esperaban exactamente los 25 Parquet de 2001 a 2025. "
            f"Faltantes: {faltantes or 'ninguno'}; extras: {extras or 'ninguno'}"
        )

    return archivos


def obtener_tamano_remoto(s3, bucket: str, key: str) -> int | None:
    try:
        respuesta = s3.head_object(Bucket=bucket, Key=key)
        return int(respuesta["ContentLength"])
    except ClientError as exc:
        codigo = str(exc.response.get("Error", {}).get("Code", ""))
        if codigo in {"404", "NoSuchKey", "NotFound"}:
            return None
        raise


def formato_bytes(value: int) -> str:
    units = ["B", "KiB", "MiB", "GiB"]
    size = float(value)
    index = 0
    while size >= 1024 and index < len(units) - 1:
        size /= 1024
        index += 1
    return f"{size:.2f} {units[index]}"


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Verifica y sube a Cloudflare R2 los Parquet de exportación detallada "
            "municipio-día. Omite objetos remotos cuyo tamaño ya coincide."
        )
    )
    parser.add_argument(
        "--solo-verificar",
        action="store_true",
        help="No sube archivos; únicamente compara los 25 objetos locales contra R2.",
    )
    args = parser.parse_args()

    raiz = encontrar_raiz(Path.cwd())
    carpeta = raiz / "data_deploy" / "exportaciones" / "municipio_dia_detalle"
    archivos = archivos_exportacion(carpeta)
    endpoint, bucket, access_key, secret_key = cargar_configuracion(raiz)

    s3 = boto3.client(
        "s3",
        endpoint_url=endpoint,
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        region_name="auto",
    )
    s3.head_bucket(Bucket=bucket)

    total_local = sum(path.stat().st_size for path in archivos)
    existentes = 0
    faltantes = 0
    diferentes = 0
    subidos = 0

    print(f"Bucket: {bucket}")
    print(f"Prefix: {PREFIX}")
    print(f"Parquet locales: {len(archivos)}")
    print(f"Tamaño local total: {formato_bytes(total_local)}")
    if args.solo_verificar:
        print("Modo: SOLO VERIFICACIÓN\n")
    else:
        print("Modo: VERIFICAR + SUBIR FALTANTES/DIFERENTES\n")

    for index, path in enumerate(archivos, 1):
        key = f"{PREFIX}/{path.name}"
        local_size = path.stat().st_size
        remote_size = obtener_tamano_remoto(s3, bucket, key)

        if remote_size == local_size:
            existentes += 1
            print(f"[{index:02d}/25] OK       {key} ({formato_bytes(local_size)})")
            continue

        if remote_size is None:
            faltantes += 1
            estado = "FALTANTE"
        else:
            diferentes += 1
            estado = f"DIFERENTE remoto={formato_bytes(remote_size)} local={formato_bytes(local_size)}"

        if args.solo_verificar:
            print(f"[{index:02d}/25] {estado}  {key}")
            continue

        print(f"[{index:02d}/25] SUBIENDO  {key} ({estado})")
        s3.upload_file(
            str(path),
            bucket,
            key,
            ExtraArgs={"ContentType": "application/octet-stream"},
        )

        verified_size = obtener_tamano_remoto(s3, bucket, key)
        if verified_size != local_size:
            raise RuntimeError(
                f"Tamaño remoto inconsistente después de subir {key}: "
                f"local={local_size}, remoto={verified_size}"
            )
        subidos += 1
        print("           OK")

    print("\n=== RESUMEN ===")
    print(f"Ya correctos en R2: {existentes}")
    print(f"Faltantes detectados: {faltantes}")
    print(f"Con tamaño distinto: {diferentes}")
    print(f"Subidos/reemplazados: {subidos}")

    if args.solo_verificar and (faltantes or diferentes):
        print("\nHay objetos pendientes. Ejecuta de nuevo sin --solo-verificar para subirlos.")
    elif not args.solo_verificar:
        print("\nEXPORTACIONES MUNICIPIO-DÍA VERIFICADAS EN R2")


if __name__ == "__main__":
    main()
