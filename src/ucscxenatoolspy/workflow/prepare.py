"""Load downloaded TSV datasets into pandas DataFrames."""

from __future__ import annotations

from pathlib import Path
from typing import Callable

import pandas as pd

from ucscxenatoolspy.workflow.query import QueryResult


def xena_prepare(
    objects: QueryResult | list[str] | str | Path,
    objects_name: list[str] | None = None,
    use_chunked: bool = False,
    chunk_size: int = 100,
    callback: Callable[[pd.DataFrame, int], pd.DataFrame] | None = None,
    comment: str = "#",
    na_values: list[str] | None = None,
    **read_csv_kwargs,
) -> pd.DataFrame | dict[str, pd.DataFrame]:
    """Load downloaded TSV files into pandas DataFrames.

    Mirrors R's XenaPrepare(). Accepts file paths, URLs, directories,
    or QueryResult objects.

    Args:
        objects: Input source — can be a QueryResult, list of file paths,
            a single file path, or a directory.
        objects_name: Optional names for returned data elements.
        use_chunked: If True, read files in chunks for large datasets.
        chunk_size: Number of rows per chunk when use_chunked=True.
        callback: Custom function to apply to each chunk. Overrides
            row/column filtering.
        comment: Character marking comment lines to skip (default '#').
        na_values: List of strings to interpret as NA.
        **read_csv_kwargs: Additional arguments passed to pd.read_csv.

    Returns:
        A single DataFrame (if one file) or dict of DataFrames (if multiple).
    """
    if na_values is None:
        na_values = ["", "NA", "[Discrepancy]"]

    # Resolve input to list of file paths
    files: list[str] = []

    if isinstance(objects, QueryResult):
        # Use locally downloaded file paths from xena_download
        if not objects.destfiles:
            raise ValueError(
                "QueryResult has no local file paths. "
                "Use xena_download() first, then pass the returned QueryResult."
            )
        files = objects.destfiles
        # Verify files exist
        existing = [f for f in files if Path(f).is_file()]
        if not existing:
            raise FileNotFoundError(
                f"None of the expected files exist. Did you run xena_download()? Paths: {files}"
            )
        files = existing
    elif isinstance(objects, (str, Path)):
        p = Path(objects)
        if p.is_dir():
            files = [str(f) for f in p.iterdir() if f.is_file()]
        elif p.is_file():
            files = [str(p)]
        elif str(objects).startswith("http"):
            # Single URL: read directly
            return pd.read_csv(
                objects, sep="\t", comment=comment, na_values=na_values, **read_csv_kwargs
            )
    elif isinstance(objects, list):
        for item in objects:
            p = Path(item)
            if p.is_dir():
                files.extend(str(f) for f in p.iterdir() if f.is_file())
            elif p.is_file():
                files.append(str(p))
            elif str(item).startswith("http"):
                raise NotImplementedError(
                    "URL lists not yet supported in xena_prepare()."
                )

    if not files:
        raise ValueError("No valid files found in input.")

    # Read files
    results: dict[str, pd.DataFrame] = {}

    for fp in files:
        if use_chunked:
            chunks = []
            for chunk in pd.read_csv(
                fp,
                sep="\t",
                comment=comment,
                na_values=na_values,
                chunksize=chunk_size,
                **read_csv_kwargs,
            ):
                if callback is not None:
                    chunk = callback(chunk, len(chunks))
                chunks.append(chunk)
            results[Path(fp).name] = pd.concat(chunks, ignore_index=True)
        else:
            results[Path(fp).name] = pd.read_csv(
                fp, sep="\t", comment=comment, na_values=na_values, **read_csv_kwargs
            )

    if objects_name is not None:
        # Remap keys
        results = dict(zip(objects_name, results.values()))

    if len(results) == 1:
        return next(iter(results.values()))

    return results
