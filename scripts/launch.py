#!/usr/bin/env python3
"""One command to set up and start Signal Studio on any device (Windows, macOS, Linux).

    python scripts/launch.py            # interactive: asks before installing or downloading anything
    python scripts/launch.py --yes      # unattended: accept every install/download
    python scripts/launch.py --check    # print what would happen; change nothing
    python scripts/launch.py --no-llm   # skip the language model; rule-based advice only
    python scripts/launch.py --model qwen2.5:7b   # use a specific model from the catalog instead of the automatic choice
    python scripts/launch.py --lan      # let other devices on your network open the app (default: this computer only)

It (1) creates ./venv and installs the pinned requirements, (2) detects RAM / NVIDIA VRAM and picks a model that
fits the device, (3) installs Ollama if needed, starts it and pulls the model plus a small lite fallback model
(then checks that each downloaded model really answers), then (4) starts the app with the settings from ./.env.
Any problem with the language model never blocks the app: it falls back to rule-based advice.
Only the Python standard library is used here, so it runs before anything is installed.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import shutil
import socket
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
from src.env_file import ENV_PATH, load_env_file  # noqa: E402  (stdlib-only module)

VENV = ROOT / "venv"
REQUIREMENTS = ROOT / "requirements-app.txt"
MARKER = VENV / ".requirements.sha256"
OLLAMA_API = "http://127.0.0.1:11434"
LITE_MODEL = "qwen2.5:0.5b"
MIN_PYTHON = (3, 10)


# --------------------------------------------------------------------------- #
# Pure helpers (unit-tested)
# --------------------------------------------------------------------------- #
def model_plan(profile: DeviceProfile, override: str | None = None) -> list[str]:
    """Models to have installed: the best one that fits the device (or the one the user asked for), then the lite fallback."""
    if override:
        return [override] if override == LITE_MODEL else [override, LITE_MODEL]
    allowed = allowed_models(profile)
    if not allowed:
        return []
    plan = [allowed[0].prefix]
    if LITE_MODEL not in plan:
        plan.append(LITE_MODEL)
    return plan


def catalog_names() -> list[str]:
    return [model.prefix for model in CATALOG]


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


def ollama_models_dirs() -> list[Path]:
    """Where Ollama keeps downloaded models (the server does not have to be running to look there)."""
    custom = os.environ.get("OLLAMA_MODELS")
    if custom:
        return [Path(custom)]
    dirs = [Path.home() / ".ollama" / "models"]
    if platform.system() == "Linux":
        dirs.append(Path("/usr/share/ollama/.ollama/models"))  # the system service installed by install.sh
    return dirs


def models_on_disk(models_dirs: list[Path] | None = None) -> list[str]:
    """Names such as ``qwen2.5:3b`` read from Ollama's manifest folders."""
    names: list[str] = []
    for directory in models_dirs if models_dirs is not None else ollama_models_dirs():
        root = directory / "manifests"
        if not root.is_dir():
            continue
        for manifest in root.rglob("*"):
            if not manifest.is_file():
                continue
            parts = manifest.relative_to(root).parts  # registry.ollama.ai / library / qwen2.5 / 3b
            if len(parts) < 4 or parts[0] != "registry.ollama.ai":
                continue
            name = "/".join(parts[2:-1])
            names.append(f"{name}:{parts[-1]}" if parts[1] == "library" else f"{parts[1]}/{name}:{parts[-1]}")
    return sorted(set(names))


def known_models() -> list[str]:
    """Installed models, from the running server if there is one, otherwise from disk."""
    from_server = installed_models()
    return from_server if from_server is not None else models_on_disk()


