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
                        # For year (cell 0)
                        year = None
                        if isinstance(cells[0], Tag):
                            a_tags = cells[0].find_all("a")
                            for a in reversed(a_tags):
                                if isinstance(a, Tag) and a.get("title"):
                                    year = a.get("title")
                                    break
                            if year is None and cells[0].get("title"):
                                year = cells[0].get("title")
                        # For title and episode_title (cell 2)
                        title = None
                        episode_title = None
                        title_html = None
                        if isinstance(cells[2], Tag):
                            title_html = str(cells[2])
                            a_tags = [
                                a
                                for a in cells[2].find_all("a")
                                if isinstance(a, Tag) and a.get("title")
                            ]
                            if len(a_tags) >= 2:
                                title = a_tags[-2].get("title")
                                episode_title = a_tags[-1].get("title")
                            elif len(a_tags) == 1:
                                title = a_tags[0].get("title")
                            if title is None and cells[2].get("title"):
                                title = cells[2].get("title")

                        content_type = cells[1].get_text(strip=True)
                        released = cells[3].get_text(strip=True)
                        # Try to find existing entry
                        result = await session.execute(
                            select(CanonMediaEntry).where(
                                CanonMediaEntry.year == year,
                                CanonMediaEntry.content_type == content_type,
                                CanonMediaEntry.title == title,
                                CanonMediaEntry.episode_title == episode_title,
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
                            if episode_title is not None:
                                setattr(existing, "episode_title", episode_title)
                            if title_html is not None:
                                setattr(existing, "title_html", title_html)
                            if released is not None:
                                setattr(existing, "released", released)
                            # watched status is preserved
                        else:
                            entry = CanonMediaEntry(
                                year=year or None,
                                content_type=content_type or None,
                                title=title,
                                episode_title=episode_title,
                                title_html=title_html,
                                released=released or None,
                                watched=False,
                            )
                            session.add(entry)
                        entry_id += 1
        await session.commit()


if __name__ == "__main__":
    asyncio.run(scrape_and_store())
