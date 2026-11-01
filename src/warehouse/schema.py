"""Star schema (D2 DWH) and reporting tables (D3 D-Mart), dialect-neutral.

SQLAlchemy renders autoincrement keys as IDENTITY on SQL Server.
"""
from sqlalchemy import (Column, Float, ForeignKey, Index, Integer, MetaData,
                        Table, Unicode)

from config.settings import DMART, DWH

metadata = MetaData()

# ---------------- D2: DWH ----------------
dim_user = Table(
    "dim_user", metadata,
    Column("user_key", Integer, primary_key=True, autoincrement=True),
    Column("user_id", Integer, nullable=False, unique=True),
    schema=DWH)

dim_product = Table(
    "dim_product", metadata,
    Column("product_key", Integer, primary_key=True, autoincrement=True),
    Column("product_id", Integer, nullable=False, unique=True),
    Column("product_name", Unicode(255)),
    Column("aisle_id", Integer),
    Column("aisle", Unicode(100)),
    Column("department_id", Integer),
    Column("department", Unicode(100)),
    schema=DWH)

# Instacart has no calendar dates, only day-of-week and hour-of-day
dim_time = Table(
    "dim_time", metadata,
    Column("time_key", Integer, primary_key=True, autoincrement=False),  # dow*24 + hour
    Column("order_dow", Integer, nullable=False),
    Column("order_hour_of_day", Integer, nullable=False),
    Column("day_part", Unicode(20)),
    schema=DWH)

fact_order_items = Table(
    "fact_order_items", metadata,
    Column("order_item_key", Integer, primary_key=True, autoincrement=True),
    Column("order_id", Integer, nullable=False),
    Column("user_key", Integer, ForeignKey(f"{DWH}.dim_user.user_key"), nullable=False),
    Column("product_key", Integer, ForeignKey(f"{DWH}.dim_product.product_key"), nullable=False),
    Column("time_key", Integer, ForeignKey(f"{DWH}.dim_time.time_key"), nullable=False),
    Column("order_number", Integer),
    Column("days_since_prior_order", Float),
    Column("add_to_cart_order", Integer),
    Column("reordered", Integer),
    Index("ix_fact_order_items_order_id", "order_id"),
    schema=DWH)

# ---------------- D3: D-Mart ----------------
mart_department_summary = Table(
    "mart_department_summary", metadata,
    Column("department", Unicode(100), primary_key=True),
    Column("items_sold", Integer), Column("orders", Integer), Column("reorder_rate", Float),
    schema=DMART)

mart_orders_by_time = Table(
    "mart_orders_by_time", metadata,
    Column("order_dow", Integer, primary_key=True, autoincrement=False),
    Column("order_hour_of_day", Integer, primary_key=True, autoincrement=False),
    Column("orders", Integer), Column("items", Integer),
    schema=DMART)

mart_product_summary = Table(
    "mart_product_summary", metadata,
    Column("product_id", Integer, primary_key=True, autoincrement=False),
    Column("product_name", Unicode(255)), Column("department", Unicode(100)),
    Column("aisle", Unicode(100)),
    Column("times_ordered", Integer), Column("reorder_rate", Float),
    schema=DMART)

mart_user_summary = Table(
    "mart_user_summary", metadata,
    Column("user_id", Integer, primary_key=True, autoincrement=False),
    Column("total_orders", Integer), Column("total_items", Integer),
    Column("avg_basket_size", Float), Column("avg_days_between_orders", Float),
    schema=DMART)
