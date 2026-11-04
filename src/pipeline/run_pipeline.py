"""Run the full pipeline (P1 -> P2 -> P3), a single stage, or continuously.

    python -m src.pipeline.run_pipeline
    python -m src.pipeline.run_pipeline --stage extract
    python -m src.pipeline.run_pipeline --every 15
"""
import argparse
import time

from src.common.logger import get_logger
from src.datamart import build as p3
from src.extract import run as p1
from src.raw import run as p0
from src.transform import run as p2

log = get_logger("pipeline")
STAGES = {"raw": p0.run, "extract": p1.run, "transform": p2.run, "datamart": p3.run}


def run_all() -> None:
    for name, fn in STAGES.items():
        log.info("=== Stage: %s ===", name)
        fn()  # raises on failure -> downstream stages don't run


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", choices=STAGES.keys())
    ap.add_argument("--every", type=int, help="loop every N minutes (cron-style fallback)")
    args = ap.parse_args()
    job = STAGES[args.stage] if args.stage else run_all
    if args.every:
        import schedule
        schedule.every(args.every).minutes.do(job)
        job()
        while True:
            schedule.run_pending()
            time.sleep(1)
    else:
        job()


if __name__ == "__main__":
    main()
