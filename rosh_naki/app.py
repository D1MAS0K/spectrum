"""Rosh Naki - ראש נקי - Main FastAPI application.

Cannabis sobriety tracking app for the Israeli community.
Founded by Niv Ifergan.
"""

from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from .database import init_db
from .routers import auth, community, pledges, tracker

BASE_DIR = Path(__file__).resolve().parent

app = FastAPI(
    title="ראש נקי - Rosh Naki",
    description="אפליקציית גמילה מקנאביס של קהילת ראש נקי בהנהגת ניב איפרגן",
    version="1.0.0",
)

# Mount static files
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")

# Templates
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

# Include routers
app.include_router(auth.router)
app.include_router(tracker.router)
app.include_router(pledges.router)
app.include_router(community.router)


@app.on_event("startup")
def on_startup():
    init_db()


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/app", response_class=HTMLResponse)
async def dashboard(request: Request):
    return templates.TemplateResponse("dashboard.html", {"request": request})


@app.get("/health")
async def health():
    return {"status": "ok", "app": "ראש נקי", "version": "1.0.0"}
