from __future__ import annotations

from pathlib import Path
from urllib.parse import urlparse, urljoin
import hashlib
import re

from app.common.config import VIDEO_ALLOWLIST


VIDEO_EXTS = {".mp4", ".mov", ".mkv", ".webm"}
IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp"}
MANIFEST_EXTS = {".m3u8", ".mpd"}


def get_domain(url: str) -> str:
    return urlparse(url).netloc.lower()


def resolve_url(base: str, url: str) -> str:
    return urljoin(base, url)


def is_allowlisted(domain: str) -> bool:
    domain = domain.lower()
    for allowed in VIDEO_ALLOWLIST:
        if domain == allowed or domain.endswith("." + allowed):
            return True
    return False


def is_youtube(domain: str) -> bool:
    return domain == "youtube.com" or domain.endswith(".youtube.com")


def has_video_ext(url: str) -> bool:
    path = urlparse(url).path.lower()
    return Path(path).suffix in VIDEO_EXTS


def has_image_ext(url: str) -> bool:
    path = urlparse(url).path.lower()
    return Path(path).suffix in IMAGE_EXTS


def is_manifest_url(url: str, content_type: str | None = None) -> bool:
    path = urlparse(url).path.lower()
    if Path(path).suffix in MANIFEST_EXTS:
        return True
    if content_type:
        ct = content_type.lower()
        if "mpegurl" in ct or "application/dash+xml" in ct:
            return True
    return False


def looks_protected(url: str, content_type: str | None, body_text: str | None) -> bool:
    token_markers = ["token=", "signature=", "expires=", "policy=", "key="]
    lowered_url = url.lower()
    if any(marker in lowered_url for marker in token_markers):
        return True

    if not body_text:
        return False

    lowered = body_text.lower()
    drm_markers = [
        "ext-x-key",
        "keyformat",
        "widevine",
        "playready",
        "cenc",
        "fairplay",
    ]
    return any(marker in lowered for marker in drm_markers)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def guess_extension(url: str, content_type: str | None) -> str:
    if content_type:
        if content_type.startswith("image/"):
            return "." + content_type.split("/")[-1].split("+")[-1]
        if content_type.startswith("video/"):
            return "." + content_type.split("/")[-1].split("+")[-1]
        if content_type == "text/html":
            return ".html"
    path = urlparse(url).path
    return Path(path).suffix or ""


def safe_filename(name: str) -> str:
    name = re.sub(r"[^a-zA-Z0-9._-]+", "_", name)
    return name.strip("_") or "file"


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def is_html_content(content_type: str | None, url: str) -> bool:
    if content_type and content_type.startswith("text/html"):
        return True
    return urlparse(url).path.lower().endswith((".html", ".htm"))
