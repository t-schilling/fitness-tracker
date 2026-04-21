from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app.database import get_db

router = APIRouter()
templates = Jinja2Templates(directory="templates")


def _week_bounds() -> tuple[str, str]:
    today = datetime.now(timezone.utc)
    monday = today - timedelta(days=today.weekday())
    start = monday.replace(hour=0, minute=0, second=0, microsecond=0)
    end = start + timedelta(days=7)
    return start.isoformat(), end.isoformat()


@router.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    db = await get_db()
    try:
        stats = await _build_stats(db)
    finally:
        await db.close()

    return templates.TemplateResponse(
        request=request, name="dashboard.html", context={"stats": stats}
    )


async def _build_stats(db) -> dict:
    week_start, week_end = _week_bounds()

    # Weekly aggregates
    row = await (await db.execute("""
        SELECT
            COALESCE(SUM(distance_m) / 1000.0, 0)  AS km,
            COALESCE(SUM(elevation_gain_m), 0)      AS elevation,
            COUNT(*)                                 AS sessions,
            COALESCE(SUM(moving_time_s) / 3600.0, 0) AS hours
        FROM activities
        WHERE start_date >= ? AND start_date < ?
    """, (week_start, week_end))).fetchone()

    week_km       = round(row["km"], 1)       if row else 0
    week_elevation = int(row["elevation"])    if row else 0
    week_sessions  = row["sessions"]          if row else 0
    week_time      = round(row["hours"], 1)   if row else 0

    # Recent activities (last 5)
    rows = await (await db.execute("""
        SELECT name, sport_type, start_date, distance_m,
               avg_pace_s_per_km, elevation_gain_m, avg_heart_rate
        FROM activities
        ORDER BY start_date DESC
        LIMIT 5
    """)).fetchall()
    recent = [dict(r) for r in rows]

    # Training load (latest entry)
    tl = await (await db.execute("""
        SELECT ctl, atl, tsb FROM training_load ORDER BY date DESC LIMIT 1
    """)).fetchone()

    return {
        "ctl": tl["ctl"] if tl else None,
        "atl": tl["atl"] if tl else None,
        "tsb": tl["tsb"] if tl else None,
        "week_km":        week_km,
        "week_elevation": week_elevation,
        "week_sessions":  week_sessions,
        "week_time":      week_time,
        "recent_activities": recent,
    }
