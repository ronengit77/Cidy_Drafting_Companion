from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from cidy_api.config import get_settings
from cidy_api.routers import artifacts as artifacts_router
from cidy_api.routers import assist as assist_router
from cidy_api.routers import auth as auth_router
from cidy_api.routers import collaborators as collaborators_router
from cidy_api.routers import me as me_router
from cidy_api.routers import schemas as schemas_router


def create_app() -> FastAPI:
    app = FastAPI(title="CIdy Drafting Companion API")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=get_settings().cors_origins,
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    app.include_router(artifacts_router.router)
    app.include_router(assist_router.router)
    app.include_router(auth_router.router)
    app.include_router(collaborators_router.router)
    app.include_router(me_router.router)
    app.include_router(schemas_router.router)
    return app
