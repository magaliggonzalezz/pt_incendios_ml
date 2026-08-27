from __future__ import annotations

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
    if not env_path.is_file():
        raise FileNotFoundError(f"No existe el archivo .env esperado: {env_path}")

    load_dotenv(env_path)

    endpoint = os.getenv("R2_ENDPOINT", "").strip().rstrip("/")
    bucket = os.getenv("R2_BUCKET", "").strip()
    access_key = os.getenv("R2_ACCESS_KEY_ID", "").strip()
    secret_key = os.getenv("R2_SECRET_ACCESS_KEY", "").strip()

    faltantes = [
        nombre
        for nombre, valor in [
            ("R2_ENDPOINT", endpoint),
            ("R2_BUCKET", bucket),
            ("R2_ACCESS_KEY_ID", access_key),
            ("R2_SECRET_ACCESS_KEY", secret_key),
        ]
        if not valor
    ]
    if faltantes:
        raise RuntimeError(
            "Faltan variables en backend/api-rest/.env: " + ", ".join(faltantes)
        )

    sufijo_bucket = f"/{bucket}"
    if endpoint.endswith(sufijo_bucket):
        endpoint = endpoint[: -len(sufijo_bucket)]

    return endpoint, bucket, access_key, secret_key


def tipo_contenido(path: Path) -> str:
    return mimetypes.guess_type(path.name)[0] or "application/geo+json"


def main() -> None:
    repo_root = Path(__file__).resolve().parents[3]
    base = repo_root / "data_deploy" / "capas_web"

    entidades = base / "inegi" / "inegi_entidades.geojson"
    municipios_dir = base / "inegi" / "municipios"
    smn = base / "smn" / "smn_estaciones.geojson"

    municipios = sorted(municipios_dir.glob("inegi_municipios_*.geojson"))
    if not entidades.is_file():
        raise FileNotFoundError(f"Falta {entidades}")
    if len(municipios) != 32:
        raise RuntimeError(
            f"Se esperaban 32 archivos municipales por entidad y se encontraron {len(municipios)}"
        )
    if not smn.is_file():
        raise FileNotFoundError(f"Falta {smn}")

    endpoint, bucket, access_key, secret_key = cargar_configuracion(repo_root)
    s3 = boto3.client(
        "s3",
        endpoint_url=endpoint,
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        region_name="auto",
    )

    objetos: list[tuple[Path, str]] = [
        (entidades, "capas_web/inegi/inegi_entidades.geojson"),
        *[
            (path, f"capas_web/inegi/municipios/{path.name}")
            for path in municipios
        ],
        (smn, "capas_web/smn/smn_estaciones.geojson"),
    ]

    total = sum(path.stat().st_size for path, _ in objetos)

    print(f"Bucket: {bucket}")
    print(f"Objetos a subir: {len(objetos)}")
    print(f"Tamaño total: {bytes_legibles(total)}\n")

    s3.head_bucket(Bucket=bucket)

    for i, (path, key) in enumerate(objetos, start=1):
        local_size = path.stat().st_size
        print(f"[{i}/{len(objetos)}] {key} | {bytes_legibles(local_size)}")

        s3.upload_file(
            str(path),
            bucket,
            key,
            ExtraArgs={"ContentType": tipo_contenido(path)},
        )

        remoto = s3.head_object(Bucket=bucket, Key=key)
        remoto_size = int(remoto["ContentLength"])
        if remoto_size != local_size:
            raise RuntimeError(
                f"Tamaño inconsistente para {key}: local={local_size}, remoto={remoto_size}"
            )

    print("\n====================================")
    print("CAPAS WEB BASE CARGADAS A R2")
    print("====================================")
    print(f"Objetos verificados: {len(objetos)}")
    print(f"Total cargado:       {bytes_legibles(total)}")
    print("Keys principales:")
    print("- capas_web/inegi/inegi_entidades.geojson")
    print("- capas_web/inegi/municipios/inegi_municipios_01.geojson ... _32.geojson")
    print("- capas_web/smn/smn_estaciones.geojson")


if __name__ == "__main__":
    main()
