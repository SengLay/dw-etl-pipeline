"""Central configuration, loaded from environment (.env)."""
import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()

# The three data stores of the DFD, as schemas inside one database
STAGING, DWH, DMART = "staging", "dwh", "dmart"      # D1, D2, D3
SCHEMAS = (STAGING, DWH, DMART)


@dataclass(frozen=True)
class Settings:
    # --- database ---
    db_backend: str = os.getenv("DB_BACKEND", "sqlite")        # sqlite (zero-setup default) | mssql
    db_server: str = os.getenv("DB_SERVER", "localhost")
    db_name: str = os.getenv("DB_NAME", "DataPipeline")
    db_user: str = os.getenv("DB_USER", "sa")
    db_password: str = os.getenv("DB_PASSWORD", "")
    db_trusted: bool = os.getenv("DB_TRUSTED", "no").lower() in ("yes", "true", "1")  # Windows auth
    db_driver: str = os.getenv("DB_DRIVER", "ODBC Driver 18 for SQL Server")
    sqlite_dir: str = os.getenv("SQLITE_DIR", "./data/sqlite")

    # --- data lake / kaggle ---
    lake_path: str = os.getenv("LAKE_PATH", "./data/lake")
    kaggle_dataset: str = os.getenv("KAGGLE_DATASET", "psparks/instacart-market-basket-analysis")
    sample_orders: int = int(os.getenv("SAMPLE_ORDERS", "1000"))   # also used for mock data size

    # --- optional sources (not used for Instacart) ---
    app_api_url: str = os.getenv("APP_API_URL", "")
    app_api_token: str = os.getenv("APP_API_TOKEN", "")
    kafka_bootstrap: str = os.getenv("KAFKA_BOOTSTRAP", "localhost:9092")
    kafka_topic: str = os.getenv("KAFKA_TOPIC", "events")


settings = Settings()
