from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.database import get_db
from app.services.sync_service import sync_strava

router = APIRouter()


@router.post("/sync")
async def sync():
    db = await get_db()
    try:
        count = await sync_strava(db)
        return JSONResponse({"synced": count}, status_code=200)
    except Exception as exc:
        return JSONResponse({"error": str(exc)}, status_code=500)
    finally:
        await db.close()
