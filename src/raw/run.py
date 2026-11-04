"""Raw landing stage: source files -> lake_raw.raw tables."""
from src.raw.loader import land_sources

SOURCES = [
    ("departments.csv", "departments", "instacart"),
    ("aisles.csv", "aisles", "instacart"),
    ("products.csv", "products", "instacart"),
    ("orders.csv", "orders", "instacart"),
    ("order_products__prior.csv", "order_products", "instacart"),
]


def run() -> None:
    land_sources(SOURCES)


if __name__ == "__main__":
    run()
