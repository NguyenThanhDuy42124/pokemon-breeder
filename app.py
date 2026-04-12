"""
app.py – Entry point for PikaMC / Pterodactyl Python Egg.

Pterodactyl auto-installs requirements.txt, then runs this file.
No Node.js needed – frontend/build/ is pre-built and included in the repo.
"""
import subprocess
import sys
import os

# ── Force sync with GitHub (fixes Pterodactyl git pull conflicts) ──
project_root = os.path.dirname(os.path.abspath(__file__))
if os.path.isdir(os.path.join(project_root, ".git")):
    print("==> Syncing code from GitHub...")
    try:
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
