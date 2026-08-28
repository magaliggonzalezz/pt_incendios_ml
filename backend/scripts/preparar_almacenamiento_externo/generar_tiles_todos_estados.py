from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description="Genera tiles web para una capa pesada en varios estados.")
    parser.add_argument("--capa", choices=["edafologia", "uso_suelo_vegetacion"], required=True)
    parser.add_argument("--desde-estado", type=int, default=1)
    parser.add_argument("--hasta-estado", type=int, default=32)
    parser.add_argument("--tolerancia", type=float, default=25.0)
    parser.add_argument("--grados", type=float, default=1.0)
    parser.add_argument("--recrear", action="store_true")
    args = parser.parse_args()

    script = Path(__file__).with_name("generar_tiles_capa_tematica.py")
    if not script.is_file():
        raise FileNotFoundError(script)

    for estado in range(args.desde_estado, args.hasta_estado + 1):
        cve = f"{estado:02d}"
        print(f"\n========== {args.capa} / estado {cve} ==========")
        cmd = [
            sys.executable,
            str(script),
            "--capa",
            args.capa,
            "--cve-ent",
            cve,
            "--tolerancia",
            str(args.tolerancia),
            "--grados",
            str(args.grados),
        ]
        if args.recrear:
            cmd.append("--recrear")
        subprocess.run(cmd, check=True)

    print("\nTODOS LOS ESTADOS SOLICITADOS TERMINARON CORRECTAMENTE")


if __name__ == "__main__":
    main()
