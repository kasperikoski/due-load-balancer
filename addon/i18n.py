"""Tiny JSON based translation helper."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .constants import DEFAULT_LANGUAGE, DEFAULT_PROJECT_NAME


class Translator:
    def __init__(self, config: dict[str, Any]) -> None:
        self.config = config
        self.language = str(config.get("ui", {}).get("language") or DEFAULT_LANGUAGE)
        self.project_name = str(config.get("project", {}).get("display_name") or DEFAULT_PROJECT_NAME)
        self.version = str(config.get("project", {}).get("version") or "0.0.1")
        self._fallback = self._load_language(DEFAULT_LANGUAGE)
        self._strings = self._load_language(self.language)

    def _load_language(self, language: str) -> dict[str, str]:
        path = Path(__file__).parent / "lang" / f"{language}.json"
        try:
            with path.open("r", encoding="utf-8") as handle:
                data = json.load(handle)
            if isinstance(data, dict):
                return {str(k): str(v) for k, v in data.items()}
        except Exception:
            pass
        return {}

    def t(self, key: str, **kwargs: object) -> str:
        text = self._strings.get(key) or self._fallback.get(key) or key
        values = {
            "project_name": self.project_name,
            "version": self.version,
            **kwargs,
        }
        try:
            return text.format(**values)
        except Exception:
            return text
