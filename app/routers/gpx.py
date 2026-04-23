import json
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Request, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from app.database import get_db
from app.services.gpx_processor import process_gpx

router = APIRouter()
templates = Jinja2Templates(directory="templates")

DIFFICULTY_LABELS = {
    "easy":     "Fácil",
    "moderate": "Moderada",
    "hard":     "Difícil",
    "extreme":  "Extrema",
}

DIFFICULTY_COLORS = {
    "easy":     "#3dcc7a",
    "moderate": "#4b9dd6",
    "hard":     "#d98840",
    "extreme":  "#c44030",
}


def _enrich(d: dict) -> dict:
    d["km"] = round(d["total_distance_m"] / 1000, 2) if d["total_distance_m"] else None
    d["gain"] = round(d["elevation_gain_m"]) if d["elevation_gain_m"] else None
    d["difficulty_label"] = DIFFICULTY_LABELS.get(d["estimated_difficulty"], "—")
    d["difficulty_color"] = DIFFICULTY_COLORS.get(d["estimated_difficulty"], "#918d87")
    d["date_fmt"] = (d["uploaded_at"] or "")[:10]
    return d


@router.get("/gpx", response_class=HTMLResponse)
async def gpx_list(request: Request):
    db = await get_db()
    try:
        rows = await (await db.execute("""
            SELECT id, filename, uploaded_at, total_distance_m,
                   elevation_gain_m, estimated_difficulty
            FROM gpx_analyses ORDER BY uploaded_at DESC
        """)).fetchall()
    finally:
        await db.close()

    routes = [_enrich(dict(r)) for r in rows]
    return templates.TemplateResponse(request=request, name="gpx.html", context={"routes": routes})


@router.post("/gpx/upload", response_class=HTMLResponse)
async def gpx_upload(request: Request, file: UploadFile = File(...)):
    if not file.filename or not file.filename.lower().endswith(".gpx"):
        raise HTTPException(status_code=400, detail="Solo se aceptan archivos .gpx")

    content = await file.read()
    try:
        gpx_str = content.decode("utf-8")
        metrics = process_gpx(gpx_str)
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"Error procesando GPX: {exc}")

    db = await get_db()
    try:
        now = datetime.now(timezone.utc).isoformat()
        cursor = await db.execute("""
            INSERT INTO gpx_analyses (
                filename, uploaded_at, total_distance_m, elevation_gain_m,
                elevation_loss_m, max_elevation_m, min_elevation_m,
                estimated_difficulty, elevation_profile, key_segments, gpx_raw
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            file.filename, now,
            metrics["total_distance_m"], metrics["elevation_gain_m"],
            metrics["elevation_loss_m"], metrics["max_elevation_m"],
            metrics["min_elevation_m"], metrics["estimated_difficulty"],
            metrics["elevation_profile"], metrics["coords"],
            gpx_str,
        ))
        new_id = cursor.lastrowid
        await db.commit()
    finally:
        await db.close()

    return RedirectResponse(url=f"/gpx/{new_id}", status_code=303)


@router.get("/gpx/{gpx_id}", response_class=HTMLResponse)
async def gpx_detail(request: Request, gpx_id: int):
    db = await get_db()
    try:
        row = await (await db.execute("""
            SELECT id, filename, uploaded_at, total_distance_m, elevation_gain_m,
                   elevation_loss_m, max_elevation_m, min_elevation_m,
                   estimated_difficulty, elevation_profile, key_segments
            FROM gpx_analyses WHERE id = ?
        """, (gpx_id,))).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Ruta no encontrada")
    finally:
        await db.close()

    route = _enrich(dict(row))
    route["loss"] = round(route["elevation_loss_m"]) if route["elevation_loss_m"] else None
    profile = json.loads(route["elevation_profile"] or "[]")
    coords_json = route["key_segments"] or "[]"

    return templates.TemplateResponse(request=request, name="gpx_detail.html", context={
        "route": route,
        "profile": profile,
        "coords_json": coords_json,
    })
