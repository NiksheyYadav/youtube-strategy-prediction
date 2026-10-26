#!/usr/bin/env python3
"""One command to set up and start Signal Studio on any device (Windows, macOS, Linux).

    python scripts/launch.py            # interactive: asks before installing or downloading anything
    python scripts/launch.py --yes      # unattended: accept every install/download
    python scripts/launch.py --check    # print what would happen; change nothing
    python scripts/launch.py --no-llm   # skip the language model; rule-based advice only

It (1) creates ./venv and installs the pinned requirements, (2) detects RAM / NVIDIA VRAM and picks a model that
fits the device, (3) installs Ollama if needed, starts it and pulls the model plus a small lite fallback model,
then (4) starts the app.  Any problem with the language model never blocks the app: it falls back to rule-based advice.
Only the Python standard library is used here, so it runs before anything is installed.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import shutil
import subprocess
import sys
import threading
import time
import urllib.request
import webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.device_profile import CATALOG, DeviceProfile, allowed_models, detect_device  # noqa: E402  (stdlib-only module)

VENV = ROOT / "venv"
REQUIREMENTS = ROOT / "requirements-app.txt"
MARKER = VENV / ".requirements.sha256"
OLLAMA_API = "http://127.0.0.1:11434"
LITE_MODEL = "qwen2.5:0.5b"
MIN_PYTHON = (3, 10)


# --------------------------------------------------------------------------- #
# Pure helpers (unit-tested)
# --------------------------------------------------------------------------- #
def model_plan(profile: DeviceProfile) -> list[str]:
    """Models to have installed: the best one that fits the device, then the lite fallback."""
    allowed = allowed_models(profile)
    if not allowed:
        return []
    plan = [allowed[0].prefix]
    if LITE_MODEL not in plan:
        plan.append(LITE_MODEL)
    return plan


def missing_models(plan: list[str], installed: list[str]) -> list[str]:
    have = [name.lower() for name in installed]
    return [model for model in plan if not any(name.startswith(model.lower()) for name in have)]


def approx_size_gb(model: str) -> float:
    return next((m.size_gb for m in CATALOG if m.prefix == model), 2.0)


def ollama_candidates() -> list[Path]:
    paths = [shutil.which("ollama")]
    if os.name == "nt":
        local = os.environ.get("LOCALAPPDATA", "")
        paths.append(str(Path(local) / "Programs" / "Ollama" / "ollama.exe"))
    else:
        paths += ["/usr/local/bin/ollama", "/opt/homebrew/bin/ollama", "/usr/bin/ollama",
                  "/Applications/Ollama.app/Contents/Resources/ollama"]
    return [Path(p) for p in paths if p]


def find_ollama() -> Path | None:
    return next((p for p in ollama_candidates() if p.exists()), None)


def venv_python() -> Path:
    return VENV / ("Scripts/python.exe" if os.name == "nt" else "bin/python")


def requirements_hash() -> str:
    return hashlib.sha256(REQUIREMENTS.read_bytes()).hexdigest()


def deps_up_to_date() -> bool:
    return venv_python().exists() and MARKER.exists() and MARKER.read_text().strip() == requirements_hash()


def installed_models() -> list[str] | None:
    """Names of models in a running Ollama server, or None if no server answers."""
    try:
        with urllib.request.urlopen(f"{OLLAMA_API}/api/tags", timeout=2) as response:
            return [m["name"] for m in json.load(response).get("models", [])]
    except Exception:  # noqa: BLE001 - any failure means "not running"
        return None


# --------------------------------------------------------------------------- #
# Actions
# --------------------------------------------------------------------------- #
def say(message: str) -> None:
    print(f"[signal-studio] {message}", flush=True)


def confirm(question: str, assume_yes: bool) -> bool:
    if assume_yes:
        return True
    if not sys.stdin.isatty():
        return False
    return input(f"{question} [y/N] ").strip().lower() in {"y", "yes"}


def ensure_environment(assume_yes: bool) -> None:
    if not venv_python().exists():
        say("Creating virtual environment ./venv ...")
        subprocess.check_call([sys.executable, "-m", "venv", str(VENV)])
    if not deps_up_to_date():
        say("Installing pinned requirements (first run only; this can take a few minutes) ...")
        subprocess.check_call([str(venv_python()), "-m", "pip", "install", "-q", "--disable-pip-version-check", "-r", str(REQUIREMENTS)])
        MARKER.write_text(requirements_hash())


def install_ollama(assume_yes: bool) -> Path | None:
    system = platform.system()
    commands = {
        "Windows": (["winget", "install", "-e", "--id", "Ollama.Ollama", "--silent",
                     "--accept-package-agreements", "--accept-source-agreements"], shutil.which("winget"), "about 1.7 GB"),
        "Darwin": (["brew", "install", "ollama"], shutil.which("brew"), "about 0.1 GB (plus models)"),
        "Linux": (["sh", "-c", "curl -fsSL https://ollama.com/install.sh | sh"], shutil.which("curl"), "about 1.5 GB"),
    }
    command, available, size = commands.get(system, (None, None, ""))
    if not command or not available:
        say("Ollama is not installed and I cannot install it automatically here. Install it from https://ollama.com/download "
            "and run this script again. Continuing in rule-based mode.")
        return None
    if not confirm(f"Ollama (the local model runtime, {size}) is not installed. Install it now?", assume_yes):
        say("Skipping Ollama; the app will use rule-based advice.")
        return None
    say("Installing Ollama ...")
    if subprocess.call(command) != 0:
        say("Ollama installation failed; continuing in rule-based mode.")
        return None
    return find_ollama()


def start_server(ollama: Path) -> bool:
    if installed_models() is not None:
        return True
    say("Starting the Ollama server ...")
    flags = (subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP) if os.name == "nt" else 0  # type: ignore[attr-defined]
    subprocess.Popen([str(ollama), "serve"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                     creationflags=flags, start_new_session=(os.name != "nt"))
    for _ in range(40):
        if installed_models() is not None:
            return True
        time.sleep(1)
    return False


def setup_language_model(assume_yes: bool) -> None:
    profile = detect_device()
    plan = model_plan(profile)
    say(f"Device: {profile.describe()} (tier {profile.tier})")
    if not plan:
        say("This device is too small for a local language model; using rule-based advice.")
        return
    ollama = find_ollama() or install_ollama(assume_yes)
    if not ollama:
        return
    if not start_server(ollama):
        say("The Ollama server did not start; continuing in rule-based mode.")
        return
    todo = missing_models(plan, installed_models() or [])
    for model in todo:
        if confirm(f"Download model {model} (about {approx_size_gb(model):.1f} GB)?", assume_yes):
            say(f"Pulling {model} ...")
            if subprocess.call([str(ollama), "pull", model]) != 0:
                say(f"Could not download {model}; continuing without it.")
        else:
            say(f"Skipping {model}.")
    say("Language models ready: " + ", ".join(installed_models() or ["none"]))


def start_app(port: int, open_browser: bool) -> int:
    url = f"http://localhost:{port}"
    if open_browser:
        def opener() -> None:
            for _ in range(90):
                try:
                    urllib.request.urlopen(f"{url}/_stcore/health", timeout=2)
                    webbrowser.open(url)
                    return
                except Exception:  # noqa: BLE001
                    time.sleep(1)
        threading.Thread(target=opener, daemon=True).start()
    say(f"Starting Signal Studio at {url}  (press Ctrl+C to stop)")
    env = dict(os.environ, STREAMLIT_BROWSER_GATHER_USAGE_STATS="false")
    return subprocess.call([str(venv_python()), "-m", "streamlit", "run", str(ROOT / "app.py"), "--server.port", str(port),
                            "--server.headless", "true"], cwd=ROOT, env=env)


def check() -> None:
    profile = detect_device()
    plan = model_plan(profile)
    ollama = find_ollama()
    installed = installed_models()
    print(f"Python        : {platform.python_version()} (need {MIN_PYTHON[0]}.{MIN_PYTHON[1]}+)")
    print(f"Environment   : venv {'present' if venv_python().exists() else 'missing'}, requirements "
          f"{'up to date' if deps_up_to_date() else 'need installing'}")
    print(f"Device        : {profile.describe()} (tier {profile.tier})")
    print(f"Model plan    : {', '.join(plan) if plan else 'none (device too small; rule-based advice)'}")
    print(f"Ollama        : {'found at ' + str(ollama) if ollama else 'not installed'}; "
          f"server {'running' if installed is not None else 'not running'}")
    if plan:
        todo = missing_models(plan, installed or [])
        print(f"To download   : {', '.join(f'{m} (~{approx_size_gb(m):.1f} GB)' for m in todo) or 'nothing'}")
    print("Plan: nothing was changed (--check).")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--yes", action="store_true", help="accept every install and download without asking")
    parser.add_argument("--no-llm", action="store_true", help="skip the language model (rule-based advice only)")
    parser.add_argument("--no-browser", action="store_true", help="do not open the browser")
    parser.add_argument("--port", type=int, default=8501)
    parser.add_argument("--check", action="store_true", help="show the plan and change nothing")
    args = parser.parse_args()
    if sys.version_info < MIN_PYTHON:
        print(f"Python {MIN_PYTHON[0]}.{MIN_PYTHON[1]}+ is required (found {platform.python_version()}).", file=sys.stderr)
        return 2
    if args.check:
        check()
        return 0
    ensure_environment(args.yes)
    if not args.no_llm:
        try:
            setup_language_model(args.yes)
        except Exception as error:  # noqa: BLE001 - the language model must never block the app
            say(f"Language-model setup failed ({type(error).__name__}); continuing in rule-based mode.")
    return start_app(args.port, not args.no_browser)


if __name__ == "__main__":
    raise SystemExit(main())
