from __future__ import annotations

import json
import zipfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
ADDON_DIR = PROJECT_ROOT / "addon"
DIST_DIR = PROJECT_ROOT / "dist"

EXCLUDED_DIRS = {"__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache"}
EXCLUDED_SUFFIXES = {".pyc", ".pyo"}


def read_version() -> str:
    config_path = ADDON_DIR / "config.json"
    try:
        data = json.loads(config_path.read_text(encoding="utf-8"))
        return str(data.get("project", {}).get("version") or "0.0.1")
    except Exception:
        return "0.0.1"


def should_include(path: Path) -> bool:
    if any(part in EXCLUDED_DIRS for part in path.parts):
        return False
    if path.suffix in EXCLUDED_SUFFIXES:
        return False
    return True


def build() -> Path:
    if not (ADDON_DIR / "__init__.py").exists():
        raise SystemExit("addon/__init__.py is missing")

    version = read_version()
    DIST_DIR.mkdir(exist_ok=True)
    output = DIST_DIR / f"due_load_balancer-{version}.ankiaddon"

    if output.exists():
        output.unlink()

    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in ADDON_DIR.rglob("*"):
            if path.is_dir() or not should_include(path):
                continue
            archive.write(path, path.relative_to(ADDON_DIR).as_posix())

    print(f"Built {output}")
    return output


if __name__ == "__main__":
    build()
