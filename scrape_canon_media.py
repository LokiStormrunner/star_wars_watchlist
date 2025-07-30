import asyncio
import json

from bs4 import BeautifulSoup, Tag
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from db import AsyncSessionLocal, engine
from models import Base, CanonMediaEntry


async def scrape_and_store():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    with open("media_table.html") as html_file:
        soup = BeautifulSoup(html_file, "html.parser")

    entries = []
    entry_id = 0
    async with AsyncSessionLocal() as session:
        for table in soup.find_all("table"):
            if not isinstance(table, Tag):
                continue
            headers = [
                th.get_text(strip=True)
                for th in table.find_all("th")
                if isinstance(th, Tag)
            ]
            if "Year" in headers and "Title" in headers and "Released" in headers:
                for row in table.find_all("tr")[1:]:
                    if not isinstance(row, Tag):
                        continue
                    cells = [
                        cell
                        for cell in row.find_all(["td", "th"])
                        if isinstance(cell, Tag)
                    ]
                    if len(cells) >= 4:
                        year = cells[0].get("title", None)
                        content_type = cells[1].get_text(strip=True)
                        title = cells[2].get("title", None)
                        released = cells[3].get_text(strip=True)
                        # Try to find existing entry
                        result = await session.execute(
                            select(CanonMediaEntry).where(
                                CanonMediaEntry.year == year,
                                CanonMediaEntry.content_type == content_type,
                                CanonMediaEntry.title == title,
                                CanonMediaEntry.released == released,
                            )
                        )
                        existing = result.scalar_one_or_none()
                        if existing:
                            # Update fields except watched
                            if year is not None:
                                setattr(existing, "year", year)
                            if content_type is not None:
                                setattr(existing, "content_type", content_type)
                            if title is not None:
                                setattr(existing, "title", title)
                            if released is not None:
                                setattr(existing, "released", released)
                            # watched status is preserved
                        else:
                            entry = CanonMediaEntry(
                                year=year or None,
                                content_type=content_type or None,
                                title=title,
                                released=released or None,
                                watched=False,
                            )
                            session.add(entry)
                        entry_id += 1
        await session.commit()


if __name__ == "__main__":
    asyncio.run(scrape_and_store())
