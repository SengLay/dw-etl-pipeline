"""System and health endpoints."""
from typing import Any

from fastapi import APIRouter, HTTPException, Response
from config.settings import settings

from api.services.pipeline import database_is_available

router = APIRouter(tags=["system"])


# @router.get("/")
# def root() -> dict[str, str]:
#     return {"name": "Instacart Data Warehouse API", "docs": "/docs"}


@router.get("/favicon.ico", include_in_schema=False)
def favicon() -> Response:
    return Response(status_code=204)


@router.get("/health")
def health() -> dict[str, Any]:
    try:
        database_is_available()
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Database unavailable: {exc}") from exc
    return {"status": "ok", "database": f"{settings.db_name} - SQL Server is ok"}
