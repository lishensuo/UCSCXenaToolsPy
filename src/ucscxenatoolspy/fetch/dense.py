"""Fetch functions — direct API queries without downloading full datasets.

Mirrors R's fetch.R. Three primary data types:
- Dense matrix (samples × probes/genes)
- Sparse (sample, position, variant)
- Segmented (sample, position, value)
"""

from __future__ import annotations

import time

import pandas as pd

from ucscxenatoolspy.api.datalog import (
    _p_dataset_fetch,
    _p_dataset_samples,
    _p_dataset_field,
    _p_sparse_data,
    _p_dataset_gene_probe_avg,
)
from ucscxenatoolspy.core.xena_data import load_xena_data


def fetch_dataset_samples(host: str, dataset: str, limit: int | None = None) -> list[str]:
    """Fetch sample IDs from a dataset.

    Args:
        host: Xena host URL.
        dataset: Dataset name.
        limit: Maximum number of samples to return. None = all.

    Returns:
        List of sample IDs.
    """
    limit_val = -1 if limit is None else limit
    result = _p_dataset_samples(host, dataset, limit=limit_val)
    if isinstance(result, list):
        return result
    return []


def fetch_dataset_identifiers(host: str, dataset: str) -> list[str]:
    """Fetch identifiers (probes/genes) from a dataset.

    Args:
        host: Xena host URL.
        dataset: Dataset name.

    Returns:
        List of identifiers.
    """
    result = _p_dataset_field(host, dataset)
    if isinstance(result, list):
        return result
    return []


def has_probeMap(host: str, dataset: str, return_url: bool = False) -> bool | str:
    """Check if a dataset has a ProbeMap for gene-to-probe mapping.

    Args:
        host: Xena host URL.
        dataset: Dataset name.
        return_url: If True and probeMap exists, return the download URL.

    Returns:
        True if probeMap exists, False otherwise. If return_url=True
        and probeMap exists, returns the full download URL.
    """
    xena_data = load_xena_data()
    match = xena_data.loc[
        (xena_data["XenaHosts"] == host) & (xena_data["XenaDatasets"] == dataset)
    ]

    if match.empty:
        return False

    probe_map = match.iloc[0].get("ProbeMap")
    if probe_map is None or (isinstance(probe_map, float) and str(probe_map) == "nan"):
        return False

    if return_url:
        return f"{host}/download/{probe_map}"
    return True


def fetch_dense_values(
    host: str,
    dataset: str,
    identifiers: list[str] | None = None,
    samples: list[str] | None = None,
    check: bool = True,
    use_probeMap: bool = False,
    time_limit: float = 30.0,
) -> pd.DataFrame:
    """Fetch values from a dense matrix dataset.

    Args:
        host: Xena host URL.
        dataset: Dataset name.
        identifiers: Probes or gene symbols. None = all.
        samples: Sample IDs. None = all.
        check: If True, validate identifiers/samples exist in dataset.
        use_probeMap: If True, map gene symbols via probeMap.
        time_limit: Timeout for query response in seconds.

    Returns:
        DataFrame indexed by identifier (gene/probe) with samples as columns.
        When use_probeMap=True, row names are gene symbols; otherwise probe IDs.

    Examples:
        >>> # Query with Ensembl IDs (probes)
        >>> fetch_dense_values(host, dataset, identifiers=['ENSG00000000005.5'],
        ...                    samples=['TCGA-02-0047-01'], check=False)
                       TCGA-02-0047-01
        ENSG00000000005.5       -9.966

        >>> # Query with gene symbols (requires probeMap)
        >>> fetch_dense_values(host, dataset, identifiers=['TP53'],
        ...                    samples=['TCGA-02-0047-01'], check=False, use_probeMap=True)
              TCGA-02-0047-01
        TP53           5.799
    """
    # Fetch all samples/identifiers if not specified
    if samples is None:
        samples = fetch_dataset_samples(host, dataset)

    if identifiers is None:
        if use_probeMap:
            # Get all identifiers from probeMap
            url = has_probeMap(host, dataset, return_url=True)
            if url:
                identifiers = list(pd.read_csv(url, sep="\t", usecols=[1]).iloc[:, 0])
            else:
                identifiers = fetch_dataset_identifiers(host, dataset)
        else:
            identifiers = fetch_dataset_identifiers(host, dataset)

    if check:
        # Validate samples
        all_samples_set = set(fetch_dataset_samples(host, dataset))
        valid_samples = [s for s in samples if s in all_samples_set]
        if not valid_samples:
            raise ValueError(f"No valid samples found for {host}/{dataset}")
        samples = valid_samples

        # Validate identifiers — skip when using probeMap since identifiers
        # are gene symbols that won't match probe-level IDs (e.g. ENSG...)
        if not use_probeMap:
            all_identifiers = fetch_dataset_identifiers(host, dataset)
            valid_ids = [i for i in identifiers if i in set(all_identifiers)]
            if not valid_ids:
                raise ValueError(f"No valid identifiers found for {host}/{dataset}")
            identifiers = valid_ids

    # Try probeMap path if requested
    if use_probeMap and has_probeMap(host, dataset):
        result = _retry_query(
            lambda: _p_dataset_gene_probe_avg(host, dataset, samples, identifiers),
            time_limit,
        )
        # Result is a list of dicts: [{'gene': 'TP53', 'position': [...], 'scores': [[...]]}, ...]
        if isinstance(result, list) and len(result) > 0 and "scores" in result[0]:
            data = {}
            for item in result:
                data[item["gene"]] = item["scores"][0]
            return pd.DataFrame(data, index=samples).T

    # Default fetch path
    result = _retry_query(
        lambda: _p_dataset_fetch(host, dataset, samples, identifiers),
        time_limit,
    )
    # result is a 2D list: rows=identifiers, cols=samples
    return pd.DataFrame(result, index=identifiers, columns=samples)


def fetch_sparse_values(
    host: str,
    dataset: str,
    genes: list[str],
    samples: list[str] | None = None,
    time_limit: float = 30.0,
) -> dict:
    """Fetch sparse (mutation) data.

    Args:
        host: Xena host URL.
        dataset: Dataset name.
        genes: Gene names to query.
        samples: Sample IDs. None = all.
        time_limit: Timeout for query response in seconds.

    Returns:
        Sparse data dict with samples, rows, etc.
    """
    if samples is None:
        samples = fetch_dataset_samples(host, dataset)

    return _retry_query(
        lambda: _p_sparse_data(host, dataset, samples, genes),
        time_limit,
    )


def _retry_query(query_fn, time_limit: float):
    """Execute a query with timeout and retry logic."""
    t_start = time.time()
    last_error = None

    while time.time() - t_start < time_limit:
        try:
            result = query_fn()
            return result
        except Exception as e:
            last_error = e
            time.sleep(1)

    raise RuntimeError(
        f"Query timed out after {time_limit}s: {last_error}"
    )
