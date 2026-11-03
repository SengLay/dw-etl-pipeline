"""Application middleware configuration."""
import time
import uuid

from fastapi import FastAPI, Request

from src.common.logger import get_logger

log = get_logger("api")


def add_middleware(application: FastAPI) -> None:
    """Register middleware shared by every API route."""

    @application.middleware("http")
    async def request_context(request: Request, call_next):
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        started = time.perf_counter()
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Process-Time"] = f"{time.perf_counter() - started:.4f}"
        log.info("%s %s -> %s [%s]", request.method, request.url.path,
                 response.status_code, request_id)
        return response
