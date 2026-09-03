from __future__ import annotations

import argparse
import os
from pathlib import Path

import boto3
from botocore.exceptions import ClientError
from dotenv import load_dotenv


LOCAL_RELATIVE = Path("data_deploy/capas_web/inegi/elevacion_mde")
PREFIX = "capas_web/inegi/elevacion_mde"


def encontrar_raiz(inicio: Path) -> Path:
    for candidato in [inicio.resolve(), *inicio.resolve().parents]:
        if (candidato / LOCAL_RELATIVE / "manifest.json").is_file():
            return candidato
    raise FileNotFoundError(
        "No se encontró data_deploy/capas_web/inegi/elevacion_mde/manifest.json"
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


def tamano_remoto(s3, bucket: str, key: str) -> int | None:
    try:
        return int(s3.head_object(Bucket=bucket, Key=key)["ContentLength"])
    except ClientError as exc:
        codigo = str(exc.response.get("Error", {}).get("Code", ""))
        if codigo in {"404", "NoSuchKey", "NotFound"}:
            return None
        raise


def content_type(path: Path) -> str:
    if path.suffix.lower() == ".png":
        return "image/png"
    if path.suffix.lower() == ".json":
        return "application/json; charset=utf-8"
    return "application/octet-stream"


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Verifica y sube a R2 los tiles de elevación MDE INEGI."
    )
    parser.add_argument("--solo-verificar", action="store_true")
    args = parser.parse_args()

    raiz = encontrar_raiz(Path.cwd())
    carpeta = raiz / LOCAL_RELATIVE
    archivos = sorted(path for path in carpeta.rglob("*") if path.is_file())
    if not archivos:
        raise RuntimeError("No hay archivos de elevación para subir")

    endpoint, bucket, access_key, secret_key = cargar_configuracion(raiz)
    s3 = boto3.client(
        "s3",
        endpoint_url=endpoint,
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        region_name="auto",
    )
    s3.head_bucket(Bucket=bucket)

    correctos = 0
    pendientes = 0
    subidos = 0

    print(f"Bucket: {bucket}")
    print(f"Prefix: {PREFIX}")
    print(f"Archivos locales: {len(archivos):,}")
    print("Modo: SOLO VERIFICACIÓN" if args.solo_verificar else "Modo: VERIFICAR + SUBIR")

    for index, path in enumerate(archivos, 1):
        relative = path.relative_to(carpeta).as_posix()
        key = f"{PREFIX}/{relative}"
        local_size = path.stat().st_size
        remote_size = tamano_remoto(s3, bucket, key)

        if remote_size == local_size:
            correctos += 1
            continue

        pendientes += 1
        if args.solo_verificar:
            continue

        s3.upload_file(
            str(path),
            bucket,
            key,
            ExtraArgs={"ContentType": content_type(path)},
        )
        verified = tamano_remoto(s3, bucket, key)
        if verified != local_size:
            raise RuntimeError(f"Tamaño remoto inconsistente: {key}")
        subidos += 1

        if index % 250 == 0 or index == len(archivos):
            print(f"  {index:,}/{len(archivos):,}", end="\r")

    print("\n=== RESUMEN ===")
    print(f"Correctos en R2: {correctos:,}")
    print(f"Pendientes detectados: {pendientes:,}")
    print(f"Subidos/reemplazados: {subidos:,}")

    if args.solo_verificar and pendientes:
        print("Ejecuta de nuevo sin --solo-verificar para subirlos.")
    elif not args.solo_verificar:
        print("ELEVACIÓN MDE VERIFICADA EN R2")


if __name__ == "__main__":
    main()
