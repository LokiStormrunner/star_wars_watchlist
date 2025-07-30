import asyncio
import json
import os

import aiohttp
from bs4 import BeautifulSoup, Tag
from sqlalchemy.future import select

from db import AsyncSessionLocal
from models import CanonMediaEntry

OUTPUT_DIR = "episode_pages"
os.makedirs(OUTPUT_DIR, exist_ok=True)


async def fetch_and_extract(session, url, entry_id):
    try:
        async with session.get(url) as resp:
            if resp.status == 200:
                html = await resp.text()
                # Extract season and episode number from the HTML
                soup = BeautifulSoup(html, "html.parser")
                season = None
                episode = None
                # Try to find season and episode info in infobox or headings
                infobox = soup.find(class_="infobox")
                if infobox and hasattr(infobox, "find_all"):
                    for row in infobox.find_all("tr"):
                        if hasattr(row, "find"):
                            header = row.find("th") if hasattr(row, "find") else None
                            value = row.find("td") if hasattr(row, "find") else None
                            if (
                                header
                                and value
                                and hasattr(header, "get_text")
                                and hasattr(value, "get_text")
                            ):
                                h_text = header.get_text(strip=True).lower()
                                if "season" in h_text:
                                    season = value.get_text(strip=True)
                                if "episode" in h_text:
                                    episode = value.get_text(strip=True)
                # Fallback: look for headings or other patterns
                if not season or not episode:
                    for tag in soup.find_all(["h2", "h3", "h4"]):
                        if hasattr(tag, "get_text"):
                            t = tag.get_text(strip=True).lower()
                            if "season" in t and not season:
                                season = t
                            if "episode" in t and not episode:
                                episode = t
                # Extract season and episode from pi-item divs
                season_div = soup.find("div", attrs={"data-source": "season"})
                episode_div = soup.find("div", attrs={"data-source": "episode"})

                def normalize_season(season_text):
                    lookup = {
                        "one": "01",
                        "two": "02",
                        "three": "03",
                        "four": "04",
                        "five": "05",
                        "six": "06",
                        "seven": "07",
                        "eight": "08",
                        "nine": "09",
                        "ten": "10",
                    }
                    s = season_text.strip().lower()
                    return lookup.get(s, s.zfill(2))

                if isinstance(season_div, Tag):
                    val = season_div.find("div", attrs={"class": "pi-data-value"})
                    if isinstance(val, Tag):
                        a = val.find("a")
                        season_raw = (
                            a.get_text(strip=True)
                            if isinstance(a, Tag)
                            else val.get_text(strip=True)
                        )
                        if season_raw:
                            season = f"S{normalize_season(season_raw)}"
                if isinstance(episode_div, Tag):
                    val = episode_div.find("div", attrs={"class": "pi-data-value"})
                    if isinstance(val, Tag):
                        import re

                        match = re.search(r"\d+", val.get_text())
                        if match:
                            episode = f"E{int(match.group(0)):02d}"
                print(
                    f"Entry {entry_id}: season={season}, episode={episode}, url={url}"
                )
            else:
                print(f"Failed to fetch {url}: {resp.status}")
    except Exception as e:
        print(f"Error fetching {url}: {e}")


async def scrape_episode_urls():
    async with AsyncSessionLocal() as db_session:
        result = await db_session.execute(select(CanonMediaEntry))
        entries = result.scalars().all()
        async with aiohttp.ClientSession() as http_session:
            tasks = []
            for entry in entries:
                if getattr(entry, "episode_url", None):
                    tasks.append(
                        fetch_and_extract(http_session, entry.episode_url, entry.id)
                    )
            await asyncio.gather(*tasks)


if __name__ == "__main__":
    asyncio.run(scrape_episode_urls())
