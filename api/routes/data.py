"""Read-only data and metadata endpoints."""
from typing import Any

from fastapi import APIRouter, Query

from api.schemas import Layer, TableRowsResponse
from api.services.database import list_layers, list_tables, read_table

router = APIRouter(prefix="/api/v1", tags=["data"])


@router.get("/layers")
def layers() -> dict[str, list[dict[str, Any]]]:
    return list_layers()


@router.get("/{layer}/tables")
def tables(layer: Layer) -> dict[str, Any]:
    """List all tables in a given layer."""
    # list_tables: called from api/services/database.py
    return {"layer": layer.value, "tables": list_tables(layer.value)}


@router.get("/{layer}/{table}", response_model=TableRowsResponse)
def table_rows(
    layer: Layer,
    table: str,
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    order_by: str | None = Query(None),
    descending: bool = False,
) -> dict[str, Any]:
    return read_table(layer.value, table, limit, offset, order_by, descending)
