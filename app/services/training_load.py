import math
from datetime import date, timedelta

import aiosqlite


# Decay constants for exponential weighted averages
_K_CTL = math.exp(-1 / 42)  # 42-day fitness
_K_ATL = math.exp(-1 / 7)   # 7-day fatigue


async def recalculate(db: aiosqlite.Connection) -> None:
    """Recompute CTL/ATL/TSB for all days and upsert into training_load."""
    daily_trimp = await _daily_trimp(db)
    if not daily_trimp:
        return

    first_day = min(daily_trimp)
    last_day = date.today()

    rows: list[tuple] = []
    ctl = atl = 0.0
    current = first_day

    while current <= last_day:
        trimp = daily_trimp.get(current, 0.0)
        ctl = ctl * _K_CTL + trimp * (1 - _K_CTL)
        atl = atl * _K_ATL + trimp * (1 - _K_ATL)
        tsb = ctl - atl
        rows.append((current.isoformat(), round(ctl, 2), round(atl, 2), round(tsb, 2), round(trimp, 2)))
        current += timedelta(days=1)

    await db.executemany("""
        INSERT INTO training_load (date, ctl, atl, tsb, daily_tss)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(date) DO UPDATE SET
            ctl       = excluded.ctl,
            atl       = excluded.atl,
            tsb       = excluded.tsb,
            daily_tss = excluded.daily_tss
    """, rows)
    await db.commit()


async def _daily_trimp(db: aiosqlite.Connection) -> dict[date, float]:
    """Sum TRIMP per calendar day across all activities."""
    rows = await (await db.execute("""
        SELECT date(start_date) AS day, SUM(trimp) AS total
        FROM activities
        WHERE trimp IS NOT NULL
        GROUP BY day
    """)).fetchall()
    return {date.fromisoformat(r["day"]): r["total"] for r in rows}
