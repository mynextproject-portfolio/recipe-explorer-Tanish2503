"""
In-memory timing metrics for comparing internal storage queries against
external (TheMealDB) API calls, plus Redis cache hit/miss counters.
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
        self._cache_hits: Dict[str, int] = defaultdict(int)
        self._cache_misses: Dict[str, int] = defaultdict(int)

    def record(self, source: str, operation: str, duration_ms: float) -> None:
        self._samples[(source, operation)].append(duration_ms)
        logger.info("timing source=%s operation=%s duration_ms=%.2f", source, operation, duration_ms)

    def record_cache_result(self, operation: str, *, hit: bool) -> None:
        if hit:
            self._cache_hits[operation] += 1
            logger.info("cache hit operation=%s", operation)
        else:
            self._cache_misses[operation] += 1
            logger.info("cache miss operation=%s", operation)

    def summary(self) -> dict:
        result: dict = {}
        for (source, operation), samples in self._samples.items():
            result.setdefault(source, {})[operation] = {
                "count": len(samples),
                "avg_ms": round(sum(samples) / len(samples), 2),
                "min_ms": round(min(samples), 2),
                "max_ms": round(max(samples), 2),
            }
        all_ops = set(self._cache_hits) | set(self._cache_misses)
        if all_ops:
            cache_stats: dict = {}
            for op in all_ops:
                hits = self._cache_hits[op]
                misses = self._cache_misses[op]
                total = hits + misses
                cache_stats[op] = {
                    "hits": hits,
                    "misses": misses,
                    "hit_rate": round(hits / total, 3) if total else 0.0,
                }
            result["cache"] = cache_stats
        return result

    def reset(self) -> None:
        self._samples.clear()
        self._cache_hits.clear()
        self._cache_misses.clear()


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
