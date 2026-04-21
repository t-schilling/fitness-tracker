from datetime import datetime, timezone

import aiosqlite

from app.services.strava_client import StravaClient, map_strava_activity
from app.services.training_load import recalculate

DEFAULT_MAX_HR = 190
DEFAULT_REST_HR = 50


async def _get_athlete_hr(db: aiosqlite.Connection) -> tuple[float, float]:
    row = await (await db.execute(
        "SELECT max_hr, rest_hr FROM athlete_profile WHERE id = 1"
    )).fetchone()
    if row:
        return row["max_hr"] or DEFAULT_MAX_HR, row["rest_hr"] or DEFAULT_REST_HR
    return DEFAULT_MAX_HR, DEFAULT_REST_HR


async def _get_last_strava_timestamp(db: aiosqlite.Connection) -> int | None:
    row = await (await db.execute(
        "SELECT start_date FROM activities WHERE source = 'strava' ORDER BY start_date DESC LIMIT 1"
    )).fetchone()
    if row and row["start_date"]:
        dt = datetime.fromisoformat(row["start_date"].replace("Z", "+00:00"))
        return int(dt.timestamp())
    return None


async def sync_strava(db: aiosqlite.Connection) -> int:
    """Sync Strava activities into SQLite. Returns count of newly inserted activities."""
    max_hr, rest_hr = await _get_athlete_hr(db)
    after = await _get_last_strava_timestamp(db)

    client = StravaClient(db)
    raw_activities = await client.get_activities(after=after)

    now = datetime.now(timezone.utc).isoformat()
    inserted = 0

    for raw in raw_activities:
        activity = map_strava_activity(raw, rest_hr, max_hr)
        try:
            await db.execute("""
                INSERT INTO activities (
                    source, external_id, name, sport_type, start_date,
                    distance_m, moving_time_s, elapsed_time_s, elevation_gain_m,
                    avg_heart_rate, max_heart_rate, avg_pace_s_per_km,
                    trimp, tss, map_polyline, raw_json, synced_at
                ) VALUES (
                    :source, :external_id, :name, :sport_type, :start_date,
                    :distance_m, :moving_time_s, :elapsed_time_s, :elevation_gain_m,
                    :avg_heart_rate, :max_heart_rate, :avg_pace_s_per_km,
                    :trimp, :tss, :map_polyline, :raw_json, :synced_at
                )
            """, {**activity, "synced_at": now})
            inserted += 1
        except aiosqlite.IntegrityError:
            pass  # Already exists, skip

    await db.commit()
    await recalculate(db)
    return inserted
