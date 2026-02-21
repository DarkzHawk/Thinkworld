from pathlib import Path
import os


def _get(name: str, default: str | None = None) -> str | None:
    value = os.getenv(name)
    if value is None or value == "":
        return default
    return value


DATABASE_URL = _get(
    "DATABASE_URL",
    "postgresql+psycopg2://archive:archive_password@postgres:5432/archive",
)
REDIS_URL = _get("REDIS_URL", "redis://redis:6379/0")
DATA_DIR = Path(_get("DATA_DIR", "/data"))
FILES_DIR = DATA_DIR / "files"
HTML_DIR = DATA_DIR / "html"
TMP_DIR = DATA_DIR / "tmp"

VIDEO_ALLOWLIST = [
    domain.strip().lower()
    for domain in (_get("VIDEO_ALLOWLIST", "") or "").split(",")
    if domain.strip()
]
