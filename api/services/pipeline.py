"""Pipeline and data-quality services."""
from typing import Any

import pandas as pd

from api.schemas import PipelineStage
from src.common.db import get_database
from src.extract.registry import get_extractors
from src.quality.checks import check_table


def run_stage(stage: PipelineStage) -> None:
    from src.extract import run as p1
    from src.transform import run as p2
    from src.datamart import build as p3

    jobs = {
        PipelineStage.extract: p1.run,
        PipelineStage.transform: p2.run,
        PipelineStage.datamart: p3.run,
    }
    if stage is PipelineStage.all:
        for job in (p1.run, p2.run, p3.run):
            job()
        return
    jobs[stage]()


def check_quality() -> dict[str, Any]:
    frames: dict[str, list[pd.DataFrame]] = {}
    for extractor in get_extractors():
        frames.setdefault(extractor.target_table, []).extend(extractor.extract())
    errors = [
        error
        for table, chunks in frames.items()
        for error in check_table(table, pd.concat(chunks, ignore_index=True))
    ]
    return {"status": "passed" if not errors else "failed", "errors": errors}


def database_is_available() -> bool:
    return get_database().scalar("SELECT 1") == 1
