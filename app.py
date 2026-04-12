"""
app.py – Entry point for PikaMC / Pterodactyl Python Egg.

Pterodactyl auto-installs requirements.txt, then runs this file.
No Node.js needed – frontend/build/ is pre-built and included in the repo.
"""
import subprocess
import sys
import os
import shutil

# ── Force sync with GitHub (fixes Pterodactyl git pull conflicts) ──
project_root = os.path.dirname(os.path.abspath(__file__))
backend_db_rel = os.path.join("backend", "pokemon_breeding.db")
backend_db_path = os.path.join(project_root, backend_db_rel)
backend_db_backup_path = backend_db_path + ".startup-backup"


def _backup_runtime_db():
    if os.path.exists(backend_db_path):
        shutil.copy2(backend_db_path, backend_db_backup_path)


def _restore_runtime_db_if_needed():
    if os.path.exists(backend_db_backup_path):
        shutil.move(backend_db_backup_path, backend_db_path)


if os.path.isdir(os.path.join(project_root, ".git")):
    print("==> Syncing code from GitHub...")
    try:
        _backup_runtime_db()

        fetch = subprocess.run(
            ["git", "fetch", "origin"],
            cwd=project_root,
            timeout=30,
            capture_output=True,
            text=True,
        )
        if fetch.returncode != 0:
            stderr = (fetch.stderr or "").strip()
            raise RuntimeError(f"git fetch failed: {stderr}")

        reset_main = subprocess.run(
            ["git", "reset", "--hard", "origin/main"],
            cwd=project_root,
            timeout=30,
            capture_output=True,
            text=True,
        )
        if reset_main.returncode != 0:
            reset_master = subprocess.run(
                ["git", "reset", "--hard", "origin/master"],
                cwd=project_root,
                timeout=30,
                capture_output=True,
                text=True,
            )
            if reset_master.returncode != 0:
                stderr_main = (reset_main.stderr or "").strip()
                stderr_master = (reset_master.stderr or "").strip()
                raise RuntimeError(
                    f"git reset failed for origin/main and origin/master. "
                    f"main_err={stderr_main} | master_err={stderr_master}"
                )

        # Keep seeded runtime DB after git reset, because the DB file is tracked in repo.
        _restore_runtime_db_if_needed()

        head = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=project_root,
            timeout=10,
            capture_output=True,
            text=True,
        )
        current_head = (head.stdout or "unknown").strip()
        print(f"==> Code synced successfully! HEAD={current_head}")
    except Exception as e:
        _restore_runtime_db_if_needed()
        print(f"==> Git sync failed. Running existing code. Reason: {e}")

# Get port from environment variable (Pterodactyl sets SERVER_PORT or PORT)
port = os.environ.get("SERVER_PORT") or os.environ.get("PORT") or "8000"

# Start FastAPI server from the backend directory
print(f"==> Starting Pokemon Breeding Calculator on port {port}...")
os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), "backend"))
subprocess.call([
    sys.executable, "-m", "uvicorn",
    "main:app",
    "--host", "0.0.0.0",
    "--port", str(port),
])
