# Database package

This package separates database connection management from reusable database
operations.

## Structure

- [`connection.py`](./connection.py) selects a database, creates SQLAlchemy
  engines, creates databases, and initializes schemas/tables.
- [`operations.py`](./operations.py) provides reusable operations through the
  `Database` class.
- [`__init__.py`](./__init__.py) exposes the public package API.

## Getting a database

Use the connection module when a service needs database operations:

```python
from src.database.connection import get_database

warehouse = get_database()
raw = get_database("raw")
```

The default connection uses `DB_NAME`. The `"raw"` connection uses
`RAW_DB_NAME`.

Initialize databases with:

```python
from src.database.connection import init_db

init_db()          # Creates the warehouse database, schemas, and tables.
init_db("raw")     # Creates the raw database and raw schema.
```

## Operations

### Required by the pipeline

| Operation | Purpose |
|---|---|
| `select(query, params)` | Read query results into a DataFrame. |
| `insert(df, table, schema)` | Append or replace DataFrame data. |
| `delete(table, schema, ...)` | Remove rows or truncate a table. |
| `transaction()` | Commit related changes together or roll them back. |
| `execute(query, params)` | Run SQL statements that are not DataFrame reads. |
| `scalar(query, params)` | Read one value, such as a row count or health check. |

### Required for initialization and services

| Operation | Purpose |
|---|---|
| `create_schema(schema)` | Create a schema if it does not exist. |
| `create_tables(metadata)` | Create warehouse tables from SQLAlchemy metadata. |
| `table_exists(table, schema)` | Avoid deleting or replacing a table that is not present. |
| `list_tables(schema)` | Support API and inspection tools that discover tables. |
| `ensure_columns(df, table, schema)` | Add new nullable source columns to an existing raw table. |

### Optional/general-purpose operations

| Operation | Purpose |
|---|---|
| `update(table, values, where, ...)` | Update rows using bound values. |
| `run_sql_file(path)` | Execute semicolon-separated SQL files. |

`update` and `run_sql_file` are reusable utilities, but they are not required
by the main ETL stages today.

## Raw schema evolution

`land_file()` supports additive schema changes for raw tables:

1. It compares source columns with the existing table.
2. Missing columns are added as nullable SQL Server columns.
3. Existing rows are truncated.
4. The new source data is inserted.

Columns removed from a source file are not dropped from the raw table. They
remain available for compatibility and receive `NULL` when future loads do not
provide values. Existing column types are not changed automatically.

Schema changes and data replacement run in the same transaction. If the schema
change or load fails, the transaction is rolled back.

### Example

If `raw.orders` initially contains `order_id` and `user_id`, and a new source
file adds `order_hour`, the loader adds the column before loading:

```text
Before: order_id | user_id
Source: order_id | user_id | order_hour
After:  order_id | user_id | order_hour
```

If a later source file removes `user_id`, the database column is retained and
new rows receive `NULL` for that column. The current loader still replaces the
table rows on each load; it does not append historical batches.

## Transactions

Pass the same connection to multiple operations when they must be atomic:

```python
db = get_database()

with db.transaction() as connection:
    db.delete("stg_orders", "staging", connection=connection, truncate=True)
    db.insert(frame, "stg_orders", "staging", connection=connection)
```

If an operation fails, the transaction is rolled back.

## Compatibility

`src/common/db.py` re-exports the database API for older imports. New code
should import from `src.database.connection` or
`src.database.operations` directly.



## Note
- `inspect` from SQLAlchemy is an `introspection utility`. It examines the database structure and returns information about schemas, tables, columns, indexes, and constraints.
<!-- 
- db.transaction() : Use it when the caller wants to group multiple operations into one transaction.
- self._connection(connection) : an internal helper used by individual methods such as insert, delete, and execute.
 -->