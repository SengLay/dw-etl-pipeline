"""FastAPI application factory."""
from contextlib import asynccontextmanager

from fastapi import FastAPI

from api.middleware import add_middleware
from api.routes import data, operations, system
from src.database.connection import init_db


def create_app() -> FastAPI:
    @asynccontextmanager
    async def lifespan(_: FastAPI):
        init_db()
        yield

    application = FastAPI(
        title="Instacart Data Warehouse API",
        version="1.0.0",
        description="Operational and read-only access to the ETL pipeline layers.",
        lifespan=lifespan,
    )
    add_middleware(application)
    application.include_router(system.router)
    application.include_router(data.router)
    application.include_router(operations.router)
    return application


app = create_app()
