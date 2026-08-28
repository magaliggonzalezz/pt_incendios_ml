from __future__ import annotations

import argparse
import json
import mimetypes
import os
from pathlib import Path

try:
    import boto3
except ImportError as exc:
    raise SystemExit("Falta boto3. Instálalo con: python -m pip install boto3 python-dotenv") from exc

try:
    from dotenv import load_dotenv
except ImportError as exc:
    raise SystemExit("Falta python-dotenv. Instálalo con: python -m pip install boto3 python-dotenv") from exc


def cargar_configuracion(repo_root: Path) -> tuple[str, str, str, str]:
    env_path = repo_root / "backend" / "api-rest" / ".env"
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


def main() -> None:
    parser = argparse.ArgumentParser(description="Sube tiles web de una capa temática a R2.")
    parser.add_argument("--capa", choices=["edafologia", "uso_suelo_vegetacion"], required=True)
    parser.add_argument("--cve-ent", required=True)
    args = parser.parse_args()

    cve_ent = str(args.cve_ent).zfill(2)
    repo_root = Path(__file__).resolve().parents[3]
    carpeta = (
        repo_root
        / "data_deploy"
        / "capas_web"
        / "inegi"
        / "tiles"
        / args.capa
        / cve_ent
    )
    manifest_path = carpeta / "manifest.json"
    if not manifest_path.is_file():
        raise FileNotFoundError(f"No existe: {manifest_path}")

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    archivos = [manifest_path] + [carpeta / t["archivo"] for t in manifest.get("tiles", [])]
    faltantes = [str(p) for p in archivos if not p.is_file()]
    if faltantes:
        raise FileNotFoundError("Faltan archivos:\n- " + "\n- ".join(faltantes))

    endpoint, bucket, access_key, secret_key = cargar_configuracion(repo_root)
    s3 = boto3.client(
        "s3",
        endpoint_url=endpoint,
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        region_name="auto",
    )
    s3.head_bucket(Bucket=bucket)

    prefix = f"capas_web/inegi/tiles/{args.capa}/{cve_ent}"
    print(f"Bucket: {bucket}")
    print(f"Objetos a subir: {len(archivos)}")

    for i, path in enumerate(archivos, start=1):
        key = f"{prefix}/{path.name}"
        size = path.stat().st_size
        content_type = "application/json" if path.name == "manifest.json" else (
            mimetypes.guess_type(path.name)[0] or "application/geo+json"
        )
        print(f"[{i}/{len(archivos)}] {key}")
        s3.upload_file(str(path), bucket, key, ExtraArgs={"ContentType": content_type})
        remoto = s3.head_object(Bucket=bucket, Key=key)
        if int(remoto["ContentLength"]) != size:
            raise RuntimeError(f"Tamaño remoto inconsistente: {key}")

    print("\nTILES CARGADOS CORRECTAMENTE")
    print(f"Prefix: {prefix}")


if __name__ == "__main__":
    main()
