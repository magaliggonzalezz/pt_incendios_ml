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
    unidades = ["B", "KiB", "MiB", "GiB", "TiB"]
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
    if path.suffix.lower() == ".parquet":
        return "application/vnd.apache.parquet"
    return mimetypes.guess_type(path.name)[0] or "application/octet-stream"


def main() -> None:
    repo_root = Path(__file__).resolve().parents[3]
    data_deploy = repo_root / "data_deploy"

    endpoint, bucket, access_key, secret_key = cargar_configuracion(repo_root)

    muestra = [
        (
            data_deploy
            / "resultados"
            / "municipio_dia"
            / "app_municipio_dia_resultados_2025.parquet",
            "resultados/municipio_dia/app_municipio_dia_resultados_2025.parquet",
        ),
        (
            data_deploy / "fuentes" / "firms" / "firms_detecciones.parquet",
            "fuentes/firms/firms_detecciones.parquet",
        ),
        (
            data_deploy / "fuentes" / "conafor" / "conafor_incendios_eventos.parquet",
            "fuentes/conafor/conafor_incendios_eventos.parquet",
        ),
        (
            data_deploy / "contexto" / "inegi_contexto_municipal.parquet",
            "contexto/inegi_contexto_municipal.parquet",
        ),
        (
            data_deploy / "capas_web" / "smn" / "smn_estaciones.geojson",
            "capas_web/smn/smn_estaciones.geojson",
        ),
    ]

    faltantes = [str(path) for path, _ in muestra if not path.is_file()]
    if faltantes:
        raise FileNotFoundError(
            "Faltan archivos de la muestra en data_deploy:\n- " + "\n- ".join(faltantes)
        )

    s3 = boto3.client(
        "s3",
        endpoint_url=endpoint,
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        region_name="auto",
    )

    print(f"Bucket: {bucket}")
    print(f"Endpoint: {endpoint}")
    print("\nVerificando acceso...")
    s3.head_bucket(Bucket=bucket)
    print("  OK\n")

    total = sum(path.stat().st_size for path, _ in muestra)
    print(f"Archivos de muestra: {len(muestra)}")
    print(f"Tamaño total: {bytes_legibles(total)}\n")

    for indice, (path, key) in enumerate(muestra, start=1):
        size = path.stat().st_size
        print(f"[{indice}/{len(muestra)}] {key}")
        print(f"  Local: {bytes_legibles(size)}")

        s3.upload_file(
            str(path),
            bucket,
            key,
            ExtraArgs={"ContentType": tipo_contenido(path)},
        )

        remoto = s3.head_object(Bucket=bucket, Key=key)
        remoto_size = int(remoto["ContentLength"])
        if remoto_size != size:
            raise RuntimeError(
                f"Tamaño remoto incorrecto para {key}: local={size}, remoto={remoto_size}"
            )

        print(f"  R2:    {bytes_legibles(remoto_size)}")
        print("  OK\n")

    print("===================================")
    print("MUESTRA R2 CARGADA CORRECTAMENTE")
    print("===================================")
    print(f"Objetos subidos: {len(muestra)}")
    print(f"Total cargado:   {bytes_legibles(total)}")
    print("\nLos archivos quedan en el bucket para la siguiente prueba con la API.")


if __name__ == "__main__":
    main()
