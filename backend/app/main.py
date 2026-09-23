from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.features.health.router import router as health_router


def create_app() -> FastAPI:
    app = FastAPI(title="FPLPatternRec")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:8455"],
        allow_credentials=False,
        allow_methods=["GET"],
        allow_headers=["Content-Type"],
    )
    app.include_router(health_router)
    return app


app = create_app()
