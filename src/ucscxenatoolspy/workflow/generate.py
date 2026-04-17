"""Generate a XenaHub from XenaData by subsetting."""

from __future__ import annotations

from typing import Callable

import pandas as pd

from ucscxenatoolspy.core.xena_hub import XenaHub
from ucscxenatoolspy.core.xena_data import load_xena_data


def xena_generate(
    subset: Callable[[pd.DataFrame], pd.Series] = lambda df: pd.Series([True] * len(df)),
    xena_data: pd.DataFrame | None = None,
) -> XenaHub:
    """Generate a XenaHub by subsetting the XenaData metadata.

    Mirrors R's XenaGenerate(). Instead of R's non-standard evaluation
    (substitute/eval), this uses a callable that receives the DataFrame
    and returns a boolean mask Series.

    Args:
        subset: A callable that takes a DataFrame and returns a boolean
            Series indicating which rows to keep.
            E.g. ``lambda df: df["XenaHostNames"] == "tcgaHub"``
        xena_data: Optional pre-loaded XenaData DataFrame. If None,
            loads the bundled snapshot.

    Returns:
        A XenaHub containing the unique hosts, cohorts, and datasets
        from the filtered rows.

    Example:
        >>> hub = xena_generate(subset=lambda df: df["XenaHostNames"] == "tcgaHub")
    """
    if xena_data is None:
        xena_data = load_xena_data()

    mask = subset(xena_data)
    filtered = xena_data.loc[mask]

    return XenaHub(
        hosts=filtered["XenaHosts"].unique().tolist(),
        cohorts=filtered["XenaCohorts"].unique().tolist(),
        datasets=filtered["XenaDatasets"].tolist(),
    )
