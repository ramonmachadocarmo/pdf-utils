import uuid
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from app.api.routes import router
from app.config import APP_VERSION, STATIC
from app.services.storage_cleanup import purge_stale_jobs

# Regenerated every process start so browsers/webviews are forced to fetch fresh
# assets after an update, instead of silently reusing a cached copy of the old UI.
ASSET_VERSION = uuid.uuid4().hex[:10]

_VERSIONED_ASSETS = ("/static/styles.css", "/static/i18n.js", "/static/editor.js", "/static/app.js")


@asynccontextmanager
async def lifespan(app: FastAPI):
    purge_stale_jobs()
    yield


app = FastAPI(title="PDF Utils", version=APP_VERSION, lifespan=lifespan)
app.include_router(router)
app.mount("/static", StaticFiles(directory=STATIC), name="static")


@app.middleware("http")
async def no_cache_static(request: Request, call_next):
    """Force revalidation so the desktop webview never serves a stale UI after an update."""
    response = await call_next(request)
    if request.url.path == "/" or request.url.path.startswith("/static/"):
        response.headers["Cache-Control"] = "no-cache"
    return response


def _render_index() -> str:
    html = (STATIC / "index.html").read_text(encoding="utf-8")
    for asset in _VERSIONED_ASSETS:
        html = html.replace(f'"{asset}"', f'"{asset}?v={ASSET_VERSION}"')
    html = html.replace(
        "</head>", f'  <meta name="asset-version" content="{ASSET_VERSION}" />\n</head>'
    )
    return html


@app.get("/", response_class=HTMLResponse)
async def index():
    return HTMLResponse(_render_index())
