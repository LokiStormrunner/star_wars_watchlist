from typing import Optional

from pydantic import BaseModel


class CanonMediaEntry(BaseModel):
    id: int
    year: Optional[str]  # e.g. '382 BBY', '0 ABY', 'c. 232 BBY', etc.
    content_type: Optional[str]  # e.g. 'C', 'TV', 'N', etc.
    title: str
    released: Optional[str]  # e.g. '2023-04-26', '2015-09-04', etc.
    watched: bool = False
