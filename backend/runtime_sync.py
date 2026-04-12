"""
runtime_sync.py

Automates post-pull runtime tasks on low-resource hosts:
- optional Smogon build seeding
- optional move learning seeding

It stores a lightweight sync state and skips reruns when the git commit
has not changed.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path


STATE_FILE = Path(__file__).resolve().parent / "data" / "runtime_sync_state.json"


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _get_git_head(project_root: Path) -> str:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=project_root,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        value = (result.stdout or "").strip()
        return value or "no-git"
    except Exception:
        return "no-git"


def _load_state() -> dict:
    if not STATE_FILE.exists():
        return {}
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _save_state(state: dict) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def _run_script(script_name: str, args: list[str], backend_dir: Path, timeout_sec: int) -> tuple[bool, str]:
    script_path = backend_dir / script_name
    if not script_path.exists():
        return False, f"missing-script:{script_name}"

    cmd = [sys.executable, str(script_path), *args]
    try:
        proc = subprocess.run(
            cmd,
            cwd=backend_dir,
            capture_output=True,
            text=True,
            timeout=timeout_sec,
            check=False,
        )
        if proc.returncode != 0:
            err = (proc.stderr or proc.stdout or "unknown-error").strip()
            return False, err[-1200:]
        out = (proc.stdout or "ok").strip()
        return True, out[-1200:]
    except subprocess.TimeoutExpired:
        return False, f"timeout:{script_name}"
    except Exception as exc:
        return False, str(exc)


def run_runtime_sync(reason: str = "startup", force: bool = False) -> dict:
    """
    Execute runtime synchronization tasks after startup/pull.

    Env flags:
    - AUTO_RUNTIME_SYNC=1/0
    - AUTO_SMOGON_SYNC=1/0
    - AUTO_SMOGON_FROM_INDEX=1/0
    - AUTO_SMOGON_FORMATS=gen9ou,gen9monotype
    - AUTO_MOVE_SYNC=1/0
    - AUTO_MOVE_SYNC_ALL=1/0
    - AUTO_MOVE_SYNC_LIMIT=1025
    - AUTO_RUNTIME_SYNC_TIMEOUT_SEC=1800
    """
    enabled = _env_bool("AUTO_RUNTIME_SYNC", True)
    if not enabled and not force:
        return {"status": "skipped", "reason": "AUTO_RUNTIME_SYNC=0"}

    backend_dir = Path(__file__).resolve().parent
    project_root = backend_dir.parent
    head = _get_git_head(project_root)
    state = _load_state()

    if not force and state.get("last_success_head") == head:
        return {"status": "skipped", "reason": "head-unchanged", "head": head}

    timeout_sec = int(os.getenv("AUTO_RUNTIME_SYNC_TIMEOUT_SEC", "1800"))

    result = {
        "status": "ok",
        "reason": reason,
        "head": head,
        "steps": [],
        "timestamp": int(time.time()),
    }

    if _env_bool("AUTO_SMOGON_SYNC", True):
        if _env_bool("AUTO_SMOGON_FROM_INDEX", False):
            smogon_args = ["--from-index"]
        else:
            formats = os.getenv("AUTO_SMOGON_FORMATS", "gen9ou,gen9monotype").strip()
            smogon_args = ["--formats", formats]

        ok, detail = _run_script("seed_smogon_builds.py", smogon_args, backend_dir, timeout_sec)
        result["steps"].append({"name": "smogon", "ok": ok, "detail": detail})
        if not ok:
            result["status"] = "error"

    if _env_bool("AUTO_MOVE_SYNC", True):
        if _env_bool("AUTO_MOVE_SYNC_ALL", True):
            move_args = ["--all"]
        else:
            limit = os.getenv("AUTO_MOVE_SYNC_LIMIT", "1025").strip()
            move_args = ["--limit", limit]

        ok, detail = _run_script("seed_pokemon_moves.py", move_args, backend_dir, timeout_sec)
        result["steps"].append({"name": "move-sync", "ok": ok, "detail": detail})
        if not ok:
            result["status"] = "error"

    if result["status"] == "ok":
        state["last_success_head"] = head
        state["last_success_reason"] = reason
        state["last_success_at"] = result["timestamp"]
        state["last_steps"] = result["steps"]
        _save_state(state)

    return result
