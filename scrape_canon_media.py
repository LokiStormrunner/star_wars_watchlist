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
