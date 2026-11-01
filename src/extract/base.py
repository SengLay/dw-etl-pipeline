"""P1 - Extract (E). Every source implements BaseExtractor."""
from abc import ABC, abstractmethod
from typing import Iterator

import pandas as pd


class BaseExtractor(ABC):
    #: target table in D1 (Staging)
    target_table: str

    @abstractmethod
    def extract(self) -> Iterator[pd.DataFrame]:
        """Yield DataFrames (chunks) of raw data, untouched from the source."""
