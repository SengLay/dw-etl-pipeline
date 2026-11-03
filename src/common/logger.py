import logging
from logging.handlers import TimedRotatingFileHandler
from datetime import datetime
from pathlib import Path
import sys


_LOG_DIR = Path("logs")
_FILE_HANDLER: TimedRotatingFileHandler | None = None
_LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
_LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def _get_file_handler() -> TimedRotatingFileHandler:
    global _FILE_HANDLER

    if _FILE_HANDLER is None:
        _LOG_DIR.mkdir(parents=True, exist_ok=True)
        _FILE_HANDLER = TimedRotatingFileHandler(
            _LOG_DIR / f"log_{datetime.now().strftime('%Y_%m_%d')}.log",
            when="midnight",
            interval=1,
            backupCount=30,
            encoding="utf-8",
        )
        _FILE_HANDLER.suffix = "%Y-%m-%d"
        _FILE_HANDLER.setFormatter(logging.Formatter(
            _LOG_FORMAT,
            datefmt=_LOG_DATE_FORMAT,
        ))

    return _FILE_HANDLER


def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    if not logger.handlers:
        formatter = logging.Formatter(_LOG_FORMAT, datefmt=_LOG_DATE_FORMAT)
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
        logger.addHandler(_get_file_handler())
        logger.setLevel(logging.INFO)
    return logger
