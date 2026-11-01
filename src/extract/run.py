"""P1: Data Lake -> quality gate -> D1 Staging.

Phase 1 extract everything, phase 2 check everything, phase 3 reload everything
in ONE transaction. Staging is never left half-updated.
"""
import pandas as pd

from src.common.db import init_db
from src.common.logger import get_logger
from src.extract.registry import get_extractors
from src.quality.checks import run_staging_checks
from src.staging.loader import reload_all

log = get_logger("P1.extract")


def run() -> None:
    init_db()
    chunks: dict[str, list[pd.DataFrame]] = {}
    for ex in get_extractors():
        chunks.setdefault(ex.target_table, []).extend(ex.extract())
    frames = {t: pd.concat(c, ignore_index=True) for t, c in chunks.items()}
    for t, df in frames.items():
        log.info("Extracted %-20s %8d rows", t, len(df))

    run_staging_checks(frames)
    reload_all(frames)
    log.info("Staging reloaded (%d tables)", len(frames))


if __name__ == "__main__":
    run()
