from __future__ import annotations

import argparse
import mimetypes
import os
from pathlib import Path

try:
    import boto3
except ImportError as exc:
    raise SystemExit(
        "Falta boto3. Instálalo con: python -m pip install boto3 python-dotenv"
    ) from exc

try:
    from dotenv import load_dotenv
except ImportError as exc:
    raise SystemExit(
        "Falta python-dotenv. Instálalo con: python -m pip install boto3 python-dotenv"
    ) from exc


CAPAS = ["fisiografia", "edafologia", "hidrografia", "uso_suelo_vegetacion"]


def bytes_legibles(num_bytes: int) -> str:
    unidades = ["B", "KiB", "MiB", "GiB"]
    valor = float(num_bytes)
    for unidad in unidades:
        if valor < 1024 or unidad == unidades[-1]:
            return f"{valor:.2f} {unidad}"
        valor /= 1024
    return f"{num_bytes} B"


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
    parser = argparse.ArgumentParser(description="Sube a R2 las particiones temáticas ya preparadas.")
    parser.add_argument("--capa", choices=[*CAPAS, "todas"], required=True)
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[3]
    base = repo_root / "data_deploy" / "capas_web" / "inegi" / "tematicas"
    capas = CAPAS if args.capa == "todas" else [args.capa]

    endpoint, bucket, access_key, secret_key = cargar_configuracion(repo_root)
    s3 = boto3.client(
        "s3",
        endpoint_url=endpoint,
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        region_name="auto",
    )
    s3.head_bucket(Bucket=bucket)

    objetos = []
    for capa in capas:
        carpeta = base / capa
        archivos = sorted(carpeta.glob(f"{capa}_*.geojson"))
        if len(archivos) != 32:
            raise RuntimeError(
                f"{capa}: se esperaban 32 particiones y se encontraron {len(archivos)}. "
                "Ejecuta primero particionar_capas_tematicas_por_estado.py."
            )
        objetos.extend(
            (path, f"capas_web/inegi/tematicas/{capa}/{path.name}") for path in archivos
        )

    total = sum(path.stat().st_size for path, _ in objetos)
    print(f"Bucket: {bucket}")
    print(f"Objetos a subir: {len(objetos)}")
    print(f"Tamaño total: {bytes_legibles(total)}\n")

    for i, (path, key) in enumerate(objetos, start=1):
        size = path.stat().st_size
        print(f"[{i}/{len(objetos)}] {key} | {bytes_legibles(size)}")
        s3.upload_file(
            str(path),
            bucket,
            key,
            ExtraArgs={"ContentType": mimetypes.guess_type(path.name)[0] or "application/geo+json"},
        )
        remoto = s3.head_object(Bucket=bucket, Key=key)
        if int(remoto["ContentLength"]) != size:
            raise RuntimeError(f"Tamaño remoto inconsistente: {key}")

    print("\nCAPAS TEMÁTICAS CARGADAS CORRECTAMENTE")
    print(f"Objetos verificados: {len(objetos)}")
    print(f"Total cargado: {bytes_legibles(total)}")


if __name__ == "__main__":
    main()
