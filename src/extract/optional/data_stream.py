import json
from typing import Iterator

import pandas as pd

from config.settings import settings
from src.extract.base import BaseExtractor


class KafkaMicroBatchExtractor(BaseExtractor):
    """Drains whatever is on the topic since last run (micro-batch), then stops.

    This keeps the stream compatible with a scheduled orchestrator.
    """

    def __init__(self, topic: str | None, target_table: str, max_wait_ms: int = 5000):
        self.topic = topic or settings.kafka_topic
        self.target_table, self.max_wait_ms = target_table, max_wait_ms

    def extract(self) -> Iterator[pd.DataFrame]:
        from kafka import KafkaConsumer  # lazy import: optional dependency

        consumer = KafkaConsumer(
            self.topic,
            bootstrap_servers=settings.kafka_bootstrap,
            group_id="dfd_pipeline",
            enable_auto_commit=False,
            auto_offset_reset="earliest",
            consumer_timeout_ms=self.max_wait_ms,
            value_deserializer=lambda v: json.loads(v.decode()),
        )
        records = [msg.value for msg in consumer]
        if records:
            yield pd.DataFrame(records)
        consumer.commit()  # commit only after a successful hand-off
        consumer.close()
