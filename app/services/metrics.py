"""
In-memory timing metrics for comparing internal storage queries against
external (TheMealDB) API calls.
"""
import logging
import time
from collections import defaultdict
from contextlib import contextmanager
from typing import Dict, List, Tuple

logger = logging.getLogger("recipe_explorer.timing")


class _Timer:
    duration_ms: float = 0.0


class TimingMetrics:
    def __init__(self):
        self._samples: Dict[Tuple[str, str], List[float]] = defaultdict(list)

    def record(self, source: str, operation: str, duration_ms: float) -> None:
        self._samples[(source, operation)].append(duration_ms)
        logger.info("timing source=%s operation=%s duration_ms=%.2f", source, operation, duration_ms)

    def summary(self) -> dict:
        result: dict = {}
        for (source, operation), samples in self._samples.items():
            result.setdefault(source, {})[operation] = {
                "count": len(samples),
                "avg_ms": round(sum(samples) / len(samples), 2),
                "min_ms": round(min(samples), 2),
                "max_ms": round(max(samples), 2),
            }
        return result

    def reset(self) -> None:
        self._samples.clear()


metrics = TimingMetrics()


@contextmanager
def timed(source: str, operation: str):
    """Measure a block's duration and record it under (source, operation).

    Works around both sync calls and `await` calls made inside the block.
    The yielded timer's `duration_ms` is only valid after the block exits.
    """
    timer = _Timer()
    start = time.perf_counter()
    try:
        yield timer
    finally:
        timer.duration_ms = (time.perf_counter() - start) * 1000
        metrics.record(source, operation, timer.duration_ms)
