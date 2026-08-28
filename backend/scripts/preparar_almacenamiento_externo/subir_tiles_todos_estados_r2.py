from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Sube a R2 los tiles ya generados de una capa temática para varios estados."
    )
    parser.add_argument("--capa", choices=["edafologia", "uso_suelo_vegetacion"], required=True)
    parser.add_argument("--desde-estado", type=int, default=1)
    parser.add_argument("--hasta-estado", type=int, default=32)
    args = parser.parse_args()

    if not (1 <= args.desde_estado <= args.hasta_estado <= 32):
        raise ValueError("El rango de estados debe estar entre 1 y 32")

    script = Path(__file__).with_name("subir_tiles_capa_tematica_r2.py")
    if not script.is_file():
        raise FileNotFoundError(script)

    for estado in range(args.desde_estado, args.hasta_estado + 1):
        cve = f"{estado:02d}"
        print(f"\n========== SUBIDA {args.capa} / estado {cve} ==========")
        cmd = [
            sys.executable,
            str(script),
            "--capa",
            args.capa,
            "--cve-ent",
            cve,
        ]
        subprocess.run(cmd, check=True)

    print("\nTODOS LOS ESTADOS SOLICITADOS SE SUBIERON CORRECTAMENTE")


if __name__ == "__main__":
    main()
