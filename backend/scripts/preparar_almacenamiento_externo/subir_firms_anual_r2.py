from __future__ import annotations

import os
from pathlib import Path

import boto3
from dotenv import load_dotenv


def encontrar_raiz(inicio: Path) -> Path:
    for candidato in [inicio.resolve(), *inicio.resolve().parents]:
        if (candidato / "data_deploy" / "capas_web" / "puntos" / "firms").exists():
            return candidato
    raise FileNotFoundError("No se encontró data_deploy/capas_web/puntos/firms")


def main() -> None:
    raiz = encontrar_raiz(Path.cwd())
    load_dotenv(raiz / "backend" / "api-rest" / ".env")

    endpoint = os.getenv("R2_ENDPOINT", "").strip().rstrip("/")
    bucket = os.getenv("R2_BUCKET", "").strip()
    access_key = os.getenv("R2_ACCESS_KEY_ID", "").strip()
    secret_key = os.getenv("R2_SECRET_ACCESS_KEY", "").strip()
    if endpoint.endswith(f"/{bucket}"):
        endpoint = endpoint[: -(len(bucket) + 1)]
    if not all([endpoint, bucket, access_key, secret_key]):
        raise RuntimeError("Falta configuración R2 en backend/api-rest/.env")

    carpeta = raiz / "data_deploy" / "capas_web" / "puntos" / "firms"
    archivos = sorted(carpeta.glob("firms_detecciones_*.parquet"))
    manifest = carpeta / "manifest.json"
    if len(archivos) != 25 or not manifest.is_file():
        raise RuntimeError("Se esperaban 25 Parquet anuales FIRMS y manifest.json")

    s3 = boto3.client(
        "s3",
        endpoint_url=endpoint,
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        region_name="auto",
    )
    s3.head_bucket(Bucket=bucket)

    objetos = [(manifest, "capas_web/puntos/firms/manifest.json")]
    objetos += [
        (path, f"capas_web/puntos/firms/{path.name}")
        for path in archivos
    ]

    print(f"Bucket: {bucket}")
    print(f"Objetos a subir: {len(objetos)}")
    for i, (path, key) in enumerate(objetos, 1):
        print(f"[{i}/{len(objetos)}] {key}")
        content_type = "application/json" if path.suffix == ".json" else "application/octet-stream"
        s3.upload_file(str(path), bucket, key, ExtraArgs={"ContentType": content_type})
        remoto = s3.head_object(Bucket=bucket, Key=key)
        if int(remoto["ContentLength"]) != path.stat().st_size:
            raise RuntimeError(f"Tamaño remoto inconsistente: {key}")

    print("\nFIRMS ANUAL CARGADO CORRECTAMENTE")
    print("Prefix: capas_web/puntos/firms")


if __name__ == "__main__":
    main()
