"""Data quality gate (the warning icon under D1: Staging).

All tables are checked before anything is written to staging.
"""
import pandas as pd

from src.common.logger import get_logger

log = get_logger("quality")


class DataQualityError(Exception):
    pass


RULES: dict[str, dict] = {
    "stg_departments": {"required": ["department_id", "department"], "unique": ["department_id"]},
    "stg_aisles": {"required": ["aisle_id", "aisle"], "unique": ["aisle_id"]},
    "stg_products": {"required": ["product_id", "product_name", "aisle_id", "department_id"],
                     "unique": ["product_id"]},
    "stg_orders": {"required": ["order_id", "user_id", "order_number", "order_dow", "order_hour_of_day"],
                   "unique": ["order_id"],
                   "ranges": {"order_dow": (0, 6), "order_hour_of_day": (0, 23)}},
    "stg_order_products": {"required": ["order_id", "product_id"],
                          "allowed": {"reordered": [0, 1]}},
}

# (child table, child column, parent table, parent column)
RELATIONSHIPS = [
    ("stg_products", "aisle_id", "stg_aisles", "aisle_id"),
    ("stg_products", "department_id", "stg_departments", "department_id"),
    ("stg_order_products", "order_id", "stg_orders", "order_id"),
    ("stg_order_products", "product_id", "stg_products", "product_id"),
]


def check_table(table: str, df: pd.DataFrame) -> list[str]:
    rule, errors = RULES.get(table, {}), []
    if df.empty:
        return [f"{table}: no rows extracted"]
    for col in rule.get("required", []):
        if col not in df.columns:
            errors.append(f"{table}: missing column '{col}'")
        elif df[col].isna().any():
            errors.append(f"{table}: {int(df[col].isna().sum())} nulls in '{col}'")
    for col in rule.get("unique", []):
        if col in df.columns and df[col].duplicated().any():
            errors.append(f"{table}: {int(df[col].duplicated().sum())} duplicates in '{col}'")
    for col, (lo, hi) in rule.get("ranges", {}).items():
        if col in df.columns and not df[col].between(lo, hi).all():
            errors.append(f"{table}: '{col}' outside [{lo}, {hi}]")
    for col, allowed in rule.get("allowed", {}).items():
        if col in df.columns and not df[col].isin(allowed).all():
            errors.append(f"{table}: '{col}' has values outside {allowed}")
    return errors


def run_staging_checks(frames: dict[str, pd.DataFrame]) -> None:
    errors: list[str] = []
    for table, df in frames.items():
        errors += check_table(table, df)
    for child, ccol, parent, pcol in RELATIONSHIPS:
        if child in frames and parent in frames and ccol in frames[child] and pcol in frames[parent]:
            orphans = ~frames[child][ccol].isin(frames[parent][pcol])
            if orphans.any():
                errors.append(f"{child}.{ccol}: {int(orphans.sum())} rows without a match in {parent}.{pcol}")
    if errors:
        for e in errors:
            log.error(e)
        raise DataQualityError("; ".join(errors))
    log.info("Quality checks passed for %d tables", len(frames))
