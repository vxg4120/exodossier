"""FastAPI application entrypoint. ``uvicorn api.main:app --port 8700`` / ``TestClient(app)``.

Wires the read-only routers under ``/api`` and, when a built SPA exists at ``web/dist``, serves it
statically at ``/`` for single-process demo mode (the API routers are registered first, so
``/api/*`` always wins the match; unknown ``/api/*`` paths keep their real JSON 404 rather than the
SPA shell). CORS is open for GET so third-party sites and agents can read the public catalog.

This is the conflict-aware provenance layer: it surfaces where the exoplanet archives disagree,
with full provenance — it does not yet adjudicate or confirm.
"""

import pathlib

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routers import attribution, conflicts, search, stats, target, twoskies

app = FastAPI(
    title="ExoDossier — Exoplanet Conflict Explorer API",
    description=(
        "Read-only JSON API over the ExoDossier identity graph: canonical stars/candidates, the "
        "full TIC/TOI/CTOI/KOI/Gaia crosswalk, per-source assertions, and the cross-source "
        "conflict corpus. Surfaces disagreement with provenance; does not adjudicate."
    ),
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "OPTIONS"],
    allow_headers=["*"],
)

app.include_router(stats.router, prefix="/api")
app.include_router(search.router, prefix="/api")
app.include_router(target.router, prefix="/api")
app.include_router(conflicts.router, prefix="/api")
app.include_router(attribution.router, prefix="/api")
app.include_router(twoskies.router, prefix="/api")


@app.get("/api/health", tags=["health"])
def health():
    return {"status": "ok", "service": "exodossier-api"}


_WEB_DIST = pathlib.Path(__file__).resolve().parent.parent / "web" / "dist"
if (_WEB_DIST / "index.html").exists():
    from fastapi.staticfiles import StaticFiles

    class _SpaStaticFiles(StaticFiles):
        """StaticFiles that falls back to index.html so SPA deep links survive a hard refresh,
        while unknown ``/api/*`` paths keep their real JSON 404 instead of the SPA shell."""

        async def get_response(self, path, scope):
            from starlette.exceptions import HTTPException as StarletteHTTPException

            is_api = path == "api" or path.startswith("api/")
            try:
                response = await super().get_response(path, scope)
            except StarletteHTTPException as exc:
                if is_api or exc.status_code != 404:
                    raise
                return await super().get_response("index.html", scope)
            if response.status_code == 404 and not is_api:
                response = await super().get_response("index.html", scope)
            return response

    app.mount("/", _SpaStaticFiles(directory=str(_WEB_DIST), html=True), name="spa")
