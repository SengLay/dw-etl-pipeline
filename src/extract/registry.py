"""Declares raw tables and their cleaned staging targets."""
from src.extract.base import BaseExtractor
from src.extract.data_lake import DataLakeExtractor


def get_extractors() -> list[BaseExtractor]:
    return [
        DataLakeExtractor("departments", "stg_departments"),
        DataLakeExtractor("aisles", "stg_aisles"),
        DataLakeExtractor("products", "stg_products"),
        DataLakeExtractor("orders", "stg_orders"),
        DataLakeExtractor("order_products", "stg_order_products"),
    ]
