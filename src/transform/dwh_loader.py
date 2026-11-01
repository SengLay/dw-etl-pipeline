"""Helpers to write into D2 (DWH). Plain SQL that runs on SQL Server and SQLite."""
import pandas as pd

from config.settings import DWH
from src.common.db import get_database


def upsert_dimension(df: pd.DataFrame, table: str, business_key: str) -> None:
    """SCD Type 1: update rows that exist, insert rows that don't."""
    tmp = f"_tmp_{table}"
    cols = list(df.columns)
    non_key = [c for c in cols if c != business_key]
    db = get_database()
    t, s = f"{DWH}.{table}", f"{DWH}.{tmp}"
    with db.transaction() as conn:
        db.insert(df, tmp, DWH, connection=conn, if_exists="replace")
        if non_key:
            sets = ", ".join(
                f"{c} = (SELECT x.{c} FROM {s} x WHERE x.{business_key} = {t}.{business_key})"
                for c in non_key)
            db.execute(
                f"UPDATE {t} SET {sets} "
                f"WHERE EXISTS (SELECT 1 FROM {s} x WHERE x.{business_key} = {t}.{business_key})",
                connection=conn)
        col_list = ", ".join(cols)
        db.execute(
            f"INSERT INTO {t} ({col_list}) SELECT {col_list} FROM {s} x "
            f"WHERE NOT EXISTS (SELECT 1 FROM {t} d WHERE d.{business_key} = x.{business_key})",
            connection=conn)
        db.execute(f"DROP TABLE {s}", connection=conn)


def load_fact(df: pd.DataFrame, table: str, replace_key: str) -> None:
    """Idempotent: delete existing rows whose `replace_key` is in df, then insert df."""
    tmp = f"_tmp_{table}"
    cols = ", ".join(df.columns)
    db = get_database()
    t, s = f"{DWH}.{table}", f"{DWH}.{tmp}"
    with db.transaction() as conn:
        db.insert(df, tmp, DWH, connection=conn, if_exists="replace")
        db.delete(t.split(".")[-1], DWH,
                  where=f"{replace_key} IN (SELECT {replace_key} FROM {s})",
                  connection=conn)
        db.execute(f"INSERT INTO {t} ({cols}) SELECT {cols} FROM {s}", connection=conn)
        db.execute(f"DROP TABLE {s}", connection=conn)
