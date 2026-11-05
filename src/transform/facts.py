"""Staging + dimension keys -> fact table."""
import pandas as pd

from config.settings import DWH, STAGING
from src.database.connection import get_database
from src.quality.checks import DataQualityError
from src.common.logger import get_logger
from src.transform.dwh_loader import load_fact

log = get_logger("P2.facts")


def build_fact_order_items() -> None:
    db = get_database()
    orders = db.select(
        f"SELECT order_id, user_id, order_number, order_dow, order_hour_of_day, "
        f"days_since_prior_order FROM {STAGING}.stg_orders")
    items = db.select(
        f"SELECT order_id, product_id, add_to_cart_order, reordered "
        f"FROM {STAGING}.stg_order_products")
    dim_u = db.select(f"SELECT user_key, user_id FROM {DWH}.dim_user")
    dim_p = db.select(f"SELECT product_key, product_id FROM {DWH}.dim_product")

    fact = items.merge(orders, on="order_id", how="inner")
    fact["time_key"] = fact["order_dow"] * 24 + fact["order_hour_of_day"]
    fact = fact.merge(dim_u, on="user_id", how="left").merge(dim_p, on="product_id", how="left")

    orphans = fact[["user_key", "product_key"]].isna().any(axis=1).sum()
    if orphans:  # never load facts that cannot point at a dimension row
        raise DataQualityError(f"{orphans} fact rows have no matching dimension key")

    out = fact[["order_id", "user_key", "product_key", "time_key", "order_number",
                "days_since_prior_order", "add_to_cart_order", "reordered"]].astype(
        {"order_id": "int64", "user_key": "int64", "product_key": "int64", "time_key": "int64",
         "order_number": "int64", "add_to_cart_order": "int64", "reordered": "int64"})
    load_fact(out, "fact_order_items", replace_key="order_id")
    log.info("fact_order_items: %d rows from %d orders", len(out), out["order_id"].nunique())
