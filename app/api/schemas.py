from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, HttpUrl


class AssetOut(BaseModel):
    id: int
    kind: str
    path: str
    sha256: Optional[str] = None
    size: Optional[int] = None
    mime: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ItemOut(BaseModel):
    id: int
    url: str
    type: Optional[str] = None
    title: Optional[str] = None
    source_domain: Optional[str] = None
    status: str
    policy_video_download_allowed: bool
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    tags: List[str] = []
    assets: List[AssetOut] = []

    model_config = ConfigDict(from_attributes=True)


class ItemCreate(BaseModel):
    url: HttpUrl
    tags: List[str] = []
