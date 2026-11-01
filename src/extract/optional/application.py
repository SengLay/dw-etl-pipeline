from typing import Iterator

import pandas as pd
import requests

from config.settings import settings
from src.extract.base import BaseExtractor


class ApplicationApiExtractor(BaseExtractor):
    """Paginated REST API extractor. Adapt pagination to your application."""

    def __init__(self, endpoint: str, target_table: str, page_size: int = 1000):
        self.endpoint, self.target_table, self.page_size = endpoint, target_table, page_size

    def extract(self) -> Iterator[pd.DataFrame]:
        headers = {"Authorization": f"Bearer {settings.app_api_token}"}
        page = 1
        while True:
            r = requests.get(
                f"{settings.app_api_url}/{self.endpoint}",
                headers=headers,
                params={"page": page, "page_size": self.page_size},
                timeout=60,
            )
            r.raise_for_status()
            rows = r.json()
            if not rows:
                break
            yield pd.DataFrame(rows)
            page += 1
