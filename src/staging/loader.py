"""D1 Staging: raw copy of the source, truncate and reload (single transaction)."""
import pandas as pd

from config.settings import STAGING
from src.database.connection import get_database


def reload_all(frames: dict[str, pd.DataFrame]) -> None:
    db = get_database()
    with db.transaction() as conn:                   # all tables or none
        for table, df in frames.items():
            if db.table_exists(table, STAGING):
                db.delete(table, STAGING, connection=conn,
                          truncate=db.engine.dialect.name == "mssql")
            out = df.copy()
            out["_loaded_at"] = pd.Timestamp.now(tz="UTC").tz_localize(None)
            db.insert(out, table, STAGING, connection=conn)
