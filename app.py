"""
app.py – Entry point for PikaMC / Pterodactyl Python Egg.

Pterodactyl auto-installs requirements.txt, then runs this file.
No Node.js needed – frontend/build/ is pre-built and included in the repo.
"""
import subprocess
import sys
import os

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
