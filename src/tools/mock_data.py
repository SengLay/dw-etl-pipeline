"""Mock data in the Instacart file format (same files, same columns, synthetic values).

    python -m src.tools.mock_data
"""
from pathlib import Path

import numpy as np
import pandas as pd

from config.settings import settings


def generate(lake_dir: str | None = None, n_orders: int | None = None, seed: int = 42) -> Path:
    n_orders = n_orders or settings.sample_orders
    rng = np.random.default_rng(seed)
    out = Path(lake_dir or settings.lake_path) / "instacart"
    out.mkdir(parents=True, exist_ok=True)

    departments = pd.DataFrame({"department_id": range(1, 7),
                                "department": ["produce", "dairy eggs", "snacks",
                                               "beverages", "frozen", "bakery"]})
    aisles = pd.DataFrame({"aisle_id": range(1, 21),
                           "aisle": [f"aisle {i}" for i in range(1, 21)]})
    products = pd.DataFrame({
        "product_id": range(1, 301),
        "product_name": [f"Product {i} Café" if i % 50 == 0 else f"Product {i}" for i in range(1, 301)],
        "aisle_id": rng.integers(1, 21, 300),
        "department_id": rng.integers(1, 7, 300)})

    n_users = max(1, n_orders // 10)
    user_ids = np.repeat(np.arange(1, n_users + 1), 10)[:n_orders]
    order_ids = rng.choice(np.arange(1, 3_000_000), n_orders, replace=False)
    order_number = np.concatenate([np.arange(1, (user_ids == u).sum() + 1) for u in range(1, n_users + 1)])
    orders = pd.DataFrame({
        "order_id": order_ids, "user_id": user_ids, "eval_set": "prior",
        "order_number": order_number,
        "order_dow": rng.integers(0, 7, n_orders),
        "order_hour_of_day": rng.integers(0, 24, n_orders),
        "days_since_prior_order": np.where(order_number == 1, np.nan, rng.integers(1, 31, n_orders))})

    lines = []
    for oid, onum in zip(order_ids, order_number):
        k = int(rng.integers(1, 15))
        pids = rng.choice(products["product_id"], k, replace=False)
        for pos, pid in enumerate(pids, 1):
            lines.append((oid, pid, pos, int(onum > 1 and rng.random() < 0.6)))
    items = pd.DataFrame(lines, columns=["order_id", "product_id", "add_to_cart_order", "reordered"])

    orders.to_csv(out / "orders.csv", index=False)
    items.to_csv(out / "order_products__prior.csv", index=False)
    products.to_csv(out / "products.csv", index=False)
    aisles.to_csv(out / "aisles.csv", index=False)
    departments.to_csv(out / "departments.csv", index=False)
    print(f"Mock data -> {out.resolve()}: orders={len(orders)}, lines={len(items)}")
    return out


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--orders", type=int, default=None)
    generate(n_orders=ap.parse_args().orders)
