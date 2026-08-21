from __future__ import annotations

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


def cargar_configuracion() -> tuple[str, str, str, str]:
    repo_root = Path(__file__).resolve().parents[3]
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

    # Cloudflare puede mostrar el endpoint con /<bucket> al final. boto3 necesita
    # el endpoint de cuenta y el bucket se pasa por separado.
    sufijo_bucket = f"/{bucket}"
    if endpoint.endswith(sufijo_bucket):
        endpoint = endpoint[: -len(sufijo_bucket)]

    return endpoint, bucket, access_key, secret_key


def main() -> None:
    endpoint, bucket, access_key, secret_key = cargar_configuracion()

    s3 = boto3.client(
        "s3",
        endpoint_url=endpoint,
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        region_name="auto",
    )

    clave_prueba = "pruebas/conexion-r2.txt"
    contenido = b"Conexion OK entre pt_incendios_ml y Cloudflare R2.\n"

    print(f"Bucket: {bucket}")
    print(f"Endpoint: {endpoint}")
    print("\n[1/4] Verificando acceso al bucket...")
    s3.head_bucket(Bucket=bucket)
    print("  OK")

    print("[2/4] Subiendo objeto de prueba...")
    s3.put_object(
        Bucket=bucket,
        Key=clave_prueba,
        Body=contenido,
        ContentType="text/plain; charset=utf-8",
    )
    print(f"  OK: {clave_prueba}")

    print("[3/4] Leyendo objeto de prueba...")
    respuesta = s3.get_object(Bucket=bucket, Key=clave_prueba)
    recibido = respuesta["Body"].read()
    if recibido != contenido:
        raise RuntimeError("El contenido leído no coincide con lo que se subió.")
    print("  OK")

    print("[4/4] Eliminando objeto de prueba...")
    s3.delete_object(Bucket=bucket, Key=clave_prueba)
    print("  OK")

    print("\n===================================")
    print("R2 FUNCIONA CORRECTAMENTE")
    print("===================================")
    print("Se pudo acceder, subir, leer y eliminar un objeto.")
    print("No se dejó ningún archivo de prueba en el bucket.")


if __name__ == "__main__":
    main()
