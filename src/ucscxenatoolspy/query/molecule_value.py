"""Query molecule values from UCSC Xena datasets.

Mirrors R's query_molecule_value() and get_data() from UCSCXenaShiny.
Supports single identifier lookup and genomic signature formula evaluation.
"""

from __future__ import annotations

import re
from typing import Any

import numpy as np
import pandas as pd

from ucscxenatoolspy.core.defaults import HOST_NAME_TO_URL
from ucscxenatoolspy.core.xena_data import load_xena_data
from ucscxenatoolspy.fetch.dense import fetch_dense_values
from ucscxenatoolspy.utils.cache import get_cache_dir, make_cache_key, read_cache, write_cache


def _auto_detect_host(dataset: str) -> str:
    """Auto-detect host URL from dataset name using metadata.

    Searches XenaDatasets column for exact match first, then partial match.
    Resolves short host names (e.g. "tcgaHub") to full URLs.
    """
    xena_data = load_xena_data()

    # Exact match
    match = xena_data[xena_data["XenaDatasets"] == dataset]
    if match.empty:
        # Partial match
        match = xena_data[xena_data["XenaDatasets"].str.contains(dataset, na=False)]
    if match.empty:
        raise ValueError(f"Dataset '{dataset}' not found in XenaData metadata.")

    host_name = match["XenaHostNames"].iloc[0]
    if host_name in HOST_NAME_TO_URL:
        return HOST_NAME_TO_URL[host_name]
    # If it's already a URL
    return host_name


def _extract_formula_variables(formula: str) -> list[str]:
    """Extract variable names (gene IDs) from a genomic signature formula.

    Strips numeric literals, operators, parentheses, and known math function
    names, leaving only identifier tokens.
    """
    # Remove known math function names
    expr = re.sub(r'\b(?:sqrt|log|log2|log10|exp|abs|round|sin|cos|tan)\b', '', formula)
    # Remove numeric literals
    expr = re.sub(r'\b\d+\.?\d*\b', '', expr)
    # Remove operators, parentheses, and whitespace
    expr = re.sub(r'[\s+\-*/()^]+', ' ', expr).strip()
    return [t for t in expr.split() if t]


def _safe_eval_formula(formula: str, df: pd.DataFrame) -> pd.Series:
    """Safely evaluate a genomic signature formula against a DataFrame.

    Uses restricted eval with empty __builtins__ and numpy math functions.
    """
    safe_ns: dict[str, Any] = {
        "abs": abs,
        "max": max,
        "min": min,
        "sum": sum,
        "sqrt": np.sqrt,
        "log": np.log,
        "log2": np.log2,
        "log10": np.log10,
        "exp": np.exp,
        "round": round,
        "np": np,
    }
    for col in df.columns:
        safe_ns[col] = df[col].values

    result = eval(formula, {"__builtins__": {}}, safe_ns)
    return pd.Series(result, index=df.index, name=formula)


def get_data(
    dataset: str,
    identifier: str,
    host: str | None = None,
    cache: bool = True,
) -> pd.Series:
    """Fetch molecular data for a single identifier from a dataset.

    Wraps fetch_dense_values with host auto-detection and file-based caching.
    Mirrors R's get_data() function.

    Args:
        dataset: Dataset name (e.g. "ccle_expression").
        identifier: Gene symbol or probe ID (e.g. "TP53").
        host: Xena host URL or short name. None = auto-detect from metadata.
        cache: Whether to use file-based caching.

    Returns:
        pd.Series indexed by sample name with molecular values.
    """
    if host is None:
        host = _auto_detect_host(dataset)
    elif host in HOST_NAME_TO_URL:
        host = HOST_NAME_TO_URL[host]

    # Check cache
    if cache:
        key = make_cache_key(identifier, dataset, host)
        cached = read_cache(key)
        if cached is not None:
            return pd.Series(cached["values"], index=cached["index"], name=identifier)

    # Fetch from API
    result = fetch_dense_values(
        host, dataset, identifiers=[identifier], samples=None, check=False
    )

    # Convert API result to pd.Series
    # fetch_dense_values returns a 2D list: [[val1, val2, ...]] for single identifier
    if isinstance(result, list) and len(result) > 0:
        values = result[0]
        # We need sample names — fetch them
        from ucscxenatoolspy.fetch.dense import fetch_dataset_samples
        sample_ids = fetch_dataset_samples(host, dataset)
        series = pd.Series(values, index=sample_ids[:len(values)], name=identifier)
    else:
        series = pd.Series([], dtype=float, name=identifier)

    # Save to cache
    if cache:
        write_cache(key, {"values": series.tolist(), "index": series.index.tolist()})

    return series


def query_molecule_value(
    dataset: str,
    molecule: str,
    host: str | None = None,
    cache: bool = True,
) -> pd.Series | Any:
    """Query molecular data from a UCSC Xena dataset.

    Supports two modes:

    1. Single identifier: returns a pd.Series of values indexed by sample.
       Example: ``query_molecule_value("ccle_expression", "TP53")``
    2. Genomic signature formula: evaluates the formula against queried genes.
       Example: ``query_molecule_value("ccle_expression", "TP53 + 2 * KRAS - PTEN")``

    Mirrors R's query_molecule_value() from UCSCXenaShiny.

    Args:
        dataset: Dataset name.
        molecule: Gene symbol/probe ID, or arithmetic formula with spaces.
        host: Xena host URL or short name. None = auto-detect.
        cache: Whether to use file-based caching.

    Returns:
        pd.Series of molecular values indexed by sample name,
        or NA if formula evaluation fails.
    """
    has_signature = " " in molecule

    if has_signature:
        # Genomic signature mode
        variables = _extract_formula_variables(molecule)
        print(f"Querying multiple identifiers: {', '.join(variables)}")

        try:
            dfs = {}
            for var in variables:
                dfs[var] = get_data(dataset, var, host=host, cache=cache)

            df = pd.DataFrame(dfs)
            result = _safe_eval_formula(molecule, df)
            return result

        except Exception:
            print("Warning: Query and evaluate failed, bad IDs or formula or data values.")
            return pd.Series([np.nan])
    else:
        # Single identifier mode
        return get_data(dataset, molecule, host=host, cache=cache)
