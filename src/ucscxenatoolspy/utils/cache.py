"""File-based caching utilities for UCSC Xena query results."""

from __future__ import annotations

import hashlib
import json
import os
import pickle
from pathlib import Path
from typing import Any


def get_cache_dir() -> Path:
    """Return the cache directory path.

    Configurable via UCSCXENA_CACHE_DIR environment variable.
    Defaults to ~/.cache/ucscxenatoolspy.
    """
    env_dir = os.environ.get("UCSCXENA_CACHE_DIR")
    if env_dir:
        cache_dir = Path(env_dir)
    else:
        cache_dir = Path.home() / ".cache" / "ucscxenatoolspy"
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir


def make_cache_key(identifier: str, dataset: str, host: str, **kwargs: Any) -> str:
    """Generate a cache key from query parameters.

    Mirrors R's digest::digest(list(id, dataset, host, ...)).
    """
    payload = json.dumps(
        {"identifier": identifier, "dataset": dataset, "host": host, **kwargs},
        sort_keys=True,
    )
    return hashlib.md5(payload.encode()).hexdigest()


def read_cache(key: str) -> Any | None:
    """Read cached data by key. Returns None on miss or corruption."""
    path = get_cache_dir() / f"{key}.pkl"
    if not path.exists():
        return None
    try:
        with open(path, "rb") as f:
            return pickle.load(f)
    except Exception:
        return None


def write_cache(key: str, data: Any) -> None:
    """Write data to cache. Silently ignores failures."""
    path = get_cache_dir() / f"{key}.pkl"
    try:
        with open(path, "wb") as f:
            pickle.dump(data, f)
    except Exception:
        pass
