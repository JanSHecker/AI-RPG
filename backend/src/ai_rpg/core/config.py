from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path


def _as_bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(slots=True)
class Settings:
    db_path: Path
    provider: str
    model: str
    api_base: str
    api_key: str | None
    debug: bool = False

    @property
    def database_url(self) -> str:
        return f"sqlite:///{self.db_path}"


def _load_env_files() -> None:
    backend_dir = Path(__file__).resolve().parents[3]
    repo_root = backend_dir.parent

    for env_path in (repo_root / ".env", backend_dir / ".env"):
        if not env_path.exists():
            continue

        for raw_line in env_path.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue

            name, value = line.split("=", 1)
            name = name.strip()
            value = value.strip()
            if not name or name in os.environ:
                continue

            if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
                value = value[1:-1]
            os.environ[name] = value


def load_settings() -> Settings:
    _load_env_files()
    db_path = Path(os.getenv("AI_RPG_DB_PATH", "ai_rpg.db")).expanduser()
    return Settings(
        db_path=db_path,
        provider=os.getenv("AI_RPG_PROVIDER", "openrouter"),
        model=os.getenv("AI_RPG_MODEL", "openrouter/auto"),
        api_base=os.getenv("AI_RPG_API_BASE", "https://openrouter.ai/api/v1"),
        api_key=os.getenv("AI_RPG_API_KEY") or None,
        debug=_as_bool(os.getenv("AI_RPG_DEBUG"), default=False),
    )
