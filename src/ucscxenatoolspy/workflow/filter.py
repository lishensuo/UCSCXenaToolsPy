"""Filter a XenaHub by cohorts or datasets using regex."""

from __future__ import annotations

import re

from ucscxenatoolspy.core.xena_hub import XenaHub, hosts, cohorts, datasets
from ucscxenatoolspy.workflow.generate import xena_generate


def xena_filter(
    x: XenaHub,
    filter_cohorts: str | None = None,
    filter_datasets: str | None = None,
    ignore_case: bool = True,
) -> XenaHub:
    """Filter a XenaHub by cohort or dataset name patterns.

    Mirrors R's XenaFilter(). Supports regular expressions.

    Args:
        x: The XenaHub to filter.
        filter_cohorts: Regex pattern to filter cohorts. If None, no cohort filtering.
        filter_datasets: Regex pattern to filter datasets. If None, no dataset filtering.
        ignore_case: If True, case-insensitive matching.

    Returns:
        A new filtered XenaHub.

    Raises:
        ValueError: If neither filter_cohorts nor filter_datasets is provided.

    Example:
        >>> hub = xena_generate(subset=lambda df: df["XenaHostNames"] == "tcgaHub")
        >>> filtered = xena_filter(hub, filter_datasets="clinical")
    """
    if filter_cohorts is None and filter_datasets is None:
        raise ValueError("At least one of filter_cohorts or filter_datasets must be provided.")

    flags = re.IGNORECASE if ignore_case else 0

    selected_cohorts: list[str] = []
    selected_datasets: list[str] = []

    if filter_cohorts is not None:
        pattern = re.compile(filter_cohorts, flags)
        selected_cohorts = [c for c in cohorts(x) if pattern.search(c)]

    if filter_datasets is not None:
        pattern = re.compile(filter_datasets, flags)
        selected_datasets = [d for d in datasets(x) if pattern.search(d)]

    if not selected_cohorts and not selected_datasets:
        raise ValueError(
            f"No matching cohorts or datasets found. "
            f"Hosts: {hosts(x)}"
        )

    # Build subset lambda and regenerate
    xena_data_all = xena_generate().datasets  # triggers load

    def subset_fn(df):
        mask = df["XenaHosts"].isin(hosts(x))
        if selected_cohorts:
            mask &= df["XenaCohorts"].isin(selected_cohorts)
        if selected_datasets:
            mask &= df["XenaDatasets"].isin(selected_datasets)
        return mask

    return xena_generate(subset=subset_fn)
