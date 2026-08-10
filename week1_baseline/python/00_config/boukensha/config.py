import os
from pathlib import Path

import yaml
from dotenv import load_dotenv


class Config:
    # The .boukensha config directory is resolved in this order:
    #   1. BOUKENSHA_DIR environment variable (set before loading .env)
    #   2. ~/.boukensha  (default)
    DEFAULT_DIR = Path.home() / ".boukensha"

    # Default prompts shipped alongside the library code.
    PROMPTS_DIR = Path(__file__).resolve().parents[1] / "prompts"

    def __init__(self):
        self._dir = self._resolve_dir()
        self._load_env()
        self._settings = self._load_settings()

    # ---------- tasks -------------------------------------------------

    @property
    def dir(self):
        return self._dir

    @property
    def settings(self):
        return self._settings

    # With no argument: returns the full tasks hash from settings.yaml.
    # With a name: returns that task's settings hash, e.g. tasks("player").
    def tasks(self, name=None):
        all_tasks = self.dig("tasks") or {}
        return all_tasks.get(name) if name else all_tasks

    # The user's prompts directory for task prompt overrides.
    @property
    def user_prompts_dir(self):
        return self._dir / "prompts"

    # ---------- MUD connection -----------------------------------------

    @property
    def mud_host(self):
        return self.dig("mud", "host") or "localhost"

    @property
    def mud_port(self):
        return self.dig("mud", "port") or 4000

    @property
    def mud_username(self):
        return self.dig("mud", "username")

    @property
    def mud_password(self):
        return self.dig("mud", "password")

    # ---------- low-level helpers ---------------------------------------

    # Fetch a nested key path from settings, e.g. dig("mud", "host")
    def dig(self, *keys):
        node = self._settings
        for key in keys:
            if not isinstance(node, dict):
                return None
            node = node.get(key)
        return node

    def __str__(self):
        return f"<Config dir={self._dir} tasks={','.join(self.tasks().keys())}>"

    def __repr__(self):
        return str(self)

    def _resolve_dir(self):
        raw = os.environ.get("BOUKENSHA_DIR") or str(self.DEFAULT_DIR)
        return Path(raw).expanduser().resolve()

    def _load_env(self):
        env_file = self._dir / ".env"
        if env_file.exists():
            load_dotenv(env_file)

    def _load_settings(self):
        settings_file = self._dir / "settings.yaml"
        if settings_file.exists():
            return yaml.safe_load(settings_file.read_text()) or {}
        return {}
