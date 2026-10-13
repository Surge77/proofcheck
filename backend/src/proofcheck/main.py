import logging
from pathlib import Path

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.trustedhost import TrustedHostMiddleware

from proofcheck.api import router
from proofcheck.config import get_settings
from proofcheck.guard import OriginGuard, allowed_origins, host_guard_hosts
from proofcheck.limits import BodySizeLimit

# The built frontend is served from the same port, so the app is a single local address.
FRONTEND_DIST = Path(__file__).resolve().parents[3] / "frontend" / "dist"
DEV_ORIGINS = ["http://localhost:5173", "http://127.0.0.1:5173"]


def _mount_frontend(app: FastAPI) -> None:
    app.mount("/assets", StaticFiles(directory=FRONTEND_DIST / "assets"), name="assets")

    @app.get("/{path:path}", include_in_schema=False)
    async def spa(path: str) -> FileResponse:
        if path.startswith("api/"):
            raise HTTPException(status_code=404, detail="Not found")
        try:
            candidate = (FRONTEND_DIST / path).resolve()
        except (OSError, ValueError):  # e.g. a null byte in the path
            candidate = FRONTEND_DIST / "index.html"
        if path and candidate.is_file() and candidate.is_relative_to(FRONTEND_DIST):
            return FileResponse(candidate)
        return FileResponse(FRONTEND_DIST / "index.html")


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="ProofCheck", version="0.1.0")
    app.add_middleware(
        CORSMiddleware, allow_origins=DEV_ORIGINS, allow_methods=["*"], allow_headers=["*"]
    )
    app.add_middleware(BodySizeLimit)
    app.add_middleware(OriginGuard, origins=allowed_origins(settings, DEV_ORIGINS))
    # Added last, so it runs first: refuse foreign Host headers before anything else.
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=host_guard_hosts(settings))
    app.include_router(router)
    if (FRONTEND_DIST / "assets").is_dir():
        _mount_frontend(app)
    return app


app = create_app()


def run() -> None:
    logging.basicConfig(level=logging.INFO)
    settings = get_settings()
    uvicorn.run("proofcheck.main:app", host=settings.host, port=settings.port)
