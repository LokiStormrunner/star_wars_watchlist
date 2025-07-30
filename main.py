import json
import re
from typing import List, Optional

from fastapi import FastAPI, Form, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from models import CanonMediaEntry

app = FastAPI()

# Load data from JSON
with open("canon_media.json") as f:
    media_data = [CanonMediaEntry(**entry) for entry in json.load(f)]


def save_media():
    with open("canon_media.json", "w") as f:
        json.dump([m.model_dump() for m in media_data], f, indent=2)


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


@app.get("/media", response_model=List[CanonMediaEntry])
def get_media(
    content_type: Optional[List[str]] = Query(None),
    watched: Optional[bool] = Query(None),
    id_gt: Optional[int] = Query(None),
    id_lt: Optional[int] = Query(None),
):
    result = media_data
    if content_type:
        result = [m for m in result if m.content_type in content_type]
    if watched is not None:
        result = [m for m in result if m.watched == watched]
    if id_gt is not None:
        result = [m for m in result if m.id > id_gt]
    if id_lt is not None:
        result = [m for m in result if m.id < id_lt]
    return result


@app.post("/media/{media_id}/watched")
def update_watched(media_id: int, watched: bool = Form(...)):
    for m in media_data:
        if m.id == media_id:
            m.watched = watched
            save_media()
            break
    else:
        raise HTTPException(status_code=404, detail="Media entry not found")
    return RedirectResponse(url="/media/table", status_code=303)


@app.get("/media/table", response_class=HTMLResponse)
def media_table(
    request: Request,
    content_type: Optional[List[str]] = Query(None),
    watched: Optional[bool] = Query(None),
    id_gt: Optional[int] = Query(None),
    id_lt: Optional[int] = Query(None),
):
    filtered = media_data
    types = sorted(set(m.content_type for m in media_data if m.content_type))
    if content_type:
        filtered = [m for m in filtered if m.content_type in content_type]
    if watched is not None:
        filtered = [m for m in filtered if m.watched == watched]
    if id_gt is not None:
        filtered = [m for m in filtered if m.id > id_gt]
    if id_lt is not None:
        filtered = [m for m in filtered if m.id < id_lt]
    selected_types = request.query_params.getlist("content_type")
    table_html = f"""
    <form method='get'>
        <label>Filter by type:</label>
        <select name='content_type' multiple size='{len(types)}' onchange='this.form.submit()'>
    """
    for t in types:
        selected = "selected" if t in selected_types else ""
        table_html += f"<option value='{t}' {selected}>{t}</option>"
    table_html += """
        </select>
        <label>Watched:</label>
        <select name='watched' onchange='this.form.submit()'>
            <option value=''>All</option>
            <option value='true' {}>Watched</option>
            <option value='false' {}>Unwatched</option>
        </select>
        <label>ID greater than:</label>
        <input type='number' name='id_gt' value='{}' onchange='this.form.submit()'>
        <label>ID less than:</label>
        <input type='number' name='id_lt' value='{}' onchange='this.form.submit()'>
    </form>
    <table border='1'>
        <tr><th>ID</th><th>Year</th><th>Type</th><th>Title</th><th>Released</th><th>Watched</th><th>Action</th></tr>
    """.format(
        "selected" if watched is True else "",
        "selected" if watched is False else "",
        id_gt if id_gt is not None else "",
        id_lt if id_lt is not None else "",
    )
    for m in filtered:
        table_html += f"<tr><td>{m.id}</td><td>{m.year}</td><td>{m.content_type}</td><td>{m.title}</td><td>{m.released}</td><td>{'Yes' if m.watched else 'No'}</td>"
        table_html += f"<td><form method='post' action='/media/{m.id}/watched'><input type='hidden' name='watched' value='{str(not m.watched).lower()}'><button type='submit'>{'Mark Unwatched' if m.watched else 'Mark Watched'}</button></form></td></tr>"
    table_html += "</table>"
    return table_html
