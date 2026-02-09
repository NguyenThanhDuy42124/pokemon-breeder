"""
start.py – Entry point for PikaMC / Pterodactyl Python Egg hosting.

This script:
1. Installs Python dependencies from requirements.txt
2. Starts the FastAPI server via uvicorn

No Node.js needed – frontend/build/ is pre-built and included in the repo.
"""
import subprocess
import sys
import os

# Install dependencies
req_file = os.path.join(os.path.dirname(__file__), "backend", "requirements.txt")
if os.path.exists(req_file):
    print("==> Installing Python dependencies...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", req_file])

# Get port from environment variable (Pterodactyl sets SERVER_PORT or PORT)
port = os.environ.get("SERVER_PORT") or os.environ.get("PORT") or "8000"

# Start FastAPI server
print(f"==> Starting Pokemon Breeding Calculator on port {port}...")
os.chdir(os.path.join(os.path.dirname(__file__), "backend"))
subprocess.call([
    sys.executable, "-m", "uvicorn",
    "main:app",
    "--host", "0.0.0.0",
    "--port", str(port),
])
