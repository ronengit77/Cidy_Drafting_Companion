from __future__ import annotations

from fastapi import FastAPI

from cidy_api.routers import auth as auth_router
from cidy_api.routers import collaborators as collaborators_router
from cidy_api.routers import me as me_router
from cidy_api.routers import schemas as schemas_router


def create_app() -> FastAPI:
    app = FastAPI(title="CIdy Drafting Companion API")

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    app.include_router(auth_router.router)
    app.include_router(collaborators_router.router)
    app.include_router(me_router.router)
    app.include_router(schemas_router.router)
    return app
