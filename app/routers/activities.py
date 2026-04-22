from fastapi import APIRouter, HTTPException, Request, Query
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
            SELECT id, name, sport_type, start_date, distance_m, moving_time_s,
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


def _hr_zones(avg_hr: float | None, max_hr: float | None, athlete_max: int = 190) -> dict:
    """Return HR zone info for the activity."""
    if not avg_hr:
        return {}
    pct_avg = avg_hr / athlete_max * 100
    pct_max = (max_hr / athlete_max * 100) if max_hr else None
    if pct_avg >= 90:
        zone, zone_label, zone_color = 5, "VO2 Máx", "#c44030"
    elif pct_avg >= 80:
        zone, zone_label, zone_color = 4, "Umbral", "#d98840"
    elif pct_avg >= 70:
        zone, zone_label, zone_color = 3, "Aeróbico", "#3dcc7a"
    elif pct_avg >= 60:
        zone, zone_label, zone_color = 2, "Base aeróbica", "#4b9dd6"
    else:
        zone, zone_label, zone_color = 1, "Recuperación", "#918d87"
    return {"zone": zone, "label": zone_label, "color": zone_color,
            "pct_avg": round(pct_avg, 1), "pct_max": round(pct_max, 1) if pct_max else None}


@router.get("/activities/{activity_id}", response_class=HTMLResponse)
async def activity_detail(request: Request, activity_id: int):
    db = await get_db()
    try:
        row = await (await db.execute("""
            SELECT id, source, external_id, name, sport_type, start_date,
                   distance_m, moving_time_s, elapsed_time_s, elevation_gain_m,
                   avg_heart_rate, max_heart_rate, avg_pace_s_per_km,
                   trimp, tss, map_polyline
            FROM activities WHERE id = ?
        """, (activity_id,))).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Actividad no encontrada")

        athlete = await (await db.execute(
            "SELECT max_hr, rest_hr FROM athlete_profile WHERE id = 1"
        )).fetchone()

        # Prev / next for navigation
        prev_row = await (await db.execute(
            "SELECT id FROM activities WHERE start_date < ? ORDER BY start_date DESC LIMIT 1",
            (row["start_date"],)
        )).fetchone()
        next_row = await (await db.execute(
            "SELECT id FROM activities WHERE start_date > ? ORDER BY start_date ASC LIMIT 1",
            (row["start_date"],)
        )).fetchone()

    finally:
        await db.close()

    athlete_max = (athlete["max_hr"] if athlete and athlete["max_hr"] else 190)
    act = dict(row)
    act["time_fmt"]   = _format_time(act["moving_time_s"])
    act["pace_fmt"]   = _format_pace(act["avg_pace_s_per_km"], act["sport_type"])
    act["sport_label"] = SPORT_LABELS.get(act["sport_type"], act["sport_type"] or "—")
    act["date_fmt"]   = (act["start_date"] or "")[:10]
    act["km"]         = round(act["distance_m"] / 1000, 2) if act["distance_m"] else None
    act["hr_zones"]   = _hr_zones(act["avg_heart_rate"], act["max_heart_rate"], athlete_max)
    pause = (act["elapsed_time_s"] or 0) - (act["moving_time_s"] or 0)
    act["pause_fmt"]  = _format_time(pause) if pause > 0 else "—"

    return templates.TemplateResponse(
        request=request,
        name="activity_detail.html",
        context={
            "act": act,
            "prev_id": prev_row["id"] if prev_row else None,
            "next_id": next_row["id"] if next_row else None,
        },
    )
