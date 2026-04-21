from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates

from app.database import get_db

router = APIRouter(prefix="/training")
templates = Jinja2Templates(directory="templates")


@router.get("", response_class=HTMLResponse)
async def training_page(request: Request):
    db = await get_db()
    try:
        row = await (await db.execute(
            "SELECT ctl, atl, tsb FROM training_load ORDER BY date DESC LIMIT 1"
        )).fetchone()
    finally:
        await db.close()
    current = dict(row) if row else {"ctl": None, "atl": None, "tsb": None}
    return templates.TemplateResponse(
        request=request, name="training.html", context={"current": current}
    )


@router.get("/data")
async def training_data(days: int = 90):
    """Return CTL/ATL/TSB series for the last N days as JSON for Chart.js."""
    db = await get_db()
    try:
        rows = await (await db.execute("""
            SELECT date, ctl, atl, tsb, daily_tss
            FROM training_load
            ORDER BY date DESC
            LIMIT ?
        """, (days,))).fetchall()
    finally:
        await db.close()

    # Reverse so chart goes oldest → newest
    data = [dict(r) for r in reversed(rows)]
    return JSONResponse({
        "labels": [r["date"] for r in data],
        "ctl":    [r["ctl"] for r in data],
        "atl":    [r["atl"] for r in data],
        "tsb":    [r["tsb"] for r in data],
        "load":   [r["daily_tss"] for r in data],
    })
