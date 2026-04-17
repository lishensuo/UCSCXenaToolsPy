"""Query ProbeMap URLs for datasets in a XenaHub."""

from __future__ import annotations

import pandas as pd

from ucscxenatoolspy.core.xena_hub import XenaHub, datasets as get_datasets
from ucscxenatoolspy.core.xena_data import load_xena_data
from ucscxenatoolspy.core.defaults import DEFAULT_HOSTS
from ucscxenatoolspy.utils.url import url_encode, http_error_check


def xena_query_probe_map(x: XenaHub) -> pd.DataFrame:
    """Query ProbeMap URLs for datasets in a XenaHub.

    Mirrors R's XenaQueryProbeMap(). Returns URLs for downloading ProbeMap
    files that map probes to gene symbols. Datasets without ProbeMap are
    ignored.

    Args:
        x: A XenaHub object.

    Returns:
        DataFrame with columns: hosts, datasets, url.
        Each row represents a ProbeMap file available for download.

    Example:
        >>> hub = xena_generate(subset=lambda df: df["XenaHostNames"] == "tcgaHub")
        >>> probe_urls = xena_query_probe_map(hub)
        >>> # Download ProbeMap files
        >>> for url in probe_urls["url"]:
        ...     # download url
        ...     pass
    """
    print("Check ProbeMap urls of datasets.")

    target_datasets = set(get_datasets(x))
    xena_data = load_xena_data()

    # Filter datasets that have ProbeMap
    matching = xena_data.loc[
        (xena_data["XenaDatasets"].isin(target_datasets)) &
        (xena_data["ProbeMap"].notna())
    ]

    if matching.empty:
        print("No datasets with ProbeMap found.")
        return pd.DataFrame(columns=["hosts", "datasets", "url"])

    results = []
    for _, row in matching.iterrows():
        host = row["XenaHosts"]
        host_name = row["XenaHostNames"]
        probe_map = row["ProbeMap"]

        if probe_map is None or pd.isna(probe_map):
            continue

        # Build URL (handle gdcHub special case)
        if host_name == "gdcHub":
            url = f"{host}/download/{url_encode(str(probe_map).rsplit('/', 1)[-1])}"
        else:
            url = f"{host}/download/{url_encode(str(probe_map))}"

        # Check if URL exists, try with .gz suffix if not
        if http_error_check(url):
            url = f"{url}.gz"
            if http_error_check(url):
                # Skip if both fail
                continue

        results.append({
            "hosts": host,
            "datasets": probe_map,
            "url": url,
        })

    if not results:
        print("No valid ProbeMap URLs found.")
        return pd.DataFrame(columns=["hosts", "datasets", "url"])

    result_df = pd.DataFrame(results)
    # Remove duplicates
    result_df = result_df.drop_duplicates()

    print(f"Found {len(result_df)} ProbeMap URLs.")

    return result_df