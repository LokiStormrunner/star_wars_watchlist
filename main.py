import asyncio
import re
from typing import List, Optional

from fastapi import FastAPI, Form, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.future import select

from db import AsyncSessionLocal
from models import CanonMediaEntry, CanonMediaEntrySchema

app = FastAPI()


async def get_all_media():
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(CanonMediaEntry))
        return result.scalars().all()


async def save_media_entry(entry):
    async with AsyncSessionLocal() as session:
        session.add(entry)
        await session.commit()


def parse_year(year_str):
    if not year_str:
        return None
    match = re.search(r"(-?\d+)(?:\s*(BBY|ABY))?", year_str)
    if match:
        value = int(match.group(1))
        era = match.group(2)
        # BBY is negative, ABY is positive
        if era == "BBY":
            return -abs(value)
        elif era == "ABY":
            return abs(value)
        else:
            return value
    return None


@app.get("/")
def read_root():
    return {"message": "Hello, FastAPI World!"}


@app.get("/media", response_model=List[CanonMediaEntrySchema])
async def get_media(
    content_type: Optional[List[str]] = Query(None),
    watched: Optional[bool] = Query(None),
    id_gt: Optional[int] = Query(None),
    id_lt: Optional[int] = Query(None),
):
    media_data = await get_all_media()
    # Convert to Pydantic models for safe attribute access
    result = [CanonMediaEntrySchema.model_validate(m) for m in media_data]
    if content_type:
        result = [m for m in result if m.content_type in content_type]
    if watched is not None:
        result = [m for m in result if m.watched == watched]
    if id_gt is not None:
        result = [m for m in result if m.id is not None and m.id > id_gt]
    if id_lt is not None:
        result = [m for m in result if m.id is not None and m.id < id_lt]
    return result


@app.post("/media/{media_id}/watched")
async def update_watched(
    media_id: int, watched: bool = Form(...), request: Request = None
):
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(CanonMediaEntry).where(CanonMediaEntry.id == media_id)
        )
        entry = result.scalar_one_or_none()
        if entry:
            setattr(entry, "watched", watched)
            await session.commit()
        else:
            raise HTTPException(status_code=404, detail="Media entry not found")
    # Preserve query parameters in redirect
    query_string = request.headers.get("referer", "")
    if "?" in query_string:
        params = query_string.split("?", 1)[1]
        return RedirectResponse(url=f"/media/table?{params}", status_code=303)
    return RedirectResponse(url="/media/table", status_code=303)


@app.get("/media/table", response_class=HTMLResponse)
async def media_table(
    request: Request,
    content_type: Optional[List[str]] = Query(None),
    watched: Optional[str] = Query(None),
    id_gt: Optional[str] = Query(None),
    id_lt: Optional[str] = Query(None),
):
    media_data = await get_all_media()
    entries = [CanonMediaEntrySchema.model_validate(m) for m in media_data]
    filtered = entries
    types = sorted(set(m.content_type for m in entries if m.content_type))
    selected_types = request.query_params.getlist("content_type")
    # Handle empty/All for filters
    content_type_val = (
        selected_types if selected_types and any(selected_types) else None
    )
    watched_val = None
    if watched == "true":
        watched_val = True
    elif watched == "false":
        watched_val = False
    id_gt_val = int(id_gt) if id_gt and id_gt.strip() else None
    id_lt_val = int(id_lt) if id_lt and id_lt.strip() else None
    if content_type_val:
        filtered = [m for m in filtered if m.content_type in content_type_val]
    if watched_val is not None:
        filtered = [m for m in filtered if m.watched == watched_val]
    if id_gt_val is not None:
        filtered = [m for m in filtered if m.id is not None and m.id > id_gt_val]
    if id_lt_val is not None:
        filtered = [m for m in filtered if m.id is not None and m.id < id_lt_val]
    table_html = """
    <form method='get'>
        <label>Filter by type:</label>
        <select name='content_type' multiple size='10' onchange='if([...this.options].every(opt=>!opt.selected)){this.form.removeAttribute("action");this.form.submit();}else{this.form.submit();}'>
    """
    for t in types:
        selected = "selected" if t in selected_types else ""
        table_html += f"<option value='{t}' {selected}>{t}</option>"
    table_html += """
        </select>
        <label>Watched:</label>
        <select name='watched' onchange='if(this.value==""){{this.form.removeAttribute("action");this.form.submit();}}else{{this.form.submit();}}'>
            <option value=''>All</option>
            <option value='true' {}>Watched</option>
            <option value='false' {}>Unwatched</option>
        </select>
        <label>ID greater than:</label>
        <input type='number' name='id_gt' value='{}' onchange='if(this.value==""){{this.form.removeAttribute("action");this.form.submit();}}else{{this.form.submit();}}'>
        <label>ID less than:</label>
        <input type='number' name='id_lt' value='{}' onchange='if(this.value==""){{this.form.removeAttribute("action");this.form.submit();}}else{{this.form.submit();}}'>
    </form>
    <table border='1'>
        <tr><th>ID</th><th>Year</th><th>Type</th><th>Title</th><th>Released</th><th>Watched</th><th>Action</th></tr>
    """.format(
        "selected" if watched_val is True else "",
        "selected" if watched_val is False else "",
        id_gt if id_gt is not None else "",
        id_lt if id_lt is not None else "",
    )
    for m in filtered:
        # Add current query string to form action for watched toggle
        query_str = request.url.query
        action_url = f"/media/{m.id}/watched"
        if query_str:
            action_url += f"?{query_str}"
        table_html += f"<tr><td>{m.id}</td><td>{m.year}</td><td>{m.content_type}</td><td>{m.title}{f' -- {m.episode_title}' if m.episode_title else ''}</td><td>{m.released}</td><td>{'Yes' if m.watched else 'No'}</td>"
        table_html += f"<td><form method='post' action='{action_url}'><input type='hidden' name='watched' value='{str(not m.watched).lower()}'><button type='submit'>{'Mark Unwatched' if m.watched else 'Mark Watched'}</button></form></td></tr>"
    table_html += "</table>"
    return table_html
