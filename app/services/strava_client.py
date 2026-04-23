import json
import math
import time
from datetime import datetime, timezone

import httpx
import aiosqlite

from app.config import settings

STRAVA_API = "https://www.strava.com/api/v3"
STRAVA_TOKEN_URL = "https://www.strava.com/oauth/token"

SPORT_TYPE_MAP = {
    "Run": "run",
    "TrailRun": "trail_run",
    "Walk": "walk",
    "Hike": "hike",
    "Ride": "ride",
    "VirtualRide": "ride",
    "WeightTraining": "strength",
    "Workout": "workout",
    "Swim": "swim",
    "Crossfit": "crossfit",
    "Rowing": "rowing",
    "Yoga": "yoga",
}


class StravaClient:
    def __init__(self, db: aiosqlite.Connection):
        self.db = db
        self._access_token: str | None = None
        self._refresh_token: str | None = None
        self._expires_at: int = 0

    async def _load_tokens(self) -> None:
        row = await (await self.db.execute(
            "SELECT access_token, refresh_token, expires_at FROM oauth_tokens WHERE source = 'strava'"
        )).fetchone()
        if row:
            self._access_token = row["access_token"]
            self._refresh_token = row["refresh_token"]
            self._expires_at = row["expires_at"]
        else:
            self._access_token = settings.STRAVA_ACCESS_TOKEN
            self._refresh_token = settings.STRAVA_REFRESH_TOKEN
            self._expires_at = 0  # Force refresh on first use

    async def _save_tokens(self, access_token: str, refresh_token: str, expires_at: int) -> None:
        await self.db.execute("""
            INSERT INTO oauth_tokens (source, access_token, refresh_token, expires_at)
            VALUES ('strava', ?, ?, ?)
            ON CONFLICT(source) DO UPDATE SET
                access_token  = excluded.access_token,
                refresh_token = excluded.refresh_token,
                expires_at    = excluded.expires_at
        """, (access_token, refresh_token, expires_at))
        await self.db.commit()
        self._access_token = access_token
        self._refresh_token = refresh_token
        self._expires_at = expires_at

    async def _get_valid_token(self) -> str:
        if not self._access_token:
            await self._load_tokens()
        if time.time() > self._expires_at - 300:
            await self._do_token_refresh()
        return self._access_token

    async def _do_token_refresh(self) -> None:
        async with httpx.AsyncClient() as client:
            resp = await client.post(STRAVA_TOKEN_URL, data={
                "client_id": settings.STRAVA_CLIENT_ID,
                "client_secret": settings.STRAVA_CLIENT_SECRET,
                "refresh_token": self._refresh_token,
                "grant_type": "refresh_token",
            })
            if not resp.is_success:
                raise Exception(f"Strava token refresh {resp.status_code}: {resp.text}")
            data = resp.json()
        await self._save_tokens(data["access_token"], data["refresh_token"], data["expires_at"])

    async def get_activities(self, after: int | None = None, per_page: int = 100) -> list[dict]:
        token = await self._get_valid_token()
        headers = {"Authorization": f"Bearer {token}"}
        activities: list[dict] = []
        page = 1

        async with httpx.AsyncClient() as client:
            while True:
                params: dict = {"per_page": per_page, "page": page}
                if after:
                    params["after"] = after
                resp = await client.get(
                    f"{STRAVA_API}/athlete/activities", headers=headers, params=params
                )
                resp.raise_for_status()
                batch = resp.json()
                if not batch:
                    break
                activities.extend(batch)
                if len(batch) < per_page:
                    break
                page += 1

        return activities


def calculate_trimp(duration_s: float, avg_hr: float, rest_hr: float, max_hr: float) -> float:
    if not all([duration_s, avg_hr, rest_hr, max_hr]) or max_hr <= rest_hr:
        return 0.0
    hr_ratio = (avg_hr - rest_hr) / (max_hr - rest_hr)
    if hr_ratio <= 0:
        return 0.0
    return (duration_s / 60) * hr_ratio * 0.64 * math.exp(1.92 * hr_ratio)


def map_strava_activity(raw: dict, rest_hr: float, max_hr: float) -> dict:
    sport_raw = raw.get("sport_type") or raw.get("type", "")
    sport_type = SPORT_TYPE_MAP.get(sport_raw, sport_raw.lower())

    distance_m = raw.get("distance") or 0.0
    moving_time_s = raw.get("moving_time") or 0
    avg_hr = raw.get("average_heartrate")

    pace = (moving_time_s / (distance_m / 1000)) if distance_m > 0 else None
    trimp = calculate_trimp(moving_time_s, avg_hr or 0, rest_hr, max_hr)

    polyline = None
    if raw.get("map"):
        polyline = raw["map"].get("summary_polyline") or raw["map"].get("polyline")

    return {
        "source": "strava",
        "external_id": str(raw["id"]),
        "name": raw.get("name"),
        "sport_type": sport_type,
        "start_date": raw.get("start_date"),
        "distance_m": distance_m,
        "moving_time_s": moving_time_s,
        "elapsed_time_s": raw.get("elapsed_time"),
        "elevation_gain_m": raw.get("total_elevation_gain"),
        "avg_heart_rate": avg_hr,
        "max_heart_rate": raw.get("max_heartrate"),
        "avg_pace_s_per_km": pace,
        "trimp": trimp if trimp > 0 else None,
        "tss": None,
        "map_polyline": polyline,
        "raw_json": json.dumps(raw),
    }
