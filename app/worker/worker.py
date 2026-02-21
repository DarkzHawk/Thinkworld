from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Optional\r?\n\r?\nimport hashlib\r?\nimport requests
from bs4 import BeautifulSoup
from readability import Document
from redis import Redis
from rq import Worker, Queue, Connection

from app.api.db import SessionLocal
from app.api.models import Item, Asset
from app.common.config import DATA_DIR, FILES_DIR, HTML_DIR, TMP_DIR, REDIS_URL
from app.common.utils import (
    ensure_dir,
    get_domain,
    guess_extension,
    has_image_ext,
    has_video_ext,
    is_allowlisted,
    is_html_content,
    is_manifest_url,
    is_youtube,
    looks_protected,
    resolve_url,
    safe_filename,
    sha256_bytes,\r?\n)


USER_AGENT = "Mozilla/5.0 (ArchiveBot/0.1)"
REQUEST_TIMEOUT = (10, 30)


def _make_dirs() -> None:
    ensure_dir(DATA_DIR)
    ensure_dir(FILES_DIR)
    ensure_dir(HTML_DIR)
    ensure_dir(TMP_DIR)


def _save_asset(
    db,
    item: Item,
    kind: str,
    path: Path,
    sha256: Optional[str],
    size: Optional[int],
    mime: Optional[str],
) -> Asset:
    asset = Asset(
        item_id=item.id,
        kind=kind,
        path=str(path),
        sha256=sha256,
        size=size,
        mime=mime,
    )
    db.add(asset)
    db.flush()
    return asset


def _download_to_file(url: str, content_type: Optional[str]) -> tuple[Path, str, int]:
    temp_path = TMP_DIR / safe_filename(Path(url).name or "download")
    with requests.get(url, stream=True, timeout=REQUEST_TIMEOUT, headers={"User-Agent": USER_AGENT}) as resp:
        resp.raise_for_status()
        digest = hashlib.sha256()
        size = 0
        with temp_path.open("wb") as handle:
            for chunk in resp.iter_content(chunk_size=1024 * 1024):
                if not chunk:
                    continue
                handle.write(chunk)
                digest.update(chunk)
                size += len(chunk)
        sha = digest.hexdigest()

    ext = guess_extension(url, content_type)
    final_path = FILES_DIR / f"{sha}{ext}"
    if not final_path.exists():
        temp_path.replace(final_path)
    else:
        temp_path.unlink(missing_ok=True)
    return final_path, sha, size


def _handle_article(db, item: Item, url: str, html: str) -> None:
    doc = Document(html)
    title = doc.short_title() or item.title or url
    content_html = doc.summary()

    soup = BeautifulSoup(content_html, "lxml")
    for img in soup.find_all("img"):
        src = img.get("src")
        if not src:
            continue
        if src.startswith("data:"):
            continue
        abs_url = resolve_url(url, src)
        try:
            asset = _download_asset(db, item, abs_url, kind="image")
        except Exception:
            asset = None
        if asset:
            img["src"] = f"/files/{asset.id}"

    final_html = str(soup)
    html_bytes = final_html.encode("utf-8")
    sha = sha256_bytes(html_bytes)
    html_path = HTML_DIR / f"item_{item.id}.html"
    html_path.write_bytes(html_bytes)
    _save_asset(db, item, "html", html_path, sha, len(html_bytes), "text/html")

    item.title = title
    item.type = "article"


def _download_asset(db, item: Item, url: str, kind: str) -> Asset:
    head_resp = requests.head(url, timeout=REQUEST_TIMEOUT, headers={"User-Agent": USER_AGENT})
    content_type = head_resp.headers.get("Content-Type", "").split(";")[0].strip()

    path, sha, size = _download_to_file(url, content_type)
    return _save_asset(db, item, kind, path, sha, size, content_type)


def _handle_file(db, item: Item, url: str, kind: str, content_type: Optional[str]) -> None:
    path, sha, size = _download_to_file(url, content_type)
    _save_asset(db, item, kind, path, sha, size, content_type)
    item.type = kind
    item.title = item.title or Path(url).name


def _handle_video(db, item: Item, url: str, content_type: Optional[str], body_text: Optional[str]) -> None:
    domain = get_domain(url)
    allowlisted = is_allowlisted(domain) and not is_youtube(domain)
    item.type = "video"
    item.policy_video_download_allowed = allowlisted

    if not allowlisted:
        return

    if is_manifest_url(url, content_type):
        return

    if looks_protected(url, content_type, body_text):
        return

    if not (content_type and content_type.startswith("video/") or has_video_ext(url)):
        return

    _handle_file(db, item, url, "video", content_type)


def process_item(item_id: int) -> None:
    _make_dirs()
    db = SessionLocal()
    try:
        item = db.get(Item, item_id)
        if not item:
            return
        item.status = "processing"
        item.updated_at = datetime.now(timezone.utc)
        db.commit()

        url = item.url
        domain = get_domain(url)
        item.source_domain = domain

        resp = requests.get(url, timeout=REQUEST_TIMEOUT, headers={"User-Agent": USER_AGENT})
        resp.raise_for_status()
        content_type = resp.headers.get("Content-Type", "").split(";")[0].strip().lower()

        body_text = None
        if is_html_content(content_type, url):
            html = resp.text
            body_text = html[:20000]
            _handle_article(db, item, url, html)
        elif content_type.startswith("image/") or has_image_ext(url):
            _handle_file(db, item, url, "image", content_type)
        elif content_type.startswith("video/") or has_video_ext(url) or is_manifest_url(url, content_type):
            if content_type.startswith("text/"):
                body_text = resp.text[:20000]
            _handle_video(db, item, url, content_type, body_text)
        else:
            _handle_file(db, item, url, "file", content_type)

        item.status = "done"
        item.updated_at = datetime.now(timezone.utc)
        db.commit()
    except Exception as exc:
        item = db.get(Item, item_id)
        if item:
            item.status = "failed"
            item.error_message = str(exc)
            item.updated_at = datetime.now(timezone.utc)
            db.commit()
    finally:
        db.close()


def main() -> None:
    redis = Redis.from_url(REDIS_URL)
    with Connection(redis):
        worker = Worker([Queue("default")])
        worker.work()


if __name__ == "__main__":
    main()

