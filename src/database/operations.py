"""Reusable database operations."""
from contextlib import contextmanager
from pathlib import Path
import re

import pandas as pd
from sqlalchemy import UnicodeText, inspect, text
from sqlalchemy.engine import Connection, Engine, Result

from config.settings import SCHEMAS


class Database:
    """Database operations using an existing SQLAlchemy engine."""

    def __init__(self, engine: Engine):
        self.engine = engine

    @contextmanager
    def transaction(self):
        """"Context manager for a database transaction."""
        with self.engine.begin() as conn:
            yield conn

    @staticmethod
    def _identifier(value: str) -> str:
        """Return a valid SQL identifier, raising an error if invalid."""
        if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", value):
            raise ValueError(f"Invalid SQL identifier: {value}")
        return value

    def _table(self, table: str, schema: str | None = None) -> str:
        """"Return a fully qualified table name, optionally including the schema."""
        table = self._identifier(table)
        return f"{self._identifier(schema)}.{table}" if schema else table

    @contextmanager
    def _connection(self, connection: Connection | None = None):
        """Context manager for a database connection."""
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

    def create_tables(self, metadata, schemas: tuple[str, ...] = SCHEMAS) -> None:
        """Create schemas and all SQLAlchemy tables represented by ``metadata``."""
        for schema in schemas:
            self.create_schema(schema)
        metadata.create_all(self.engine)

    def table_exists(self, table: str, schema: str) -> bool:
        """Check if a table exists in the database."""
        return inspect(self.engine).has_table(self._identifier(table), schema=self._identifier(schema))

    def ensure_columns(self, df: pd.DataFrame, table: str, schema: str,
                       connection: Connection | None = None) -> None:
        """Add source columns missing from an existing table."""
        if not self.table_exists(table, schema):
            return

        table = self._identifier(table)
        schema = self._identifier(schema)
        existing = {
            column["name"]
            for column in inspect(self.engine).get_columns(table, schema=schema)
        }
        missing = [column for column in df.columns if str(column) not in existing]
        if not missing:
            return

        with self._connection(connection) as conn:
            for column in missing:
                name = self._identifier(str(column))
                conn.execute(text(
                    f"ALTER TABLE {schema}.{table} "
                    f"ADD {name} {self._column_type(df[column])} NULL"))

    @staticmethod
    def _column_type(column: pd.Series) -> str:
        if pd.api.types.is_bool_dtype(column):
            return "BIT"
        if pd.api.types.is_integer_dtype(column):
            return "BIGINT"
        if pd.api.types.is_float_dtype(column):
            return "FLOAT"
        if pd.api.types.is_datetime64_any_dtype(column):
            return "DATETIME2"
        return "NVARCHAR(MAX)"

    def list_tables(self, schema: str) -> list[str]:
        """List all tables in a schema."""
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
        """Execute a statement and return a single scalar value."""
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
