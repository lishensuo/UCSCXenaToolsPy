"""URL utilities — encoding and HTTP validation."""

from __future__ import annotations

import httpx


def url_encode(path: str) -> str:
    """URL-encode a path while preserving '/' separators.

    Mirrors R's url_encode() which uses URLencode(reserved=TRUE) then
    converts %2F back to /.

    Args:
        path: The URL path component to encode.

    Returns:
        URL-encoded string with '/' preserved.
    """
    from urllib.parse import quote
    return quote(path, safe="/")


def http_error_check(url: str, max_tries: int = 3, timeout: float = 10.0) -> bool:
    """Check if a URL returns an HTTP error.

    Mirrors R's httr::http_error() with retry logic.

    Args:
        url: The URL to check.
        max_tries: Number of retry attempts.
        timeout: Request timeout in seconds.

    Returns:
        True if the URL has an error (4xx/5xx), False if OK.
    """
    for attempt in range(1, max_tries + 1):
        try:
            with httpx.Client(verify=False, timeout=timeout) as client:
                resp = client.head(url, follow_redirects=True)
                return resp.status_code >= 400
        except httpx.HTTPError:
            if attempt == max_tries:
                return True  # Assume error after retries
            continue

    return True
