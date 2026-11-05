from typing import Iterator

import pandas as pd

from src.database.connection import get_database
from src.extract.base import BaseExtractor


class DataLakeExtractor(BaseExtractor):
    """Reads one landed source table from the lake_raw database."""

    def __init__(self, raw_table: str, target_table: str, chunksize: int = 100_000):
        self.raw_table, self.target_table = raw_table, target_table
        self.chunksize = chunksize

    def extract(self) -> Iterator[pd.DataFrame]:
        yield get_database("raw").select(f"SELECT * FROM raw.{self.raw_table}")
