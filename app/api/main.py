from __future__ import annotations

from pathlib import Path
from typing import List, Optional
from datetime import datetime, timezone

from fastapi import Depends, FastAPI, HTTPException, Query, Request
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from redis import Redis
from rq import Queue, Retry
from sqlalchemy.orm import Session
from sqlalchemy import or_, func

from app.api.db import SessionLocal
from app.api.models import Item, Asset, Tag
from app.api.schemas import ItemCreate, ItemOut
from app.common.config import REDIS_URL, DATA_DIR
from app.common.utils import get_domain, is_allowlisted, is_youtube
from app.worker.worker import process_item

app = FastAPI(title="Personal Archive MVP")

app.mount("/static", StaticFiles(directory="web/static"), name="static")


templates = Jinja2Templates(directory="web/templates")


def get_db() -> Session:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def enqueue_item(item_id: int) -> None:
    redis = Redis.from_url(REDIS_URL)
    queue = Queue("default", connection=redis)
    queue.enqueue(
        process_item,
        item_id,
        retry=Retry(max=3, interval=[60, 120, 300]),
    )


def item_to_schema(item: Item) -> ItemOut:
    return ItemOut(
        id=item.id,
        url=item.url,
        type=item.type,
        title=item.title,
        source_domain=item.source_domain,
        status=item.status,
        policy_video_download_allowed=item.policy_video_download_allowed,
        error_message=item.error_message,
        created_at=item.created_at,
        updated_at=item.updated_at,
        tags=[tag.name for tag in item.tags],
        assets=list(item.assets),
    )


@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/items/{item_id}", response_class=HTMLResponse)
def detail_page(item_id: int, request: Request, db: Session = Depends(get_db)):
    item = db.get(Item, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    return templates.TemplateResponse(
        "detail.html",
        {
            "request": request,
            "item": item_to_schema(item).model_dump(),
        },
    )


@app.post("/api/items", response_model=ItemOut)
def create_item(payload: ItemCreate, db: Session = Depends(get_db)):
    domain = get_domain(str(payload.url))
    policy_allowed = is_allowlisted(domain) and not is_youtube(domain)

    item = Item(
        url=str(payload.url),
        type="unknown",
        status="queued",
        source_domain=domain,
        policy_video_download_allowed=policy_allowed,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )

    tags = []
    for raw_tag in payload.tags:
        name = raw_tag.strip()
        if not name:
            continue
        existing = db.query(Tag).filter(func.lower(Tag.name) == name.lower()).first()
        if existing:
            tags.append(existing)
        else:
            new_tag = Tag(name=name)
            db.add(new_tag)
            db.flush()
            tags.append(new_tag)
    item.tags = tags

    db.add(item)
    db.commit()
    db.refresh(item)

    enqueue_item(item.id)
    return item_to_schema(item)


@app.get("/api/items", response_model=List[ItemOut])
def list_items(
    db: Session = Depends(get_db),
    query: Optional[str] = Query(default=None),
    tag: Optional[str] = Query(default=None),
):
    items_query = db.query(Item)

    if query:
        q = f"%{query}%"
        items_query = items_query.filter(or_(Item.url.ilike(q), Item.title.ilike(q)))

    if tag:
        items_query = items_query.join(Item.tags).filter(func.lower(Tag.name) == tag.lower())

    items = items_query.order_by(Item.created_at.desc()).limit(200).all()
    return [item_to_schema(item) for item in items]


@app.get("/api/items/{item_id}", response_model=ItemOut)
def get_item(item_id: int, db: Session = Depends(get_db)):
    item = db.get(Item, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    return item_to_schema(item)


@app.get("/files/{asset_id}")
def get_file(asset_id: int, db: Session = Depends(get_db)):
    asset = db.get(Asset, asset_id)
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")

    path = Path(asset.path).resolve()
    if not str(path).startswith(str(DATA_DIR.resolve())):
        raise HTTPException(status_code=403, detail="Invalid asset path")

    return FileResponse(path, media_type=asset.mime, filename=path.name)
