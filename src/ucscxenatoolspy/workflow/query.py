"""Query download URLs for datasets in a XenaHub."""

from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd

from ucscxenatoolspy.core.xena_hub import XenaHub, datasets as get_datasets
from ucscxenatoolspy.core.defaults import DEFAULT_HOSTS
from ucscxenatoolspy.core.xena_data import load_xena_data
from ucscxenatoolspy.utils.url import url_encode, http_error_check
from ucscxenatoolspy.utils.cache import make_key, read_cache, write_cache


@dataclass(frozen=True)
class QueryResult:
    """Result of xena_query(), containing URL and download information."""

    hosts: list[str] = field(default_factory=list)
    datasets: list[str] = field(default_factory=list)
    urls: list[str] = field(default_factory=list)
    destfiles: list[str] = field(default_factory=list)

    def to_dataframe(self) -> pd.DataFrame:
        """Convert to a pandas DataFrame."""
        df = pd.DataFrame({
            "hosts": self.hosts,
            "datasets": self.datasets,
            "url": self.urls,
        })
        if self.destfiles:
            df["destfile"] = self.destfiles
        return df

    @property
    def n_files(self) -> int:
        """Number of files to download."""
        return len(self.urls)


def xena_query(x: XenaHub, cache: bool = True) -> QueryResult:
    """Query download URLs for datasets in a XenaHub.

    Mirrors R's XenaQuery(). Constructs download URLs and validates
    them with HTTP HEAD requests, automatically appending .gz if needed.

    Results are cached on disk keyed by (hosts, datasets) so repeated
    calls with the same selection are instant.

    Args:
        x: The XenaHub object to query.
        cache: Whether to use disk cache. True = check cache first, save on miss.

    Returns:
        A QueryResult with hosts, datasets, and validated URLs.

    Example:
        >>> hub = xena_generate(subset=lambda df: df["XenaHostNames"] == "tcgaHub")
        >>> query = xena_query(hub)
    """
    # Check cache
    if cache:
        key = make_key("xena_query", sorted(x.hosts), sorted(x.datasets))
        cached = read_cache(key)
        if cached is not None:
            return cached

    print("This will check url status, please be patient.")

    xena_data = load_xena_data()
    target_datasets = set(get_datasets(x))

    matching = xena_data.loc[xena_data["XenaDatasets"].isin(target_datasets)]

    hosts_list: list[str] = []
    datasets_list: list[str] = []
    urls_list: list[str] = []

    for _, row in matching.iterrows():
        host = row["XenaHosts"]
        host_name = row["XenaHostNames"]
        ds = row["XenaDatasets"]

        # GDC Hub uses basename only for download URLs
        if host_name == "gdcHub":
            url = f"{host}/download/{url_encode(ds.rsplit('/', 1)[-1])}"
        else:
            url = f"{host}/download/{url_encode(ds)}"

        # Check if URL exists, try with .gz suffix if not
        if http_error_check(url):
            url = f"{url}.gz"

        hosts_list.append(host)
        datasets_list.append(ds)
        urls_list.append(url)

    result = QueryResult(
        hosts=hosts_list,
        datasets=datasets_list,
        urls=urls_list,
    )

    # Save to cache
    if cache:
        write_cache(key, result)

    return result
