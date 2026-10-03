"""Opt-in development timing helpers for investigating slow requests."""

from __future__ import annotations

import logging
import os
from contextlib import contextmanager
from time import perf_counter
from typing import Any, Iterator

logger = logging.getLogger("docktech.timing")
logger.setLevel(logging.INFO)


def timing_start() -> float:
    return perf_counter()


def log_timing(stage: str, started_at: float, **details: Any) -> None:
    if os.getenv("DOCKTECH_TIMING") != "1":
        return
    logger.info("[DockTech timing] %s duration_ms=%.1f details=%s", stage, (perf_counter() - started_at) * 1000, details)


@contextmanager
def timed_stage(stage: str, **details: Any) -> Iterator[None]:
    started_at = timing_start()
    try:
        yield
    finally:
        log_timing(stage, started_at, **details)
