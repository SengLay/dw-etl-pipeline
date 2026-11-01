"""Look at what each layer contains (row counts + first rows).

    python -m src.tools.inspect_layers              # all layers
    python -m src.tools.inspect_layers staging      # staging | dwh | dmart
"""
import sys

from config.settings import SCHEMAS
from src.common.db import get_database


def main(layers: list[str]) -> None:
    db = get_database()
    for schema in layers:
        print(f"\n===== {schema} =====")
        tables = sorted(t for t in db.list_tables(schema) if not t.startswith("_tmp"))
        if not tables:
            print("(empty)")
        for t in tables:
            n = db.scalar(f"SELECT COUNT(*) FROM {schema}.{t}")
            print(f"\n{schema}.{t}: {n} rows")
            if n:
                print(db.select(f"SELECT * FROM {schema}.{t} ORDER BY 1").head(3).to_string(index=False))


if __name__ == "__main__":
    main(sys.argv[1:] or list(SCHEMAS))
