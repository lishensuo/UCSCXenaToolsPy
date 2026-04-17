"""Scan XenaData metadata by regular expression."""

from __future__ import annotations

import re

import pandas as pd

from ucscxenatoolspy.core.xena_data import load_xena_data


def xena_scan(
    pattern: str | None = None,
    ignore_case: bool = True,
    xena_data: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Scan XenaData metadata by regular expression.

    Mirrors R's XenaScan(). Searches across all columns for rows matching
    the pattern. Useful for quickly finding datasets before using xena_generate().

    Args:
        pattern: Regular expression pattern to search. If None, returns all data.
        ignore_case: If True, case-insensitive matching.
        xena_data: Optional pre-loaded XenaData DataFrame. If None,
            loads the bundled snapshot.

    Returns:
        DataFrame of matching rows, or empty DataFrame if no matches.

    Example:
        >>> # Find datasets containing "Blood"
        >>> blood_datasets = xena_scan(pattern="Blood")
        >>> hub = xena_generate(subset=lambda df: df["XenaDatasets"].isin(blood_datasets["XenaDatasets"]))
    """
    if xena_data is None:
        xena_data = load_xena_data()

    if pattern is None:
        return xena_data

    flags = re.IGNORECASE if ignore_case else 0
    regex = re.compile(pattern, flags)

    # Search across all columns for each row
    matching_rows = []
    for idx, row in xena_data.iterrows():
        # Check if pattern matches any column value
        for col in xena_data.columns:
            val = row[col]
            if val is not None and not pd.isna(val):
                if isinstance(val, str) and regex.search(val):
                    matching_rows.append(idx)
                    break

    if matching_rows:
        return xena_data.loc[matching_rows]
    else:
        return xena_data.iloc[0:0]  # Empty DataFrame with same columns