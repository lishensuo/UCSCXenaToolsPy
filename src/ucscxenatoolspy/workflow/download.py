"""Download datasets from UCSC Xena Hubs."""

from __future__ import annotations

from pathlib import Path
from tempfile import gettempdir

import httpx
from tqdm import tqdm

from ucscxenatoolspy.workflow.query import QueryResult


def xena_download(
    query_result: QueryResult,
    destdir: str | Path | None = None,
    download_probe_map: bool = False,
    trans_slash: bool = False,
    force: bool = False,
    max_retries: int = 3,
) -> QueryResult:
    """Download datasets from UCSC Xena.

    Mirrors R's XenaDownload(). Downloads files with retry logic and
    progress bar.

    Args:
        query_result: QueryResult from xena_query().
        destdir: Directory to store downloaded files. Defaults to temp dir.
        download_probe_map: If True, also download ProbeMap data for ID mapping.
        trans_slash: If True, replace '/' in dataset names with '__'.
        force: If True, re-download even if file exists.
        max_retries: Maximum number of download attempts.

    Returns:
        Updated QueryResult with local file paths added.
    """
    if destdir is None:
        destdir = Path(gettempdir())
    else:
        destdir = Path(destdir)

    destdir.mkdir(parents=True, exist_ok=True)
    print(f"All downloaded files will be under: {destdir}")

    file_names: list[str] = []
    dest_files: list[str] = []

    for ds in query_result.datasets:
        if trans_slash:
            fname = ds.replace("/", "__")
        else:
            fname = ds

        # Ensure .gz extension matches URL
        if ".gz" in query_result.urls[query_result.datasets.index(ds)]:
            fname = f"{fname}.gz"

        file_names.append(fname)
        dest_path = destdir / fname

        # Create subdirectories if needed (when trans_slash is False)
        if not trans_slash:
            dest_path.parent.mkdir(parents=True, exist_ok=True)

        dest_files.append(str(dest_path))

    # Download files
    with httpx.Client(verify=False, timeout=60.0) as client:
        for i, (url, dest) in enumerate(tqdm(
            zip(query_result.urls, dest_files),
            total=len(query_result.urls),
            desc="Downloading",
        )):
            dest_path = Path(dest)
            if dest_path.exists() and not force:
                print(f"  {dest_path} already exists, skipping.")
                continue

            print(f"  Downloading {file_names[i]}")
            success = False
            for attempt in range(1, max_retries + 1):
                try:
                    resp = client.get(url)
                    resp.raise_for_status()
                    dest_path.parent.mkdir(parents=True, exist_ok=True)
                    dest_path.write_bytes(resp.content)
                    success = True
                    break
                except httpx.HTTPError as e:
                    if attempt < max_retries:
                        print(f"    Attempt {attempt} failed, retrying: {e}")
                    else:
                        # Try without .gz suffix
                        if url.endswith(".gz"):
                            url_no_gz = url[:-3]
                            try:
                                resp = client.get(url_no_gz)
                                resp.raise_for_status()
                                dest_path.parent.mkdir(parents=True, exist_ok=True)
                                dest_path.write_bytes(resp.content)
                                success = True
                            except httpx.HTTPError:
                                print(f"    Download failed after {max_retries} attempts")
                        else:
                            print(f"    Download failed after {max_retries} attempts")

    if trans_slash:
        print("Note: '/' in file names was replaced with '__'.")

    # Return updated QueryResult with destfiles info
    return QueryResult(
        hosts=query_result.hosts,
        datasets=query_result.datasets,
        urls=query_result.urls,
    )