def smoke_test(model: str, timeout: float = 180.0) -> bool:
    """True if the model loads and says something (a freshly downloaded model is verified, not just trusted)."""
    body = json.dumps({"model": model, "prompt": "Reply with the single word OK.", "stream": False,
                       "options": {"num_predict": 8}}).encode()
    request = urllib.request.Request(f"{OLLAMA_API}/api/generate", data=body, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return bool(str(json.load(response).get("response", "")).strip())
    except Exception:  # noqa: BLE001 - any failure means the model is not usable
        return False


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


def setup_language_model(assume_yes: bool, override: str | None = None) -> None:
    profile = detect_device()
    plan = model_plan(profile, override)
    say(f"Device: {profile.describe()} (tier {profile.tier})")
    if not plan:
        say("This device is too small for a local language model; using rule-based advice.")
        return
    if override and override not in [m.prefix for m in allowed_models(profile)]:
        say(f"Note: {override} is bigger than recommended for this device; answers may be slow or fail "
            "(the app falls back to the lite model automatically).")
    ollama = find_ollama() or install_ollama(assume_yes)
    if not ollama:
        return
    if not start_server(ollama):
        say("The Ollama server did not start; continuing in rule-based mode.")
        return
    for model in missing_models(plan, installed_models() or []):
        if confirm(f"Download model {model} (about {approx_size_gb(model):.1f} GB)?", assume_yes):
            say(f"Pulling {model} ...")
            if subprocess.call([str(ollama), "pull", model]) != 0:
                say(f"Could not download {model}; continuing without it.")
                continue
            say(f"Checking that {model} answers ...")
            say(f"{model} works." if smoke_test(model) else f"{model} was downloaded but did not answer; the app will fall back.")
        else:
            say(f"Skipping {model}.")
    say("Language models ready: " + ", ".join(installed_models() or ["none"]))


def port_is_free(port: int, host: str = "127.0.0.1") -> bool:
    """True when the port can be taken: we try the very operation the app server will perform (binding it)."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        try:
            probe.bind((host, port))
        except OSError:
            return False
        return True


def pick_port(preferred: int, attempts: int = 20) -> int:
    """The preferred port if it is free, otherwise the next free one (so a busy port never stops the app from starting)."""
    for port in range(preferred, preferred + attempts):
        if port_is_free(port):
            return port
    raise OSError(f"No free port found between {preferred} and {preferred + attempts - 1}. Close other apps or pass --port.")


def start_app(port: int, open_browser: bool, model: str | None = None, lan: bool = False) -> int:
    chosen = pick_port(port)
    if chosen != port:
        say(f"Port {port} is busy, so I am using {chosen} instead. (If you use the Google sign-in, GOOGLE_REDIRECT_URI in .env must use this port.)")
    port = chosen
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
    if lan:
        say("LAN mode: other devices on your network can open this app and use your local AI model. Use it only on a network you trust.")
    say(f"Starting Signal Studio at {url}  (press Ctrl+C to stop)")
    env = dict(os.environ, STREAMLIT_BROWSER_GATHER_USAGE_STATS="false")
    if model:
        env["LLM_MODEL"] = model  # the app then uses exactly this model instead of choosing one by device
    address = "0.0.0.0" if lan else "127.0.0.1"  # by default only this computer can reach the app
    return subprocess.call([str(venv_python()), "-m", "streamlit", "run", str(ROOT / "app.py"), "--server.port", str(port),
                            "--server.address", address, "--server.headless", "true"], cwd=ROOT, env=env)


def check(override: str | None = None) -> None:
    profile = detect_device()
    plan = model_plan(profile, override)
    ollama = find_ollama()
    server_models = installed_models()
    present = server_models if server_models is not None else models_on_disk()
    print(f"Python        : {platform.python_version()} (need {MIN_PYTHON[0]}.{MIN_PYTHON[1]}+)")
    print(f"Environment   : venv {'present' if venv_python().exists() else 'missing'}, requirements "
          f"{'up to date' if deps_up_to_date() else 'need installing'}")
    print(f"Settings      : {ENV_PATH.name} {'found' if ENV_PATH.exists() else 'not found (optional)'}")
    print(f"Device        : {profile.describe()} (tier {profile.tier})")
    print(f"Model plan    : {', '.join(plan) if plan else 'none (device too small; rule-based advice)'}")
    print(f"Ollama        : {'found at ' + str(ollama) if ollama else 'not installed'}; server "
          f"{'running' if server_models is not None else 'not running (started automatically when needed)'}")
    print(f"Models present: {', '.join(present) or 'none'}")
    if plan:
        todo = missing_models(plan, present)
        print(f"To download   : {', '.join(f'{m} (~{approx_size_gb(m):.1f} GB)' for m in todo) or 'nothing'}")
    print("Plan: nothing was changed (--check).")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--yes", action="store_true", help="accept every install and download without asking")
    parser.add_argument("--no-llm", action="store_true", help="skip the language model (rule-based advice only)")
    parser.add_argument("--no-browser", action="store_true", help="do not open the browser")
    parser.add_argument("--port", type=int, default=8501)
    parser.add_argument("--check", action="store_true", help="show the plan and change nothing")
    parser.add_argument("--model", help=f"use this model instead of the automatic choice (one of: {', '.join(catalog_names())})")
    parser.add_argument("--lan", action="store_true", help="let other devices on your network open the app (default: this computer only)")
    args = parser.parse_args()
    if sys.version_info < MIN_PYTHON:
        print(f"Python {MIN_PYTHON[0]}.{MIN_PYTHON[1]}+ is required (found {platform.python_version()}).", file=sys.stderr)
        return 2
    if args.model and args.model not in catalog_names():
        print(f"Unknown model {args.model!r}. Choose one of: {', '.join(catalog_names())}", file=sys.stderr)
        return 2
    if args.check:
        check(args.model)
        return 0
    load_env_file()  # ./.env settings (the real environment always wins); inherited by the app process
    ensure_environment(args.yes)
    if not args.no_llm:
        try:
            setup_language_model(args.yes, args.model)
        except Exception as error:  # noqa: BLE001 - the language model must never block the app
            say(f"Language-model setup failed ({type(error).__name__}); continuing in rule-based mode.")
    return start_app(args.port, not args.no_browser, None if args.no_llm else args.model, args.lan)


if __name__ == "__main__":
    raise SystemExit(main())
