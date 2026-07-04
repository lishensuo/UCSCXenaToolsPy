"""Thread-safe in-memory TTL cache for API response caching."""
from __future__ import annotations

import hashlib
import json
import threading
import time
from collections.abc import Callable
from functools import wraps
from typing import Any


def ttl_cache(
    ttl: int = 3600,
    maxsize: int = 512,
):
    """Cache function results in memory with TTL, LRU, and per-key locking."""
    cache: dict[str, Any] = {}
    cache_times: dict[str, float] = {}
    cache_order: dict[str, int] = {}
    inflight: dict[str, threading.Lock] = {}
    lock = threading.RLock()
    sequence = 0

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            nonlocal sequence
            fn_name = getattr(func, "__name__", type(func).__name__)
            raw = json.dumps(
                {"fn": fn_name, "args": args, "kwargs": kwargs},
                sort_keys=True,
                default=str,
            )
            key = hashlib.md5(raw.encode(), usedforsecurity=False).hexdigest()

            now = time.monotonic()
            with lock:
                if key in cache:
                    if now - cache_times[key] < ttl:
                        sequence += 1
                        cache_order[key] = sequence
                        return cache[key]
                    del cache[key]
                    del cache_times[key]
                    del cache_order[key]

                key_lock = inflight.setdefault(key, threading.Lock())

            with key_lock:
                now = time.monotonic()
                with lock:
                    if key in cache and now - cache_times[key] < ttl:
                        sequence += 1
                        cache_order[key] = sequence
                        return cache[key]

                try:
                    result = func(*args, **kwargs)
                except Exception:
                    with lock:
                        inflight.pop(key, None)
                    raise

                with lock:
                    if len(cache) >= maxsize:
                        oldest_key = min(cache_order, key=lambda k: cache_order[k])
                        del cache[oldest_key]
                        del cache_times[oldest_key]
                        del cache_order[oldest_key]

                    cache[key] = result
                    cache_times[key] = time.monotonic()
                    sequence += 1
                    cache_order[key] = sequence
                    inflight.pop(key, None)

                return result

        def cache_clear() -> None:
            """Clear all cached entries for this function."""
            with lock:
                cache.clear()
                cache_times.clear()
                cache_order.clear()
                inflight.clear()

        wrapper.cache_clear = cache_clear  # type: ignore[attr-defined]
        return wrapper

    return decorator
