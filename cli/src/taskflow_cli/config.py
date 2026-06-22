"""Runtime config: env-driven, XDG-compliant, fail-fast."""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

DEFAULT_API_URL = "http://localhost:8000"


class ConfigError(Exception):
    """Raised when env config is invalid."""


def _xdg_config_home() -> Path:
    # XDG spec: ignore empty value; fall back to ~/.config
    raw = os.environ.get("XDG_CONFIG_HOME", "").strip()
    return Path(raw) if raw else Path.home() / ".config"


@dataclass(frozen=True)
class Config:
    """Resolved once per CLI invocation. Immutable."""

    api_url: str
    config_dir: Path

    @property
    def credentials_path(self) -> Path:
        return self.config_dir / "credentials"


def load() -> Config:
    """Load and validate config from env. Raises ConfigError on bad input."""
    api_url = os.environ.get("TASKFLOW_API_URL", DEFAULT_API_URL).rstrip("/")
    if not (api_url.startswith("http://") or api_url.startswith("https://")):
        raise ConfigError(
            f"TASKFLOW_API_URL must start with http:// or https:// (got: {api_url!r})"
        )
    config_dir = _xdg_config_home() / "tflowctl"
    return Config(api_url=api_url, config_dir=config_dir)
