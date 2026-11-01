"""One engine; D1/D2/D3 are three schemas: staging, dwh, dmart.

SQL Server : one database, three schemas.
SQLite     : three attached files (staging.db, dwh.db, dmart.db) - same `schema.table`
             syntax, so every query in the project runs unchanged on both.
"""
from functools import lru_cache
from contextlib import contextmanager
from pathlib import Path
import re
from urllib.parse import quote_plus

import pandas as pd
from sqlalchemy import UnicodeText, create_engine, event, text
from sqlalchemy.engine import Connection, Engine
from sqlalchemy.engine import Result
from sqlalchemy import inspect

from config.settings import SCHEMAS, settings


@lru_cache(maxsize=None)
def get_engine() -> Engine:
    if settings.db_backend == "sqlite":
        folder = Path(settings.sqlite_dir).resolve()
        folder.mkdir(parents=True, exist_ok=True)
        engine = create_engine("sqlite://")

        @event.listens_for(engine, "connect")
        def _attach(dbapi_conn, _):
            cur = dbapi_conn.cursor()
            for schema in SCHEMAS:
                cur.execute(f"ATTACH DATABASE '{folder / (schema + '.db')}' AS {schema}")
            cur.close()

        return engine

    auth = ("Trusted_Connection=yes;" if settings.db_trusted
            else f"UID={settings.db_user};PWD={settings.db_password};")
    odbc = (f"DRIVER={{{settings.db_driver}}};SERVER={settings.db_server};"
            f"DATABASE={settings.db_name};{auth}TrustServerCertificate=yes")
    return create_engine(f"mssql+pyodbc:///?odbc_connect={quote_plus(odbc)}",
                         fast_executemany=True)


class Database:
    """Small database facade for connection, CRUD, and transaction operations."""

    def __init__(self, engine: Engine | None = None):
        self.engine = engine or get_engine()

    @contextmanager
    def transaction(self):
        with self.engine.begin() as conn:
            yield conn

    @staticmethod
    def _identifier(value: str) -> str:
        if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", value):
            raise ValueError(f"Invalid SQL identifier: {value}")
        return value

    def _table(self, table: str, schema: str | None = None) -> str:
        table = self._identifier(table)
        return f"{self._identifier(schema)}.{table}" if schema else table

    @contextmanager
    def _connection(self, connection: Connection | None = None):
        if connection is not None:
            yield connection
        else:
            with self.engine.begin() as conn:
                yield conn

    def create_schema(self, schema: str, connection: Connection | None = None) -> None:
        """Create a SQL Server schema if it does not already exist."""
        schema = self._identifier(schema)
        if self.engine.dialect.name != "mssql":
            return
        with self._connection(connection) as conn:
            conn.execute(text(
                f"IF NOT EXISTS (SELECT 1 FROM sys.schemas WHERE name = :schema) "
                f"EXEC('CREATE SCHEMA {schema}')"), {"schema": schema})

    def create_tables(self, metadata) -> None:
        """Create all SQLAlchemy tables represented by ``metadata``."""
        for schema in SCHEMAS:
            self.create_schema(schema)
        metadata.create_all(self.engine)

    def table_exists(self, table: str, schema: str) -> bool:
        return inspect(self.engine).has_table(self._identifier(table), schema=self._identifier(schema))

    def list_tables(self, schema: str) -> list[str]:
        return inspect(self.engine).get_table_names(schema=self._identifier(schema))

    def select(self, query: str, params: dict | None = None,
               connection: Connection | None = None) -> pd.DataFrame:
        """Run a SELECT statement and return a DataFrame."""
        if connection is not None:
            return pd.read_sql(text(query), connection, params=params)
        with self.engine.connect() as conn:
            return pd.read_sql(text(query), conn, params=params)

    def execute(self, query: str, params: dict | None = None,
                connection: Connection | None = None) -> Result:
        """Execute a statement that is not a DataFrame SELECT."""
        with self._connection(connection) as conn:
            return conn.execute(text(query), params or {})

    def scalar(self, query: str, params: dict | None = None):
        """Execute a query and return its first scalar value."""
        with self.engine.connect() as conn:
            return conn.execute(text(query), params or {}).scalar()

    def insert(self, df: pd.DataFrame, table: str, schema: str,
               connection: Connection | None = None, if_exists: str = "append") -> None:
        """Insert a DataFrame into a table."""
        text_cols = df.select_dtypes(include=["object", "string"]).columns
        dtype = {column: UnicodeText() for column in text_cols}
        with self._connection(connection) as conn:
            df.to_sql(self._identifier(table), conn, schema=self._identifier(schema),
                      if_exists=if_exists, index=False, chunksize=5000, dtype=dtype)

    def update(self, table: str, values: dict, where: str,
               params: dict | None = None, schema: str | None = None,
               connection: Connection | None = None) -> int:
        """Update rows using named values and a caller-supplied WHERE clause."""
        if not values:
            return 0
        assignments = ", ".join(
            f"{self._identifier(column)} = :_update_{column}" for column in values)
        bound = dict(params or {})
        bound.update({f"_update_{column}": value for column, value in values.items()})
        result = self.execute(
            f"UPDATE {self._table(table, schema)} SET {assignments} WHERE {where}",
            bound, connection)
        return result.rowcount

    def delete(self, table: str, schema: str, where: str | None = None,
               params: dict | None = None, connection: Connection | None = None,
               truncate: bool = False) -> int:
        """Delete rows, or truncate a table when ``truncate`` is requested."""
        target = self._table(table, schema)
        statement = f"TRUNCATE TABLE {target}" if truncate else f"DELETE FROM {target}"
        if where and not truncate:
            statement += f" WHERE {where}"
        result = self.execute(statement, params, connection)
        return result.rowcount

    def run_sql_file(self, path: str | Path) -> None:
        """Run a SQL file whose statements are separated by semicolons."""
        lines = [line for line in Path(path).read_text(encoding="utf-8").splitlines()
                 if not line.strip().startswith("--")]
        with self.transaction() as conn:
            for statement in (s.strip() for s in "\n".join(lines).split(";") if s.strip()):
                self.execute(statement, connection=conn)


def get_database() -> Database:
    return Database()


def init_db() -> None:
    """Idempotent: create schemas and the DWH / D-Mart tables."""
    from src.warehouse.schema import metadata

    get_database().create_tables(metadata)


def run_sql_file(path: str | Path) -> None:
    get_database().run_sql_file(path)
