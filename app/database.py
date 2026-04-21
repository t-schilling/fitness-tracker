import aiosqlite
from app.config import settings

DB_PATH = settings.DATABASE_PATH


async def get_db() -> aiosqlite.Connection:
    db = await aiosqlite.connect(DB_PATH)
    db.row_factory = aiosqlite.Row
    return db


async def init_db() -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.executescript("""
            CREATE TABLE IF NOT EXISTS athlete_profile (
                id          INTEGER PRIMARY KEY DEFAULT 1,
                name        TEXT,
                max_hr      INTEGER,
                rest_hr     INTEGER,
                hr_zones    TEXT,
                updated_at  TEXT
            );

            CREATE TABLE IF NOT EXISTS activities (
                id                INTEGER PRIMARY KEY AUTOINCREMENT,
                source            TEXT NOT NULL,
                external_id       TEXT NOT NULL,
                name              TEXT,
                sport_type        TEXT,
                start_date        TEXT,
                distance_m        REAL,
                moving_time_s     INTEGER,
                elapsed_time_s    INTEGER,
                elevation_gain_m  REAL,
                avg_heart_rate    REAL,
                max_heart_rate    REAL,
                avg_pace_s_per_km REAL,
                trimp             REAL,
                tss               REAL,
                map_polyline      TEXT,
                raw_json          TEXT,
                synced_at         TEXT,
                UNIQUE(source, external_id)
            );

            CREATE TABLE IF NOT EXISTS training_load (
                date        TEXT PRIMARY KEY,
                ctl         REAL,
                atl         REAL,
                tsb         REAL,
                daily_tss   REAL
            );

            CREATE TABLE IF NOT EXISTS gpx_analyses (
                id                   INTEGER PRIMARY KEY AUTOINCREMENT,
                filename             TEXT,
                uploaded_at          TEXT,
                total_distance_m     REAL,
                elevation_gain_m     REAL,
                elevation_loss_m     REAL,
                max_elevation_m      REAL,
                min_elevation_m      REAL,
                estimated_difficulty TEXT,
                key_segments         TEXT,
                elevation_profile    TEXT,
                ai_analysis          TEXT,
                gpx_raw              TEXT
            );

            CREATE TABLE IF NOT EXISTS strength_sessions (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                jefit_id     TEXT UNIQUE,
                workout_date TEXT,
                workout_name TEXT,
                exercises    TEXT,
                duration_min REAL,
                synced_at    TEXT
            );

            CREATE TABLE IF NOT EXISTS oauth_tokens (
                source        TEXT PRIMARY KEY,
                access_token  TEXT NOT NULL,
                refresh_token TEXT NOT NULL,
                expires_at    INTEGER NOT NULL
            );
        """)
        await db.commit()
