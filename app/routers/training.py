from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.database import get_db

router = APIRouter(prefix="/training")


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
