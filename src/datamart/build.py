"""P3: D2 DWH -> D3 D-Mart. Runs sql/datamart/*.sql in filename order."""
from pathlib import Path

from src.database.connection import init_db, run_sql_file
from src.common.logger import get_logger

log = get_logger("P3.datamart")
SQL_DIR = Path(__file__).resolve().parents[2] / "sql" / "datamart"


def run() -> None:
    init_db()
    for f in sorted(SQL_DIR.glob("*.sql")):
        log.info("Running %s", f.name)
        run_sql_file(f)


if __name__ == "__main__":
    run()
