"""The deployed app must contain everything it needs: model files, knowledge files and every package it imports."""

from __future__ import annotations

import ast
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PIP_NAME = {"sklearn": "scikit-learn", "PIL": "pillow", "yaml": "pyyaml"}
PROVIDED_BY_STREAMLIT = {"altair"}  # installed as a dependency of streamlit


def _imports(path: Path) -> set[str]:
    """Modules imported when the module is loaded. Imports inside functions are lazy (for example matplotlib, used only
    when training writes its plots), so they do not run in the deployed app and are not counted."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    names: set[str] = set()

    def visit(node: ast.AST) -> None:
        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            if isinstance(child, ast.Import):
                names.update(alias.name for alias in child.names)
            elif isinstance(child, ast.ImportFrom) and child.module and child.level == 0:
                names.add(child.module)
            visit(child)

    visit(tree)
    return names


def _runtime_modules() -> list[Path]:
    """app.py plus every src module it reaches (the closure of its imports), i.e. what really runs in production."""
    seen, queue = set(), [ROOT / "app.py"]
    while queue:
        path = queue.pop()
        if path in seen:
            continue
        seen.add(path)
        for name in _imports(path):
            if name.startswith("src."):
                candidate = ROOT / (name.replace(".", "/") + ".py")
                if candidate.exists():
                    queue.append(candidate)
    return sorted(seen)


def test_every_third_party_package_the_app_imports_is_in_the_deployment_requirements():
    requirements = {re.split(r"[=<>\[ ]", line.strip(), 1)[0].lower() for line in (ROOT / "requirements-app.txt").read_text(encoding="utf-8").splitlines()
                    if line.strip() and not line.startswith("#")}
    missing = set()
    for path in _runtime_modules():
        for name in _imports(path):
            top = name.split(".")[0]
            if top in sys.stdlib_module_names or top == "src" or top in PROVIDED_BY_STREAMLIT or (ROOT / "src" / f"{top}.py").exists():
                continue  # standard library, our own code (also imported by bare name when a script runs directly), or a streamlit dependency
            if PIP_NAME.get(top, top).lower() not in requirements:
                missing.add((path.name, top))
    assert not missing, f"imported in production code but not in requirements-app.txt: {sorted(missing)}"


def test_the_docker_image_contains_the_models_and_knowledge_the_app_loads():
    dockerfile = (ROOT / "Dockerfile").read_text(encoding="utf-8")
    copied = " ".join(line for line in dockerfile.splitlines() if line.startswith("COPY"))
    for needed in ("models/advanced_model_bundle.joblib", "models/similarity_index.joblib", "models/history_models.joblib", "knowledge", "src", "app.py", ".streamlit"):
        assert needed in copied, f"the Dockerfile does not copy {needed}"
    # and none of the runtime files is excluded from the build context
    ignored = {line.strip() for line in (ROOT / ".dockerignore").read_text(encoding="utf-8").splitlines() if line.strip()}
    assert not ignored & {"knowledge", "src", "models", "app.py", ".streamlit"}


def test_the_runtime_files_really_exist_in_the_repository():
    for relative in ("models/advanced_model_bundle.joblib", "models/similarity_index.joblib", "models/history_models.joblib",
                     "knowledge/youtube_platform_timeline.json", "knowledge/real_examples.json", ".streamlit/config.toml"):
        assert (ROOT / relative).is_file(), relative


def test_the_streamlit_config_keeps_the_origin_check_on():
    config = (ROOT / ".streamlit" / "config.toml").read_text(encoding="utf-8")
    assert not re.search(r"^\s*enableCORS\s*=\s*false", config, re.MULTILINE), "turning CORS off lets any website connect to the app"
    assert re.search(r"^\s*enableXsrfProtection\s*=\s*true", config, re.MULTILINE)
