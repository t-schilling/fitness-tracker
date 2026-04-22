from fastapi import APIRouter, Request, Query
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app.database import get_db

router = APIRouter()
templates = Jinja2Templates(directory="templates")

PAGE_SIZE = 50

SPORT_LABELS = {
    "run":       "Running",
    "trail_run": "Trail Run",
    "strength":  "Fuerza",
    "ride":      "Ciclismo",
    "walk":      "Caminata",
    "hike":      "Senderismo",
    "swim":      "Natación",
    "workout":   "Workout",
    "crossfit":  "Crossfit",
    "rowing":    "Remo",
    "yoga":      "Yoga",
}

PACE_SPORTS = {"run", "trail_run", "walk", "hike"}


def _format_time(seconds: int | None) -> str:
    if not seconds:
        return "—"
    h, rem = divmod(int(seconds), 3600)
    m, s = divmod(rem, 60)
    return f"{h}h {m:02d}m" if h else f"{m}:{s:02d}"


def _format_pace(s_per_km: float | None, sport_type: str | None) -> str:
    if not s_per_km or sport_type not in PACE_SPORTS:
        return "—"
    m, s = divmod(int(s_per_km), 60)
    return f"{m}:{s:02d} /km"


def _build_where(sport: str, date_from: str, date_to: str) -> tuple[str, list]:
    clauses, params = [], []
    if sport:
        clauses.append("sport_type = ?")
        params.append(sport)
    if date_from:
        clauses.append("start_date >= ?")
        params.append(date_from)
    if date_to:
        clauses.append("start_date <= ?")
        params.append(date_to + "T23:59:59Z")
    where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
    return where, params


@router.get("/activities", response_class=HTMLResponse)
async def activities_list(
    request: Request,
    sport: str = "",
    date_from: str = "",
    date_to: str = "",
    page: int = Query(1, ge=1),
):
    db = await get_db()
    try:
        sport_rows = await (await db.execute(
            "SELECT DISTINCT sport_type FROM activities ORDER BY sport_type"
        )).fetchall()
        sports = [r["sport_type"] for r in sport_rows if r["sport_type"]]

        where, params = _build_where(sport, date_from, date_to)

        count_row = await (await db.execute(
            f"SELECT COUNT(*) FROM activities {where}", params
        )).fetchone()
        total = count_row[0]
        total_pages = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)
        offset = (page - 1) * PAGE_SIZE

        rows = await (await db.execute(f"""
            SELECT name, sport_type, start_date, distance_m, moving_time_s,
                   elevation_gain_m, avg_heart_rate, avg_pace_s_per_km, trimp
            FROM activities {where}
            ORDER BY start_date DESC
            LIMIT ? OFFSET ?
        """, params + [PAGE_SIZE, offset])).fetchall()

        agg = await (await db.execute(f"""
            SELECT COALESCE(SUM(distance_m)/1000,0) AS km,
                   COALESCE(SUM(moving_time_s),0)   AS secs,
                   COUNT(*)                          AS sessions
            FROM activities {where}
        """, params)).fetchone()

    finally:
        await db.close()

    activities = []
    for r in rows:
        d = dict(r)
        d["time_fmt"] = _format_time(d["moving_time_s"])
        d["pace_fmt"] = _format_pace(d["avg_pace_s_per_km"], d["sport_type"])
        d["sport_label"] = SPORT_LABELS.get(d["sport_type"], d["sport_type"] or "—")
        d["date_fmt"] = (d["start_date"] or "")[:10]
        d["km"] = round(d["distance_m"] / 1000, 2) if d["distance_m"] else None
        activities.append(d)

    total_hours, rem = divmod(int(agg["secs"]), 3600)
    total_min = rem // 60

    return templates.TemplateResponse(
        request=request,
        name="activities.html",
        context={
            "activities": activities,
            "sports": sports,
            "sport_labels": SPORT_LABELS,
            "active_sport": sport,
            "date_from": date_from,
            "date_to": date_to,
            "page": page,
            "total_pages": total_pages,
            "total": total,
            "agg": {
                "km": round(agg["km"], 1),
                "time": f"{total_hours}h {total_min:02d}m",
                "sessions": agg["sessions"],
            },
        },
    )
