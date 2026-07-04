"""Unit tests for TTL cache utility — no network required."""
from __future__ import annotations

import time
import threading

import pytest

from ucscxenatoolspy.api_service.cache_utils import ttl_cache


# ── Fixtures ──────────────────────────────────────────────────────────────

class _CallCounter:
    """Track how many times a decorated function was actually called."""
    def __init__(self):
        self.count = 0

    def __call__(self, x: int = 0) -> int:
        self.count += 1
        return x * 2


@pytest.fixture
def fresh_cache():
    """Return a fresh @ttl_cache-decorated function and its call counter."""
    counter = _CallCounter()
    fn = ttl_cache(ttl=10, maxsize=32)(counter)
    return fn, counter


# ── Basic cache behavior ──────────────────────────────────────────────────

class TestCacheMiss:
    """On first call, the function should execute."""
    def test_returns_correct_value(self, fresh_cache):
        fn, _ = fresh_cache
        assert fn(5) == 10

    def test_increments_call_count(self, fresh_cache):
        fn, counter = fresh_cache
        fn(1)
        assert counter.count == 1


class TestCacheHit:
    """Second call with same args should return cached result."""
    def test_returns_same_value(self, fresh_cache):
        fn, _ = fresh_cache
        a = fn(7)
        b = fn(7)
        assert a == b == 14

    def test_does_not_increment_call_count(self, fresh_cache):
        fn, counter = fresh_cache
        fn(3)
        fn(3)
        fn(3)
        assert counter.count == 1


class TestCacheDifferentArgs:
    """Different arguments should cause separate cache entries."""
    def test_different_args_miss(self, fresh_cache):
        fn, counter = fresh_cache
        fn(1)
        fn(2)
        assert counter.count == 2

    def test_different_kwargs_miss(self, fresh_cache):
        fn, counter = fresh_cache
        fn(x=10)
        fn(x=20)
        assert counter.count == 2


# ── TTL expiration ────────────────────────────────────────────────────────

class TestTTLExpiration:
    def test_cache_expires_after_ttl(self):
        """After TTL, the function should be called again."""
        fn = ttl_cache(ttl=1, maxsize=32)(_CallCounter())
        counter = fn.__wrapped__
        fn(42)
        assert counter.count == 1
        time.sleep(1.1)  # wait for TTL
        fn(42)
        assert counter.count == 2

    def test_cache_fresh_within_ttl(self):
        """Within TTL, cached value is returned."""
        fn = ttl_cache(ttl=10, maxsize=32)(_CallCounter())
        counter = fn.__wrapped__
        fn(99)
        fn(99)
        assert counter.count == 1


# ── maxsize / LRU eviction ────────────────────────────────────────────────

class TestLRUEviction:
    def test_evicts_oldest_when_at_capacity(self):
        """Oldest (least recently read) entry should be evicted first."""
        fn = ttl_cache(ttl=60, maxsize=3)(_CallCounter())
        counter = fn.__wrapped__

        # Fill cache: keys 1, 2, 3
        fn(1)
        fn(2)
        fn(3)
        assert counter.count == 3

        # Access key 1 again — now 2 is the oldest-by-access
        fn(1)

        # Insert key 4 — should evict key 2 (oldest access time)
        fn(4)
        assert counter.count == 4

        # key 1 should still be cached (was accessed recently)
        fn(1)
        assert counter.count == 4  # still cached

        # key 2 was evicted — should trigger a new call
        fn(2)
        assert counter.count == 5


# ── cache_clear ───────────────────────────────────────────────────────────

class TestCacheClear:
    def test_clear_empties_cache(self):
        fn = ttl_cache(ttl=60, maxsize=32)(_CallCounter())
        counter = fn.__wrapped__
        fn(1)
        fn(2)
        fn.cache_clear()
        fn(1)
        assert counter.count == 3  # 2 for initial + 1 after clear


# ── Thread safety ─────────────────────────────────────────────────────────

class TestThreadSafety:
    def test_concurrent_access_consistent(self):
        """Multiple threads hitting the cache should get consistent results."""
        fn = ttl_cache(ttl=60, maxsize=128)(_CallCounter())
        counter = fn.__wrapped__
        errors = []

        def worker(n: int):
            for _ in range(50):
                r = fn(42)
                if r != 84:
                    errors.append(r)

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
        # Should be called exactly once — first thread populates cache
        assert counter.count == 1
