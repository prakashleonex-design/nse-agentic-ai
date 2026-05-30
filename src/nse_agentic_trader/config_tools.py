from __future__ import annotations

import shutil
from dataclasses import fields
from pathlib import Path

from nse_agentic_trader.config import Settings


SECRET_FIELDS = {
    "angel_client_code",
    "angel_password",
    "angel_api_key",
    "angel_totp_secret",
}


def settings_lines(settings: Settings) -> list[str]:
    lines: list[str] = []
    for field in fields(settings):
        value = getattr(settings, field.name)
        if field.name in SECRET_FIELDS:
            value = "***set***" if value else ""
        lines.append(f"{field.name}: {value}")
    lines.append(f"live_orders_enabled: {settings.live_orders_enabled}")
    return lines


def init_env_file(example_path: Path = Path(".env.example"), env_path: Path = Path(".env"), overwrite: bool = False) -> str:
    if env_path.exists() and not overwrite:
        return f"{env_path} already exists. Use --overwrite to replace it."
    if not example_path.exists():
        raise FileNotFoundError(f"Missing example env file: {example_path}")
    shutil.copyfile(example_path, env_path)
    return f"Created {env_path} from {example_path}"
