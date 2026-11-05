from itertools import chain
from pathlib import Path

import pandas as pd

from config.settings import settings
from src.database.connection import get_database, init_db

RAW_SCHEMA = "raw"


def land_file(file: str, table: str, folder: str = "instacart") -> None:
    """
    Land a source file into the lake_raw database.

    Parameters
    ----------
    file : str
        The name of the source file to land.
    table : str
        The name of the table to insert the data into.
    folder : str, optional
        The folder containing the source file, by default "instacart"
    """
    path = Path(settings.lake_path) / folder / file
    if not path.exists():
        raise FileNotFoundError(
            f"{path} not found. Land the source file first: "
            "python -m src.tools.mock_data")

    db = get_database("raw")
    chunks = pd.read_parquet(path) if path.suffix == ".parquet" else pd.read_csv(
        path, chunksize=100_000)

    if isinstance(chunks, pd.DataFrame):
        chunks = iter([chunks])

    with db.transaction() as conn:
        if db.table_exists(table, RAW_SCHEMA):
            first_chunk = next(chunks)
            db.ensure_columns(first_chunk, table, RAW_SCHEMA, connection=conn)
            db.delete(table, RAW_SCHEMA, connection=conn, truncate=db.engine.dialect.name == "mssql")
            chunks = chain([first_chunk], chunks)
        for chunk in chunks:
            db.insert(chunk, table, RAW_SCHEMA, connection=conn)


def land_sources(sources: list[tuple[str, str, str]]) -> None:
    """
    Replace raw tables with the current source files in one landing run.

    Example
    -------
    >>> SOURCES = [
    ...     ("departments.csv", "departments", "instacart"),
    ...     ("aisles.csv", "aisles", "instacart"),
    ...     ("products.csv", "products", "instacart"),
    ...     ("orders.csv", "orders", "instacart"),
    ... ]
    >>> land_sources(SOURCES)
    """

    init_db("raw")
    for file, table, folder in sources:
        land_file(file, table, folder)
