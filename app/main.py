from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routers import analytics, meta


def create_app() -> FastAPI:
    app = FastAPI(
        title="Work Orders Analytics API",
        description="Read-only API over the workorders_dwh star schema",
        version="1.0.0",
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(meta.router)
    app.include_router(analytics.router)
    return app


app = create_app()