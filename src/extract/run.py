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


def _prepare_for_staging(df: pd.DataFrame) -> pd.DataFrame:
    """Apply source-independent cleanup before the staging quality gate."""
    out = df.copy()
    out.columns = [str(column).strip().lower() for column in out.columns]
    for column in out.select_dtypes(include=["object", "string"]).columns:
        out[column] = out[column].astype("string").str.strip()
    return out


def run() -> None:
    init_db()
    chunks: dict[str, list[pd.DataFrame]] = {}
    for ex in get_extractors():
        chunks.setdefault(ex.target_table, []).extend(ex.extract())
    frames = {
        table: _prepare_for_staging(pd.concat(parts, ignore_index=True))
        for table, parts in chunks.items()
    }
    for t, df in frames.items():
        log.info("Extracted %-20s %8d rows", t, len(df))

    run_staging_checks(frames)
    reload_all(frames)
    log.info("Staging reloaded (%d tables)", len(frames))


if __name__ == "__main__":
    run()
