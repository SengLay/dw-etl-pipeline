"""Staging -> dimension tables."""
import pandas as pd

from config.settings import STAGING
from src.common.db import get_database
from src.transform.dwh_loader import upsert_dimension


def build_dim_user() -> None:
    db = get_database()
    df = db.select(f"SELECT DISTINCT user_id FROM {STAGING}.stg_orders")
    upsert_dimension(df.astype({"user_id": "int64"}), "dim_user", "user_id")


def build_dim_product() -> None:
    db = get_database()
    p = db.select(f"SELECT * FROM {STAGING}.stg_products")
    a = db.select(f"SELECT aisle_id, aisle FROM {STAGING}.stg_aisles")
    d = db.select(f"SELECT department_id, department FROM {STAGING}.stg_departments")
    df = p.merge(a, on="aisle_id", how="left").merge(d, on="department_id", how="left")
    out = pd.DataFrame({
        "product_id": df["product_id"].astype("int64"),
        "product_name": df["product_name"].str.strip(),
        "aisle_id": df["aisle_id"].astype("int64"),
        "aisle": df["aisle"].fillna("Unknown"),
        "department_id": df["department_id"].astype("int64"),
        "department": df["department"].fillna("Unknown"),
    })
    upsert_dimension(out, "dim_product", "product_id")


def _day_part(h: int) -> str:
    return "night" if h < 6 else "morning" if h < 12 else "afternoon" if h < 18 else "evening"


def build_dim_time() -> None:
    rows = [(d * 24 + h, d, h, _day_part(h)) for d in range(7) for h in range(24)]
    df = pd.DataFrame(rows, columns=["time_key", "order_dow", "order_hour_of_day", "day_part"])
    upsert_dimension(df, "dim_time", "time_key")
