"""Raw landing stage: source files -> lake_raw.raw tables."""
from src.raw.loader import land_sources

"""format to load to raw: file (in CSV from data/lake), table (table name in lake_raw), folder (from data/lake/folder)"""
SOURCES = [
    ("departments.csv", "instacart_departments", "instacart"),
    ("aisles.csv", "instacart_aisles", "instacart"),
    ("products.csv", "instacart_products", "instacart"),
    ("orders.csv", "instacart_orders", "instacart"),
    ("order_products__prior.csv", "instacart_order_products", "instacart"),
]


def run() -> None:
    land_sources(SOURCES)


if __name__ == "__main__":
    run()
