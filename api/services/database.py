"""Database read services used by API routes."""
from typing import Any

from fastapi import HTTPException
from sqlalchemy import inspect

from config.settings import SCHEMAS
from src.common.db import get_database


def validate_layer(layer: str) -> str:
    if layer not in SCHEMAS:
        raise HTTPException(status_code=404, detail=f"Unknown layer: {layer}")
    return layer


def validate_table(layer: str, table: str) -> None:
    """validates that a requested table exists"""
    db = get_database()
    if table.startswith("_tmp") or table not in db.list_tables(layer):
        raise HTTPException(status_code=404, detail=f"Table not found: {layer}.{table}")


def list_layers() -> dict[str, list[dict[str, Any]]]:
    """builds the `/layers` response"""
    db = get_database() # <- return `Database()` which is initiated in db.py
    return {
        layer: [
            {"table": table, "rows": int(db.scalar(f"SELECT COUNT(*) FROM {layer}.{table}"))}
            for table in sorted(db.list_tables(layer))
            if not table.startswith("_tmp")
        ]
        for layer in SCHEMAS
    }


def list_tables(layer: str) -> list[str]:
    """This wraps the core method for the API. It validates the layer, sorts tables, and hides temporary tables."""
    validate_layer(layer)
    return sorted(t for t in get_database().list_tables(layer) if not t.startswith("_tmp"))


def read_table(
    layer: str,
    table: str,
    limit: int,
    offset: int,
    order_by: str | None,
    descending: bool,
) -> dict[str, Any]:
    """
    read_table does four main things:
    - Validates that the layer exists.
    - Validates that the table exists and is not temporary.
    - Checks that `order_by` is a real column.
    - Reads paginated rows and returns:
    ```
    {
        "layer": layer,
        "table": table,
        "items": [...],
        "limit": limit,
        "offset": offset,
        "total": total_rows,
    }
    ```
    """
    validate_layer(layer)           # Validates that the layer exists.
    validate_table(layer, table)    # Validates that the table exists and is not temporary.
    db = get_database()
    columns = [column["name"] for column in inspect(db.engine).get_columns(table, schema=layer)]
    selected_order = order_by or columns[0]
    if selected_order not in columns:
        raise HTTPException(status_code=400, detail=f"Unknown order_by column: {selected_order}")
    direction = "DESC" if descending else "ASC"
    pagination = (
        "LIMIT :limit OFFSET :offset"
        if db.engine.dialect.name == "sqlite"
        else "OFFSET :offset ROWS FETCH NEXT :limit ROWS ONLY"
    )
    frame = db.select(
        f"SELECT * FROM {layer}.{table} ORDER BY {selected_order} {direction} {pagination}",
        {"limit": limit, "offset": offset},
    )
    return {
        "layer": layer,
        "table": table,
        "items": frame.where(frame.notna(), None).to_dict(orient="records"),
        "limit": limit,
        "offset": offset,
        "total": int(db.scalar(f"SELECT COUNT(*) FROM {layer}.{table}")),
    }
