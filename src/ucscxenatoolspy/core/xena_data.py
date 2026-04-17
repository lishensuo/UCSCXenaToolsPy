"""XenaData metadata loading and update."""

from __future__ import annotations

import importlib.resources
import json
import time
from pathlib import Path

import pandas as pd

from ucscxenatoolspy.api.datalog import _p_all_cohorts, _p_dataset_list, _p_dataset_metadata
from ucscxenatoolspy.core.defaults import DEFAULT_HOSTS


_XENA_DATA_COLUMNS = [
    "XenaHosts", "XenaHostNames", "XenaCohorts", "XenaDatasets", "SampleCount",
    "DataSubtype", "Label", "Type", "AnatomicalOrigin", "SampleType",
    "Tags", "ProbeMap", "LongTitle", "Citation", "Version", "Unit", "Platform",
]


def _parse_json_metadata(text: str | None) -> dict:
    """Parse JSON metadata from dataset text field."""
    if not text:
        return {}
    try:
        return json.loads(text)
    except (json.JSONDecodeError, TypeError):
        return {}


def _extract_metadata_fields(metadata: dict) -> dict:
    """Extract structured fields from JSON metadata."""
    # Helper to convert list to comma-separated string (mirrors R's behavior)
    def _to_str(v):
        if v is None:
            return None
        if isinstance(v, list):
            return ",".join(str(x) for x in v)
        return str(v)

    return {
        "Cohort": metadata.get("cohort"),  # Cohort is in JSON text, not top-level
        "Label": metadata.get("label"),
        "Citation": metadata.get("citation"),
        "Tags": _to_str(metadata.get("tags")),
        "AnatomicalOrigin": _to_str(metadata.get("anatomical_origin")),
        "SampleType": _to_str(metadata.get("sample_type")),
        "Version": metadata.get("version"),
        "Unit": metadata.get("unit"),
        "Platform": metadata.get("platform"),
    }


def _query_host_datasets(host_url: str) -> pd.DataFrame:
    """Query all datasets for a single host."""
    host_name = DEFAULT_HOSTS.get(host_url, host_url)

    try:
        # Add delay to avoid rate limiting
        time.sleep(0.5)

        # Get all cohorts
        cohorts = _p_all_cohorts(host_url)
        if not cohorts:
            return pd.DataFrame()

        # Remove "(unassigned)" cohort
        cohorts = [c for c in cohorts if c != "(unassigned)"]
        if not cohorts:
            return pd.DataFrame()

        # Add delay
        time.sleep(0.5)

        # Get all datasets for all cohorts (batched)
        all_datasets = _p_dataset_list(host_url, cohorts)

        if not all_datasets:
            return pd.DataFrame()

        # Build DataFrame
        records = []
        for ds in all_datasets:
            # Parse JSON metadata first to get cohort
            text = ds.get("text")
            metadata = _parse_json_metadata(text) if text else {}

            # Cohort is in JSON text, not top-level field
            cohort = metadata.get("cohort") or ds.get("cohort")

            record = {
                "XenaHosts": host_url,
                "XenaHostNames": host_name,
                "XenaCohorts": cohort,
                "XenaDatasets": ds.get("name"),
                "SampleCount": ds.get("count", 0),
                "Type": ds.get("type"),
                "DataSubtype": ds.get("datasubtype"),
                "LongTitle": ds.get("longtitle"),
                "ProbeMap": ds.get("probemap"),
            }

            # Add other metadata fields (excluding Cohort which we already set)
            extra_fields = _extract_metadata_fields(metadata)
            # Don't overwrite XenaCohorts with Cohort key
            if "Cohort" in extra_fields:
                del extra_fields["Cohort"]
            record.update(extra_fields)

            records.append(record)

        return pd.DataFrame(records)

    except Exception as e:
        print(f"Error querying {host_url}: {e}")
        return pd.DataFrame()


def load_xena_data() -> pd.DataFrame:
    """Load the bundled XenaData metadata snapshot.

    Returns:
        DataFrame with 17 columns of UCSC Xena dataset metadata.
    """
    pkg_data = importlib.resources.files("ucscxenatoolspy.data")
    parquet_path = pkg_data / "xena_data.parquet"

    if parquet_path.is_file():
        return pd.read_parquet(parquet_path)

    # Fallback: return empty DataFrame with correct schema
    return pd.DataFrame(columns=_XENA_DATA_COLUMNS)


def xena_data_update(save_to_local: bool = False) -> pd.DataFrame:
    """Fetch fresh metadata from all Xena hubs.

    Mirrors R's XenaDataUpdate(). Queries all default hosts for cohorts
    and datasets, parses JSON metadata, and returns an updated DataFrame.

    Args:
        save_to_local: If True, save the updated data to the package data directory.

    Returns:
        Updated XenaData DataFrame with columns:
        - XenaHosts: Host URL
        - XenaHostNames: Host short name
        - XenaCohorts: Cohort name
        - XenaDatasets: Dataset name
        - SampleCount: Number of samples
        - Type: Data type
        - DataSubtype: Data subtype
        - LongTitle: Long title
        - ProbeMap: ProbeMap dataset name
        - Label, Citation, Tags, AnatomicalOrigin, SampleType, Version, Unit, Platform
    """
    print("Fetching metadata from UCSC Xena hubs...")

    host_urls = list(DEFAULT_HOSTS.keys())

    # Query hosts sequentially to avoid rate limiting
    all_dfs = []
    for i, url in enumerate(host_urls):
        host_name = DEFAULT_HOSTS.get(url, url)
        print(f"  [{i+1}/{len(host_urls)}] Querying {host_name}...", end=" ", flush=True)
        try:
            df = _query_host_datasets(url)
            if not df.empty:
                print(f"{len(df)} datasets")
                all_dfs.append(df)
            else:
                print("0 datasets")
        except Exception as e:
            print(f"Error - {e}")

    if not all_dfs:
        print("No data fetched from any host.")
        return pd.DataFrame(columns=_XENA_DATA_COLUMNS)

    # Combine all DataFrames
    result = pd.concat(all_dfs, ignore_index=True)

    # Ensure all columns exist
    for col in _XENA_DATA_COLUMNS:
        if col not in result.columns:
            result[col] = None

    # Reorder columns
    result = result[_XENA_DATA_COLUMNS]

    print(f"Total: {len(result)} datasets from {len(host_urls)} hosts")

    if save_to_local:
        # Save to package data directory
        try:
            data_dir = Path(__file__).parent.parent.parent / "data"
            data_dir.mkdir(exist_ok=True)
            parquet_path = data_dir / "xena_data.parquet"
            result.to_parquet(parquet_path, index=False)
            print(f"Saved to {parquet_path}")
        except Exception as e:
            print(f"Warning: Could not save to local: {e}")

    return result
