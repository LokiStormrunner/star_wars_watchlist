import json

from bs4 import BeautifulSoup, Tag

from models import CanonMediaEntry

with open("media_table.html") as html_file:
    soup = BeautifulSoup(html_file, "html.parser")

entries = []
entry_id = 0
for table in soup.find_all("table"):
    if not isinstance(table, Tag):
        continue
    headers = [
        th.get_text(strip=True) for th in table.find_all("th") if isinstance(th, Tag)
    ]
    if "Year" in headers and "Title" in headers and "Released" in headers:
        for row in table.find_all("tr")[1:]:
            if not isinstance(row, Tag):
                continue
            cells = [
                cell for cell in row.find_all(["td", "th"]) if isinstance(cell, Tag)
            ]
            if len(cells) >= 4:
                year = cells[0].get_text(strip=True)
                content_type = cells[1].get_text(strip=True)
                title = cells[2].get_text(strip=True)
                released = cells[3].get_text(strip=True)
                entry = CanonMediaEntry(
                    id=entry_id,
                    year=year or None,
                    content_type=content_type or None,
                    title=title,
                    released=released or None,
                    watched=False,
                ).model_dump()
                entries.append(entry)
                entry_id += 1

with open("canon_media.json", "w") as f:
    json.dump(entries, f, indent=2)
