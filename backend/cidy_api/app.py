from __future__ import annotations

from fastapi import FastAPI

from cidy_api.routers import auth as auth_router


def create_app() -> FastAPI:
    app = FastAPI(title="CIdy Drafting Companion API")

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    app.include_router(auth_router.router)
    return app
