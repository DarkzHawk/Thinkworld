from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import relationship

from app.api.db import Base


class Item(Base):
    __tablename__ = "items"

    id = Column(Integer, primary_key=True, index=True)
    url = Column(Text, nullable=False)
    type = Column(String(20), nullable=True)
    title = Column(Text, nullable=True)
    source_domain = Column(Text, nullable=True)
    status = Column(String(20), nullable=False, default="queued")
    policy_video_download_allowed = Column(Boolean, nullable=False, default=False)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    assets = relationship("Asset", back_populates="item", cascade="all, delete-orphan")
    tags = relationship("Tag", secondary="item_tags", back_populates="items")


class Asset(Base):
    __tablename__ = "assets"

    id = Column(Integer, primary_key=True, index=True)
    item_id = Column(Integer, ForeignKey("items.id", ondelete="CASCADE"), nullable=False)
    kind = Column(String(20), nullable=False)
    path = Column(Text, nullable=False)
    sha256 = Column(String(64), nullable=True)
    size = Column(Integer, nullable=True)
    mime = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    item = relationship("Item", back_populates="assets")


class Tag(Base):
    __tablename__ = "tags"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False)

    items = relationship("Item", secondary="item_tags", back_populates="tags")


class ItemTag(Base):
    __tablename__ = "item_tags"

    item_id = Column(Integer, ForeignKey("items.id", ondelete="CASCADE"), primary_key=True)
    tag_id = Column(Integer, ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True)
