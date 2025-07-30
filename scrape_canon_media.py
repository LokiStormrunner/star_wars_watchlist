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
                        year_cell = cells[0]
                        type_cell = cells[1]
                        title_cell = cells[2]
                        released_cell = cells[3]

                        # Prepend local hrefs in all cells
                        for cell in [year_cell, type_cell, title_cell, released_cell]:
                            if cell:
                                for a in cell.find_all("a", href=True):
                                    if isinstance(a, Tag):
                                        href = a.get("href")
                                        if (
                                            isinstance(href, str)
                                            and href.startswith("/")
                                            and not href.startswith("//")
                                        ):
                                            a.attrs["href"] = (
                                                f"https://starwars.fandom.com{href}"
                                            )

                        # For year (cell 0)
                        year = year_cell.get_text(strip=True) if year_cell else None
                        year_html = year_cell.decode_contents() if year_cell else None
                        # For content_type (cell 1)
                        content_type = (
                            type_cell.get_text(strip=True) if type_cell else None
                        )
                        content_type_html = (
                            type_cell.decode_contents() if type_cell else None
                        )
                        # For title and episode_title (cell 2)
                        title = None
                        episode_title = None
                        title_html = None
                        if isinstance(title_cell, Tag):
                            title_html = title_cell.decode_contents()
                            a_tags = [
                                a
                                for a in title_cell.find_all("a")
                                if isinstance(a, Tag) and a.get("title")
                            ]
                            if len(a_tags) >= 2:
                                title = a_tags[-2].get("title")
                                episode_title = a_tags[-1].get("title")
                            elif len(a_tags) == 1:
                                title = a_tags[0].get("title")
                            if title is None and title_cell.get("title"):
                                title = title_cell.get("title")

                        # For released (cell 3)
                        released = (
                            released_cell.get_text(strip=True)
                            if released_cell
                            else None
                        )
                        released_html = (
                            released_cell.decode_contents() if released_cell else None
                        )

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
                            if year_html is not None:
                                setattr(existing, "year_html", year_html)
                            if content_type is not None:
                                setattr(existing, "content_type", content_type)
                            if content_type_html is not None:
                                setattr(
                                    existing, "content_type_html", content_type_html
                                )
                            if title is not None:
                                setattr(existing, "title", title)
                            if title_html is not None:
                                setattr(existing, "title_html", title_html)
                            if episode_title is not None:
                                setattr(existing, "episode_title", episode_title)
                            if released is not None:
                                setattr(existing, "released", released)
                            if released_html is not None:
                                setattr(existing, "released_html", released_html)
                            # watched status is preserved
                        else:
                            entry = CanonMediaEntry(
                                year=year or None,
                                year_html=year_html,
                                content_type=content_type or None,
                                content_type_html=content_type_html,
                                title=title,
                                title_html=title_html,
                                episode_title=episode_title,
                                released=released or None,
                                released_html=released_html,
                                watched=False,
                            )
                            session.add(entry)
                        entry_id += 1
        await session.commit()


if __name__ == "__main__":
    asyncio.run(scrape_and_store())
