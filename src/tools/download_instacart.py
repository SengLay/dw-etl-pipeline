"""Landing step (not part of P1): Kaggle -> Data Lake folder, sampled.

    python -m src.tools.download_instacart            # SAMPLE_ORDERS from .env (default 1000)
    python -m src.tools.download_instacart --orders 500

Sample = the first N *prior* orders, plus ONLY the order lines belonging to them
(so orders and items still join), plus the small lookup files in full.
"""
import argparse
from pathlib import Path

import pandas as pd

from config.settings import settings

NEEDED = ["orders.csv", "order_products__prior.csv", "products.csv",
          "aisles.csv", "departments.csv"]


def _find(root: Path, name: str) -> Path:
    hit = next(root.rglob(name), None)
    if hit is None:
        found = sorted(p.name for p in root.rglob("*.csv"))
        raise FileNotFoundError(f"{name} not found in {root}. CSV files present: {found}")
    return hit


def main(n_orders: int) -> None:
    import kagglehub  # imported here so tests don't need it

    root = Path(kagglehub.dataset_download(settings.kaggle_dataset))
    print("Kaggle files at:", root)

    orders = pd.read_csv(_find(root, "orders.csv"))
    orders = orders[orders["eval_set"] == "prior"].head(n_orders)
    ids = set(orders["order_id"])

    # items file has ~32M rows: stream it in chunks, keep only our orders
    parts = [c[c["order_id"].isin(ids)]
             for c in pd.read_csv(_find(root, "order_products__prior.csv"), chunksize=2_000_000)]
    items = pd.concat(parts, ignore_index=True)

    out = Path(settings.lake_path) / "instacart"
    out.mkdir(parents=True, exist_ok=True)
    orders.to_csv(out / "orders.csv", index=False)
    items.to_csv(out / "order_products__prior.csv", index=False)
    for name in ("products.csv", "aisles.csv", "departments.csv"):
        pd.read_csv(_find(root, name)).to_csv(out / name, index=False)

    print(f"Wrote to {out.resolve()}: orders={len(orders)}, order lines={len(items)}, "
          f"users={orders['user_id'].nunique()}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--orders", type=int, default=settings.sample_orders)
    main(ap.parse_args().orders)
