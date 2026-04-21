from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.config import settings
from app.database import init_db
from app.routers import dashboard, sync

templates = Jinja2Templates(directory="templates")


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


app = FastAPI(title="Fitness Tracker", lifespan=lifespan)

app.mount("/static", StaticFiles(directory="static"), name="static")

app.include_router(dashboard.router)
app.include_router(sync.router)


# Temporary route to capture Strava OAuth code — remove after setup
@app.get("/strava-callback", response_class=HTMLResponse)
async def strava_callback(request: Request, code: str = "", error: str = ""):
    if error:
        return HTMLResponse(f"<h2>Error: {error}</h2>")
    import httpx
    async with httpx.AsyncClient() as client:
        resp = await client.post("https://www.strava.com/oauth/token", data={
            "client_id": settings.STRAVA_CLIENT_ID,
            "client_secret": settings.STRAVA_CLIENT_SECRET,
            "code": code,
            "grant_type": "authorization_code",
        })
    data = resp.json()
    if "access_token" not in data:
        return HTMLResponse(f"<pre>Error: {data}</pre>")
    return HTMLResponse(f"""
        <h2>Tokens obtenidos — copia al .env</h2>
        <pre>
STRAVA_ACCESS_TOKEN={data['access_token']}
STRAVA_REFRESH_TOKEN={data['refresh_token']}
        </pre>
        <p>expires_at: {data['expires_at']}</p>
    """)
