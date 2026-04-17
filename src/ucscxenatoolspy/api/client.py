"""HTTP client for UCSC Xena API."""

from __future__ import annotations

from typing import Any

import httpx


class XenaClient:
    """HTTP client for UCSC Xena data hubs.

    Mirrors R's .xena_post() function. Sends Datalog queries to
    the {host}/data/ endpoint.

    Args:
        timeout: Request timeout in seconds.
        max_retries: Maximum retry attempts for failed requests.
        verify: SSL certificate verification. Default False to match
            R package behavior. Set True for production use.

    Example:
        >>> client = XenaClient()
        >>> result = client.post("https://tcga.xenahubs.net", "(+ 1 2)")
    """

    def __init__(
        self,
        timeout: float = 30.0,
        max_retries: int = 3,
        verify: bool = False,
    ):
        self.timeout = timeout
        self.max_retries = max_retries
        self.verify = verify
        self._client = httpx.Client(
            verify=verify,
            timeout=timeout,
            follow_redirects=True,
        )

    def post(self, host: str, query: str) -> Any:
        """POST a Datalog query to {host}/data/.

        Args:
            host: Xena host URL (e.g. "https://tcga.xenahubs.net").
            query: Datalog query string.

        Returns:
            Parsed JSON response.

        Raises:
            httpx.HTTPStatusError: If the server returns an error status.
            RuntimeError: If all retry attempts fail.
        """
        url = f"{host}/data/"

        for attempt in range(1, self.max_retries + 1):
            try:
                # Must send with empty Content-Type header, otherwise
                # Ring's wrap-params middleware consumes the body.
                # This matches httr::POST() behavior with raw string body.
                resp = self._client.post(
                    url,
                    content=query,
                    headers={"Content-Type": ""},
                )
                resp.raise_for_status()
                return resp.json()
            except (httpx.HTTPError, Exception) as e:
                if attempt < self.max_retries:
                    continue
                raise RuntimeError(
                    f"Failed to query {url} after {self.max_retries} attempts: {e}"
                ) from e

    def close(self):
        """Close the underlying HTTP client."""
        self._client.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()


# Global client (mirrors R's package-level state)
_global_client: XenaClient | None = None


def get_client() -> XenaClient:
    """Get or create the global XenaClient."""
    global _global_client
    if _global_client is None:
        _global_client = XenaClient()
    return _global_client


def xena_post(host: str, query: str) -> Any:
    """Convenience wrapper for the global client's POST method."""
    return get_client().post(host, query)
