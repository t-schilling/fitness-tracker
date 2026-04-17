from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

router = APIRouter()
templates = Jinja2Templates(directory="templates")


@router.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    # TODO: pull real stats from SQLite once sync is implemented
    stats = {
        "ctl": None,
        "atl": None,
        "tsb": None,
        "week_km": None,
        "week_elevation": None,
        "recent_activities": [],
    }
    return templates.TemplateResponse(
        request=request, name="dashboard.html", context={"stats": stats}
    )
