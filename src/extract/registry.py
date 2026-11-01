"""Declares which lake files feed which staging tables (D1)."""
from src.extract.base import BaseExtractor
from src.extract.data_lake import DataLakeExtractor


def get_extractors() -> list[BaseExtractor]:
    return [
        DataLakeExtractor("departments.csv", "stg_departments"),
        DataLakeExtractor("aisles.csv", "stg_aisles"),
        DataLakeExtractor("products.csv", "stg_products"),
        DataLakeExtractor("orders.csv", "stg_orders"),
        DataLakeExtractor("order_products__prior.csv", "stg_order_products"),
    ]
