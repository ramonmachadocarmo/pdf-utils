from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api.routes import router
from app.config import APP_VERSION, STATIC
from app.services.storage_cleanup import purge_stale_jobs


@asynccontextmanager
async def lifespan(app: FastAPI):
    purge_stale_jobs()
    yield


app = FastAPI(title="PDF Utils", version=APP_VERSION, lifespan=lifespan)
app.include_router(router)
app.mount("/static", StaticFiles(directory=STATIC), name="static")


@app.get("/")
async def index():
    return FileResponse(STATIC / "index.html")
