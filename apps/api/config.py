"""
Configuration reader for the LLM provider in the diagnose endpoint.
Loads config.yaml, resolves environment variable placeholders, and validates required fields.
"""

import yaml
import os
from pathlib import Path

CONFIG_PATH = Path(__file__).parent / "config.yaml"
REQUIRED_FIELDS = {"provider", "model", "api_key", "temperature", "max_tokens"}


def _load_yaml() -> dict:
    """Read config.yaml and return as dict."""
    if not CONFIG_PATH.is_file():
        raise FileNotFoundError(f"Config file not found at {CONFIG_PATH}")
    with CONFIG_PATH.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    return data


def _resolve_env_vars(data: dict) -> dict:
    """Replace ${VAR_NAME} with values from the environment."""
    for key, val in data.items():
        if isinstance(val, str):
            var_name = val.strip("${}") if "${" in val and "}" in val else ""
            if var_name:
                env_val = os.getenv(var_name)
                if env_val is not None:
                    data[key] = env_val
        elif isinstance(val, dict):
            _resolve_env_vars(val)
    return data


def _validate(data: dict):
    """Validate that all required fields are present and non-empty."""
    for field in REQUIRED_FIELDS:
        if field not in data:
            raise KeyError(f"Missing required config field: {field}")
        if not data[field]:
            raise ValueError(f"Config field '{field}' cannot be empty")


def get_config() -> dict:
    """Return the validated, environment‑resolved configuration."""
    raw = _load_yaml()
    resolved = _resolve_env_vars(raw)
    _validate(resolved)
    return resolved


if __name__ == "__main__":
    # Simple sanity check
    try:
        cfg = get_config()
        print("Configuration loaded:", cfg)
    except Exception as e:
        print("Configuration error:", e)
        exit(1)