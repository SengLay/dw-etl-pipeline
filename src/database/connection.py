"""Database selection, engine creation, and initialization."""
from functools import lru_cache
from urllib.parse import quote_plus

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

from config.settings import settings
from src.database.operations import Database


RAW_SCHEMA = "raw"
DATABASES = {"all": settings.db_name, "raw": settings.raw_db_name}


def _build_engine(database: str, *, fast_executemany: bool = True) -> Engine:
    auth = ("Trusted_Connection=yes;" if settings.db_trusted else
            f"UID={settings.db_user};PWD={settings.db_password};")
    odbc = (f"DRIVER={{{settings.db_driver}}};SERVER={settings.db_server};"
            f"DATABASE={database};{auth}TrustServerCertificate=yes")
    return create_engine(f"mssql+pyodbc:///?odbc_connect={quote_plus(odbc)}",
                         fast_executemany=fast_executemany)


@lru_cache(maxsize=None)
def get_engine(database: str | None = None) -> Engine:
    return _build_engine(database or settings.db_name)


def get_raw_engine() -> Engine:
    return get_engine(settings.raw_db_name)


def get_database(name: str = "all") -> Database:
    """Return operations bound to the warehouse or raw database."""
    database = DATABASES.get(name)
    if database is None:
        raise ValueError(f"Unknown database: {name!r}; expected 'all' or 'raw'")
    return Database(get_engine(database))


def ensure_database(database: str) -> None:
    engine = _build_engine("master", fast_executemany=False)
    try:
        with engine.begin() as conn:
            exists = conn.execute(
                text("SELECT 1 FROM sys.databases WHERE name = :database"),
                {"database": database}).scalar()
            if not exists:
                safe_name = Database._identifier(database)
                conn.execute(text(f"CREATE DATABASE [{safe_name}]"))
    finally:
        engine.dispose()


def init_db(name: str = "all") -> None:
    """Idempotently initialize either the warehouse or raw database."""
    database = DATABASES.get(name)
    if database is None:
        raise ValueError(f"Unknown database: {name!r}; expected 'all' or 'raw'")
    ensure_database(database)
    print(f"Initializing SQL Server database {database}...")
    db = get_database(name)
    if name == "raw":
        db.create_schema(RAW_SCHEMA)
        return

    from src.warehouse.schema import metadata
    db.create_tables(metadata)


def run_sql_file(path: str) -> None:
    get_database().run_sql_file(path)
