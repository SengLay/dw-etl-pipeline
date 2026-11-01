from pathlib import Path
from typing import Iterator

import pandas as pd

from config.settings import settings
from src.extract.base import BaseExtractor


class DataLakeExtractor(BaseExtractor):
    """Reads one csv/parquet file from the lake and yields it in chunks."""

    def __init__(self, file: str, target_table: str, folder: str = "instacart",
                 chunksize: int = 100_000):
        self.file, self.target_table = file, target_table
        self.folder, self.chunksize = folder, chunksize

    def extract(self) -> Iterator[pd.DataFrame]:
        path = Path(settings.lake_path) / self.folder / self.file
        if not path.exists():
            raise FileNotFoundError(
                f"{path} not found. Land the data first: "
                "python -m src.tools.mock_data  (or the optional python -m src.tools.download_instacart)")
        if path.suffix == ".parquet":
            yield pd.read_parquet(path)
        else:
            yield from pd.read_csv(path, chunksize=self.chunksize)
