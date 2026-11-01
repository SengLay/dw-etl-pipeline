"""One command: mock data -> P1 -> P2 -> P3, then print row counts per layer.

    python -m src.tools.demo              # 1000 mock orders, SQLite (no setup needed)
    python -m src.tools.demo --orders 200
    python -m src.tools.demo --reset      # wipe previous SQLite files first
"""
import argparse
import shutil
from pathlib import Path

from config.settings import SCHEMAS, settings
from src.common.db import get_database, get_engine
from src.common.logger import get_logger
from src.datamart import build as p3
from src.extract import run as p1
from src.tools import mock_data
from src.transform import run as p2

log = get_logger("demo")


def print_counts() -> None:
    db = get_database()
    print("\nRow counts")
    print("-" * 44)
    for schema in SCHEMAS:
        for t in sorted(x for x in db.list_tables(schema) if not x.startswith("_tmp")):
            n = db.scalar(f"SELECT COUNT(*) FROM {schema}.{t}")
            print(f"{schema + '.' + t:<38}{n:>6}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--orders", type=int, default=None)
    ap.add_argument("--reset", action="store_true")
    args = ap.parse_args()

    if args.reset and settings.db_backend == "sqlite":
        shutil.rmtree(Path(settings.sqlite_dir), ignore_errors=True)
        get_engine.cache_clear()

    log.info("Backend: %s", settings.db_backend)
    mock_data.generate(n_orders=args.orders)
    p1.run()
    p2.run()
    p3.run()
    print_counts()


if __name__ == "__main__":
    main()
