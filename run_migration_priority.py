"""
Ejecuta migraciones en el orden de prioridad solicitado:
1) imperio (imp)
2) escuelas elementales (esc)
3) pe
4) extra
5) imp_r (restante, excluyendo esc)

Uso recomendado:
    python run_migration_priority.py --max-ok 150 --max-bytes 268435456

Notas:
- El script NO hardcodea credenciales. Usa variables de entorno.
- Mantiene topes por etapa para evitar sobrepasar cupo de Cloudinary.
"""

import argparse
import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent
PYTHON = sys.executable


def _run_step(name: str, command: list[str], env: dict[str, str]) -> int:
    print("\n" + "=" * 72)
    print(f"[STEP] {name}")
    print("Command:", " ".join(command))
    print("=" * 72)
    proc = subprocess.run(command, cwd=str(ROOT), env=env)
    return proc.returncode


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="No sube nada; solo valida scopes")
    parser.add_argument("--max-ok", type=int, default=150, help="Tope de uploads por etapa MYL")
    parser.add_argument(
        "--max-bytes",
        type=int,
        default=268435456,
        help="Tope de bytes por etapa MYL (default 256MB)",
    )
    parser.add_argument("--workers", type=int, default=1, help="Workers para migradores (default 1)")
    parser.add_argument(
        "--continue-on-error",
        action="store_true",
        help="Si una etapa falla, continua con la siguiente",
    )
    args = parser.parse_args()

    env = os.environ.copy()
    env.setdefault("CDN_PROVIDER", "cloudinary")

    steps = [
        (
            "Imperio (imp)",
            [
                PYTHON,
                "migrate_myl_to_cloudinary.py",
                "--scope",
                "imp",
                "--workers",
                str(args.workers),
            ],
        ),
        (
            "Escuelas Elementales (esc)",
            [
                PYTHON,
                "migrate_myl_to_cloudinary.py",
                "--scope",
                "esc",
                "--workers",
                str(args.workers),
            ],
        ),
        (
            "PE (pe)",
            [
                PYTHON,
                "migrate_myl_to_cloudinary.py",
                "--scope",
                "pe",
                "--workers",
                str(args.workers),
            ],
        ),
        (
            "Cartas extra",
            [
                PYTHON,
                "upload_to_cloudinary.py",
            ],
        ),
        (
            "IMP_R final (sin ESC)",
            [
                PYTHON,
                "migrate_myl_to_cloudinary.py",
                "--scope",
                "imp_r",
                "--exclude-esc-from-imp-r",
                "--workers",
                str(args.workers),
            ],
        ),
    ]

    # Inject safe caps into MYL steps (the ones using migrate_myl_to_cloudinary.py).
    for idx, (name, cmd) in enumerate(steps):
        if "migrate_myl_to_cloudinary.py" in cmd:
            if args.dry_run:
                cmd.append("--dry-run")
            else:
                cmd.extend(["--max-ok", str(args.max_ok), "--max-bytes", str(args.max_bytes)])
        elif args.dry_run:
            # Non-MYL steps have no dry-run mode; skip them safely.
            steps[idx] = (name, [])
            continue
        steps[idx] = (name, cmd)

    failures = 0
    for name, cmd in steps:
        if not cmd:
            print(f"[SKIP] {name} (sin modo dry-run)")
            continue
        step_env = env.copy()
        if not args.dry_run:
            # Apply hard caps to every stage that uses cdn_uploader.
            step_env["CDN_MAX_UPLOAD_CALLS"] = str(args.max_ok)
            step_env["CDN_MAX_UPLOAD_BYTES"] = str(args.max_bytes)

        code = _run_step(name, cmd, step_env)
        if code != 0:
            failures += 1
            print(f"[ERROR] Etapa fallo ({name}) con exit code {code}")
            if not args.continue_on_error:
                print("[STOP] Corta ejecucion por seguridad.")
                return code

    if failures:
        print(f"\n[WARN] Finalizo con {failures} etapas con error.")
        return 1

    print("\n[OK] Migracion por prioridad completada.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
