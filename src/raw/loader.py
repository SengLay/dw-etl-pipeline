"""Land source files into the separate lake_raw database."""
from pathlib import Path

import pandas as pd

from config.settings import settings
from src.common.db import get_raw_database, init_raw_db

RAW_SCHEMA = "raw"


def land_file(file: str, table: str, folder: str = "instacart") -> None:
    path = Path(settings.lake_path) / folder / file
    if not path.exists():
        raise FileNotFoundError(
            f"{path} not found. Land the source file first: "
            "python -m src.tools.mock_data")

    db = get_raw_database()
    chunks = pd.read_parquet(path) if path.suffix == ".parquet" else pd.read_csv(
        path, chunksize=100_000)
    if isinstance(chunks, pd.DataFrame):
        chunks = [chunks]

    with db.transaction() as conn:
        if db.table_exists(table, RAW_SCHEMA):
            db.delete(table, RAW_SCHEMA, connection=conn,
                      truncate=db.engine.dialect.name == "mssql")
        for chunk in chunks:
            db.insert(chunk, table, RAW_SCHEMA, connection=conn)


def land_sources(sources: list[tuple[str, str, str]]) -> None:
    """Replace raw tables with the current source files in one landing run."""
    init_raw_db()
    for file, table, folder in sources:
        land_file(file, table, folder)
