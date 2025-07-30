from typing import Optional

from pydantic import BaseModel
from sqlalchemy import Boolean, Column, Integer, String
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class CanonMediaEntry(Base):
    __tablename__ = "canon_media"

    id = Column(Integer, primary_key=True, autoincrement=True)
    year = Column(
        String(32), nullable=True
    )  # e.g. '382 BBY', '0 ABY', 'c. 232 BBY', etc.
    content_type = Column(String(64), nullable=True)  # e.g. 'C', 'TV', 'N', etc.
    title = Column(String(256), nullable=False)
    released = Column(
        String(64), nullable=True
    )  # e.g. '2023-04-26', '2015-09-04', etc.
    watched = Column(Boolean, default=False)


class CanonMediaEntrySchema(BaseModel):
    id: int
    year: Optional[str]
    content_type: Optional[str]
    title: str
    released: Optional[str]
    watched: bool

    model_config = {"from_attributes": True}
